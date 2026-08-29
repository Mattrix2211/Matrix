"""Handlers de l'action-dispatcher POST de InstallationDetailView (assets/web_views.py).

Un handler par action de la fiche installation, regroupés ci-dessous par
sous-domaine (fiche, événements, entretien, pièces, relevés heures/vibration/
isolement) — même esprit que reports/services.py : la logique métier est isolée
dans des fonctions dédiées et testables plutôt que dans une longue chaîne
if/elif (~30 branches, ~560 lignes avant ce découpage).

Refactor pur : chaque handler reproduit exactement le comportement de la branche
elif correspondante d'origine.

Chaque handler reçoit (view, request, inst, qs) :
- view : l'instance de InstallationDetailView (pour view.get_queryset(), scopé
  par ScopedQuerySetMixin — même périmètre qu'avant ce découpage) ;
- request : la requête HTTP (POST/FILES) ;
- inst : l'installation courante (view.get_object()) ;
- qs : suffixe "?tab=..." à conserver dans les redirections (onglet actif).

Le tableau ACTION_HANDLERS en bas de fichier associe chaque valeur du champ
POST "action" à son handler ; InstallationDetailView.post s'en sert comme
dict {action: handler} au lieu de la chaîne if/elif.
"""
import json
from datetime import datetime, time

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.utils import OperationalError
from django.shortcuts import redirect
from django.utils import timezone

from accounts.models import AuditLog
from org.models import Section, Sector, Service, Ship

from .models import (
    Installation,
    InstallationBigrameChoice,
    InstallationEvent,
    InstallationEventAttachment,
    InstallationExtraField,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationMaintenance,
    InstallationMaintenanceAttachment,
    InstallationPart,
    InstallationVibrationReading,
    ModeDeclenchement,
)
from .web_views import _afficher_erreur_validation, _org_dans_perimetre, _resoudre_emplacement, _resoudre_parent_valide


def _parse_date_jjmmaaaa(date_str):
    """Convertit une date saisie au format JJ/MM/AAAA en objet date, ou None si
    la saisie est vide ou mal formée (même tolérance silencieuse que le code
    d'origine, qui laissait alors la valeur par défaut de l'appelant)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except Exception:
        return None


def _parse_datetime_jjmmaaaa_minuit(date_str):
    """Convertit une date saisie au format JJ/MM/AAAA en datetime timezone-aware
    à minuit (utilisé pour InstallationEvent.date, qui est un DateTimeField),
    ou None si la saisie est vide ou mal formée."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, '%d/%m/%Y')
        return timezone.make_aware(datetime.combine(dt.date(), time(0, 0)), timezone.get_current_timezone())
    except Exception:
        return None


# --- Fiche installation ---------------------------------------------------

def _action_edit_installation(view, request, inst, qs):
    pk = request.POST.get('pk')
    ship_id = request.POST.get('ship_id')
    service_id = request.POST.get('service_id')
    sector_id = request.POST.get('sector_id')
    section_id = request.POST.get('section_id')
    # Périmètre (T-SEC) : même contrôle que sur la liste (InstallationListView),
    # pour empêcher un contournement via la fiche détail.
    if ship_id and not _org_dans_perimetre(request.user, Ship, ship_id):
        messages.error(request, "Unité hors de votre périmètre.")
        return redirect(f"/installations/{pk}/{qs}")
    if service_id and not _org_dans_perimetre(request.user, Service, service_id):
        messages.error(request, "Service hors de votre périmètre.")
        return redirect(f"/installations/{pk}/{qs}")
    if sector_id and not _org_dans_perimetre(request.user, Sector, sector_id):
        messages.error(request, "Secteur hors de votre périmètre.")
        return redirect(f"/installations/{pk}/{qs}")
    if section_id and not _org_dans_perimetre(request.user, Section, section_id):
        messages.error(request, "Section hors de votre périmètre.")
        return redirect(f"/installations/{pk}/{qs}")
    try:
        # Périmètre : l'installation visée doit appartenir au périmètre de
        # l'appelant (view.get_queryset(), scopé) — un identifiant hors périmètre
        # est traité comme introuvable plutôt que d'être chargé via le manager brut.
        it = view.get_queryset().get(pk=pk)
        it.designation = request.POST.get('designation', it.designation).strip()
        it.reference = request.POST.get('reference', it.reference).strip()
        it.marque = request.POST.get('marque', it.marque).strip()
        it.gisement = request.POST.get('gisement', it.gisement).strip()
        it.local = request.POST.get('local', it.local).strip()
        bigrame_id = request.POST.get('bigrame_id')
        photo = request.FILES.get('photo')
        if photo:
            it.photo = photo
        it.ship = Ship.objects.filter(pk=ship_id).first() if ship_id else None
        it.service = Service.objects.filter(pk=service_id).first() if service_id else None
        it.sector = Sector.objects.filter(pk=sector_id).first() if sector_id else None
        it.section = Section.objects.filter(pk=section_id).first() if section_id else None
        it.location = _resoudre_emplacement(request, it.ship)
        it.bigrame = InstallationBigrameChoice.objects.filter(pk=bigrame_id).first() if bigrame_id else None
        # Périodicité isolement
        iso_period = (request.POST.get('iso_periodicity') or '').strip().upper()
        if iso_period in ('M', 'T', 'A'):
            it.iso_periodicity = iso_period
        erreur_parent = _resoudre_parent_valide(request, it, Installation)
        if erreur_parent:
            messages.error(request, erreur_parent)
            return redirect(f"/installations/{pk}/{qs}")
        try:
            it.full_clean()
        except ValidationError as exc:
            _afficher_erreur_validation(request, exc)
            return redirect(f"/installations/{pk}/{qs}")
        it.save()
        # Met à jour les champs personnalisés si fournis
        try:
            extras_json = request.POST.get('extra_fields')
            if extras_json is not None:
                InstallationExtraField.objects.filter(installation=it).delete()
                extras = json.loads(extras_json) if extras_json else []
                order = 0
                for ex in extras:
                    lbl = (ex.get('label') or '').strip()
                    val = (ex.get('value') or '').strip()
                    if not lbl:
                        continue
                    InstallationExtraField.objects.create(
                        installation=it, label=lbl, value=val, order=order, created_by=request.user
                    )
                    order += 1
        except Exception:
            pass
        AuditLog.objects.create(actor=request.user, action='edit_installation', details=f'id={it.id}')
        messages.success(request, 'Installation mise à jour.')
    except Installation.DoesNotExist:
        messages.error(request, "Installation introuvable")
    return redirect(f"/installations/{pk}/{qs}")


def _action_delete_installation(view, request, inst, qs):
    pk = request.POST.get('pk')
    # Périmètre : une installation hors périmètre est traitée comme introuvable.
    supprimees = view.get_queryset().filter(pk=pk).delete()[0]
    if supprimees:
        messages.success(request, 'Installation supprimée.')
    else:
        messages.error(request, 'Installation introuvable.')
    return redirect('installation-list')


# --- Événements -------------------------------------------------------------

def _action_add_event(view, request, inst, qs):
    label = request.POST.get('label', '').strip()
    notes = request.POST.get('notes', '').strip()
    date_str = request.POST.get('date', '').strip()
    if not label:
        messages.error(request, "Le champ 'Événement' est requis.")
        return redirect(f"/installations/{inst.id}/{qs}")
    ev_date = _parse_datetime_jjmmaaaa_minuit(date_str)
    ev = InstallationEvent.objects.create(
        installation=inst,
        label=label,
        notes=notes,
        date=ev_date or timezone.now(),
        created_by=request.user,
        updated_by=request.user,
    )
    for f in request.FILES.getlist('attachments'):
        InstallationEventAttachment.objects.create(event=ev, file=f, created_by=request.user, updated_by=request.user)
    AuditLog.objects.create(actor=request.user, action='add_installation_event', details=f'installation_id={inst.id}, event_id={ev.id}')
    messages.success(request, 'Événement ajouté.')
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_edit_event(view, request, inst, qs):
    event_id = request.POST.get('event_id')
    try:
        ev = InstallationEvent.objects.get(pk=event_id, installation=inst)
    except InstallationEvent.DoesNotExist:
        messages.error(request, "Événement introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    ev.label = request.POST.get('label', ev.label).strip()
    ev.notes = request.POST.get('notes', ev.notes or '').strip()
    new_dt = _parse_datetime_jjmmaaaa_minuit(request.POST.get('date', '').strip())
    if new_dt is not None:
        ev.date = new_dt
    ev.updated_by = request.user
    ev.save()
    for f in request.FILES.getlist('attachments'):
        InstallationEventAttachment.objects.create(event=ev, file=f, created_by=request.user, updated_by=request.user)
    AuditLog.objects.create(actor=request.user, action='edit_installation_event', details=f'event_id={ev.id}')
    messages.success(request, "Événement mis à jour.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_event_attachment(view, request, inst, qs):
    event_id = request.POST.get('event_id')
    att_id = request.POST.get('attachment_id')
    try:
        ev = InstallationEvent.objects.get(pk=event_id, installation=inst)
    except InstallationEvent.DoesNotExist:
        messages.error(request, "Événement introuvable")
        return redirect(f"/installations/{inst.id}/")
    deleted = InstallationEventAttachment.objects.filter(event=ev, pk=att_id).delete()[0]
    if deleted:
        AuditLog.objects.create(actor=request.user, action='delete_installation_event_attachment', details=f'attachment_id={att_id}')
        messages.success(request, 'Pièce jointe supprimée.')
    else:
        messages.error(request, "Pièce jointe introuvable")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_event(view, request, inst, qs):
    event_id = request.POST.get('event_id')
    InstallationEvent.objects.filter(pk=event_id, installation=inst).delete()
    AuditLog.objects.create(actor=request.user, action='delete_installation_event', details=f'event_id={event_id}')
    messages.success(request, 'Événement supprimé.')
    return redirect(f"/installations/{inst.id}/{qs}")


# --- Entretien (plan de maintenance de l'installation) -----------------------

def _action_add_maintenance(view, request, inst, qs):
    periodicity = (request.POST.get('periodicity') or '').strip()
    title = (request.POST.get('title') or '').strip()
    description = (request.POST.get('description') or '').strip()
    # Parse durée HH:MM -> minutes
    try:
        hours = int((request.POST.get('planned_duration_hours') or '0') or 0)
    except Exception:
        hours = 0
    try:
        minutes = int((request.POST.get('planned_duration_minutes') or '0') or 0)
    except Exception:
        minutes = 0
    minutes = max(0, min(59, minutes))
    duration = max(0, hours * 60 + minutes)
    people = int((request.POST.get('people_count') or '1') or 1)
    competence = (request.POST.get('competence') or 'BORD').strip().upper()
    if competence not in ('BORD', 'SLM', 'INDUSTRIEL'):
        competence = 'BORD'
    if not title:
        messages.error(request, "Le titre est requis.")
        return redirect(f"/installations/{inst.id}/{qs}")
    m = InstallationMaintenance.objects.create(
        installation=inst,
        periodicity=periodicity or '—',
        title=title,
        description=description,
        planned_duration_min=max(0, duration),
        people_count=max(1, people),
        competence=competence,
        created_by=request.user,
        updated_by=request.user,
    )
    for f in request.FILES.getlist('attachments'):
        InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
    AuditLog.objects.create(actor=request.user, action='add_installation_maintenance', details=f'maintenance_id={m.id}')
    messages.success(request, "Entretien ajouté.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_add_maintenance_attachment(view, request, inst, qs):
    mid = request.POST.get('maintenance_id')
    try:
        m = InstallationMaintenance.objects.get(pk=mid, installation=inst)
    except InstallationMaintenance.DoesNotExist:
        messages.error(request, "Tâche d'entretien introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    count = 0
    for f in request.FILES.getlist('attachments'):
        InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
        count += 1
    AuditLog.objects.create(actor=request.user, action='add_installation_maintenance_attachment', details=f'maintenance_id={m.id}; files={count}')
    messages.success(request, f"{count} pièce(s) jointe(s) ajoutée(s).")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_maintenance_attachment(view, request, inst, qs):
    mid = request.POST.get('maintenance_id')
    att_id = request.POST.get('attachment_id')
    try:
        m = InstallationMaintenance.objects.get(pk=mid, installation=inst)
    except InstallationMaintenance.DoesNotExist:
        messages.error(request, "Tâche d'entretien introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    deleted = InstallationMaintenanceAttachment.objects.filter(maintenance=m, pk=att_id).delete()[0]
    if deleted:
        AuditLog.objects.create(actor=request.user, action='delete_installation_maintenance_attachment', details=f'attachment_id={att_id}')
        messages.success(request, 'Pièce jointe supprimée.')
    else:
        messages.error(request, "Pièce jointe introuvable")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_maintenance(view, request, inst, qs):
    mid = request.POST.get('maintenance_id')
    InstallationMaintenance.objects.filter(pk=mid, installation=inst).delete()
    AuditLog.objects.create(actor=request.user, action='delete_installation_maintenance', details=f'maintenance_id={mid}')
    messages.success(request, "Entretien supprimé.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_edit_maintenance(view, request, inst, qs):
    mid = request.POST.get('maintenance_id')
    try:
        m = InstallationMaintenance.objects.get(pk=mid, installation=inst)
    except InstallationMaintenance.DoesNotExist:
        messages.error(request, "Tâche d'entretien introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    m.periodicity = (request.POST.get('periodicity') or m.periodicity or '').strip()
    m.title = (request.POST.get('title') or m.title or '').strip()
    m.description = (request.POST.get('description') or m.description or '').strip()
    try:
        hours = int((request.POST.get('planned_duration_hours') or '') or 0)
    except Exception:
        hours = m.planned_duration_min // 60
    try:
        minutes = int((request.POST.get('planned_duration_minutes') or '') or 0)
    except Exception:
        minutes = m.planned_duration_min % 60
    minutes = max(0, min(59, minutes))
    m.planned_duration_min = max(0, hours * 60 + minutes)
    try:
        people = int((request.POST.get('people_count') or '') or m.people_count)
    except Exception:
        people = m.people_count
    m.people_count = max(1, people)
    comp = (request.POST.get('competence') or m.competence or '').strip().upper()
    m.competence = comp if comp in ('BORD', 'SLM', 'INDUSTRIEL') else m.competence
    # Mode de suivi de l'échéance (calendaire / compteur / le premier des deux) et
    # champs associés. On mémorise l'ancien mode avant modification pour tracer
    # le changement dans l'historique de l'installation (InstallationEvent).
    ancien_mode = m.mode_declenchement
    ancien_mode_display = m.get_mode_declenchement_display()
    nouveau_mode = (request.POST.get('mode_declenchement') or '').strip().upper()
    if nouveau_mode in ModeDeclenchement.values:
        m.mode_declenchement = nouveau_mode
    intervalle_raw = (request.POST.get('intervalle') or '').strip()
    if intervalle_raw:
        try:
            m.intervalle = max(1, int(intervalle_raw))
        except ValueError:
            pass
    unite = (request.POST.get('unite_intervalle') or '').strip().upper()
    if unite in dict(InstallationMaintenance.UNITE_INTERVALLE_CHOICES):
        m.unite_intervalle = unite
    seuil_raw = (request.POST.get('seuil_heures') or '').strip()
    if seuil_raw:
        try:
            m.seuil_heures = max(0, int(seuil_raw))
        except ValueError:
            pass
    m.updated_by = request.user
    m.save()
    # Traçabilité du changement de mode de suivi : historisé via InstallationEvent
    # (système d'historique déjà existant, pas de nouveau mécanisme d'audit).
    if m.mode_declenchement != ancien_mode:
        utilisateur = request.user.get_full_name() or request.user.username
        InstallationEvent.objects.create(
            installation=inst,
            label="Changement mode de suivi maintenance",
            notes=(
                f"{m.title} : {ancien_mode_display} → {m.get_mode_declenchement_display()} "
                f"(par {utilisateur})"
            ),
            created_by=request.user,
            updated_by=request.user,
        )
    # Ajout de nouvelles pièces jointes lors de la modification
    for f in request.FILES.getlist('attachments'):
        InstallationMaintenanceAttachment.objects.create(maintenance=m, file=f, created_by=request.user, updated_by=request.user)
    AuditLog.objects.create(actor=request.user, action='edit_installation_maintenance', details=f'maintenance_id={m.id}')
    messages.success(request, "Entretien mis à jour.")
    return redirect(f"/installations/{inst.id}/{qs}")


# --- Pièces -------------------------------------------------------------

def _action_add_part(view, request, inst, qs):
    name = request.POST.get('designation', '').strip()
    nno = request.POST.get('nno', '').strip()
    reference = request.POST.get('reference', '').strip()
    marque = request.POST.get('marque', '').strip()
    if not name:
        messages.error(request, "La désignation de la pièce est requise.")
        return redirect(f"/installations/{inst.id}/{qs}")
    p = InstallationPart.objects.create(
        installation=inst,
        name=name,
        nno=nno,
        reference=reference,
        marque=marque,
        created_by=request.user,
        updated_by=request.user,
    )
    photo = request.FILES.get('photo')
    if photo:
        p.photo = photo
        p.save(update_fields=['photo'])
    AuditLog.objects.create(actor=request.user, action='add_installation_part', details=f'part_id={p.id}')
    messages.success(request, 'Pièce ajoutée.')
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_edit_part(view, request, inst, qs):
    part_id = request.POST.get('part_id')
    try:
        p = InstallationPart.objects.get(pk=part_id, installation=inst)
    except InstallationPart.DoesNotExist:
        messages.error(request, "Pièce introuvable")
        return redirect(f"/installations/{inst.id}/")
    p.name = request.POST.get('designation', p.name).strip()
    p.nno = request.POST.get('nno', p.nno or '').strip()
    p.reference = request.POST.get('reference', p.reference or '').strip()
    p.marque = request.POST.get('marque', p.marque or '').strip()
    photo = request.FILES.get('photo')
    if photo:
        p.photo = photo
    p.updated_by = request.user
    p.save()
    AuditLog.objects.create(actor=request.user, action='edit_installation_part', details=f'part_id={p.id}')
    messages.success(request, 'Pièce mise à jour.')
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_part(view, request, inst, qs):
    part_id = request.POST.get('part_id')
    InstallationPart.objects.filter(pk=part_id, installation=inst).delete()
    AuditLog.objects.create(actor=request.user, action='delete_installation_part', details=f'part_id={part_id}')
    messages.success(request, 'Pièce supprimée.')
    return redirect(f"/installations/{inst.id}/{qs}")


# --- Relevés heures de marche ---------------------------------------------

def _action_add_hour_reading(view, request, inst, qs):
    date_str = request.POST.get('date', '').strip()
    hours_str = request.POST.get('hours', '').strip()
    is_visit = bool(request.POST.get('is_visit'))
    if not hours_str:
        messages.error(request, "Le champ 'Heures' est requis.")
        return redirect(f"/installations/{inst.id}/{qs}")
    rd_date = _parse_date_jjmmaaaa(date_str)
    try:
        val = float(hours_str.replace(',', '.'))
        if val < 0:
            val = 0.0
    except Exception:
        messages.error(request, "Valeur d'heures invalide.")
        return redirect(f"/installations/{inst.id}/{qs}")
    try:
        reading = InstallationHourReading.objects.create(
            installation=inst,
            date=rd_date or timezone.localdate(),
            hours=val,
            is_visit=is_visit,
            created_by=request.user,
            updated_by=request.user,
        )
    except OperationalError:
        messages.error(request, "Base non à jour: appliquez les migrations (assets).")
        return redirect(f"/installations/{inst.id}/{qs}")
    AuditLog.objects.create(actor=request.user, action='add_installation_hour_reading', details=f'reading_id={reading.id}')
    messages.success(request, "Relevé d'heures ajouté.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_edit_hour_reading(view, request, inst, qs):
    rid = request.POST.get('reading_id')
    try:
        reading = InstallationHourReading.objects.get(pk=rid, installation=inst)
    except InstallationHourReading.DoesNotExist:
        messages.error(request, "Relevé introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    date_str = request.POST.get('date', '').strip()
    hours_str = request.POST.get('hours', '').strip()
    is_visit = bool(request.POST.get('is_visit'))
    parsed_date = _parse_date_jjmmaaaa(date_str)
    if parsed_date is not None:
        reading.date = parsed_date
    if hours_str:
        try:
            val = float(hours_str.replace(',', '.'))
            reading.hours = val if val >= 0 else 0.0
        except Exception:
            pass
    try:
        reading.is_visit = is_visit
        reading.updated_by = request.user
        reading.save()
    except OperationalError:
        messages.error(request, "Base non à jour: appliquez les migrations (assets).")
        return redirect(f"/installations/{inst.id}/{qs}")
    AuditLog.objects.create(actor=request.user, action='edit_installation_hour_reading', details=f'reading_id={reading.id}')
    messages.success(request, "Relevé mis à jour.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_hour_reading(view, request, inst, qs):
    rid = request.POST.get('reading_id')
    InstallationHourReading.objects.filter(pk=rid, installation=inst).delete()
    AuditLog.objects.create(actor=request.user, action='delete_installation_hour_reading', details=f'reading_id={rid}')
    messages.success(request, "Relevé supprimé.")
    return redirect(f"/installations/{inst.id}/{qs}")


# --- Relevés vibration ---------------------------------------------------

def _action_add_vibration(view, request, inst, qs):
    date_str = request.POST.get('date', '').strip()
    state = (request.POST.get('state') or '').strip().upper()
    note = request.POST.get('note', '').strip()
    if state not in ('A', 'B', 'C'):
        messages.error(request, "État vibratoire invalide (A/B/C).")
        return redirect(f"/installations/{inst.id}/{qs}")
    vb_date = _parse_date_jjmmaaaa(date_str) or timezone.localdate()
    try:
        reading = InstallationVibrationReading.objects.create(
            installation=inst,
            date=vb_date,
            state=state,
            note=note,
            created_by=request.user,
            updated_by=request.user,
        )
    except OperationalError:
        messages.error(request, "Base non à jour: appliquez les migrations (assets).")
        return redirect(f"/installations/{inst.id}/{qs}")
    AuditLog.objects.create(actor=request.user, action='add_installation_vibration', details=f'reading_id={reading.id}')
    messages.success(request, "Mesure de vibration ajoutée.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_edit_vibration(view, request, inst, qs):
    rid = request.POST.get('reading_id')
    try:
        vb = InstallationVibrationReading.objects.get(pk=rid, installation=inst)
    except InstallationVibrationReading.DoesNotExist:
        messages.error(request, "Mesure introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    date_str = request.POST.get('date', '').strip()
    state = (request.POST.get('state') or '').strip().upper()
    note = request.POST.get('note', '').strip()
    parsed_date = _parse_date_jjmmaaaa(date_str)
    if parsed_date is not None:
        vb.date = parsed_date
    if state in ('A', 'B', 'C'):
        vb.state = state
    vb.note = note
    try:
        vb.updated_by = request.user
        vb.save()
    except OperationalError:
        messages.error(request, "Base non à jour: appliquez les migrations (assets).")
        return redirect(f"/installations/{inst.id}/{qs}")
    AuditLog.objects.create(actor=request.user, action='edit_installation_vibration', details=f'reading_id={vb.id}')
    messages.success(request, "Mesure de vibration mise à jour.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_vibration(view, request, inst, qs):
    rid = request.POST.get('reading_id')
    InstallationVibrationReading.objects.filter(pk=rid, installation=inst).delete()
    AuditLog.objects.create(actor=request.user, action='delete_installation_vibration', details=f'reading_id={rid}')
    messages.success(request, "Mesure supprimée.")
    return redirect(f"/installations/{inst.id}/{qs}")


# --- Relevés isolement ----------------------------------------------------

def _action_add_isolation(view, request, inst, qs):
    date_str = request.POST.get('date', '').strip()
    ohm_str = request.POST.get('ohms', '').strip()
    note = request.POST.get('note', '').strip()
    if not ohm_str:
        messages.error(request, "La mesure (Ohm) est requise.")
        return redirect(f"/installations/{inst.id}/{qs}")
    iso_date = _parse_date_jjmmaaaa(date_str) or timezone.localdate()
    try:
        val = float(ohm_str.replace(',', '.'))
    except Exception:
        messages.error(request, "Valeur de mesure invalide.")
        return redirect(f"/installations/{inst.id}/{qs}")
    try:
        rd = InstallationIsolationReading.objects.create(
            installation=inst,
            date=iso_date,
            ohms=val,
            note=note,
            created_by=request.user,
            updated_by=request.user,
        )
    except OperationalError:
        messages.error(request, "Base non à jour: appliquez les migrations (assets).")
        return redirect(f"/installations/{inst.id}/{qs}")
    AuditLog.objects.create(actor=request.user, action='add_installation_isolation', details=f'reading_id={rd.id}')
    messages.success(request, "Mesure d'isolement ajoutée.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_edit_isolation(view, request, inst, qs):
    rid = request.POST.get('reading_id')
    try:
        rd = InstallationIsolationReading.objects.get(pk=rid, installation=inst)
    except InstallationIsolationReading.DoesNotExist:
        messages.error(request, "Mesure d'isolement introuvable")
        return redirect(f"/installations/{inst.id}/{qs}")
    date_str = request.POST.get('date', '').strip()
    ohm_str = request.POST.get('ohms', '').strip()
    note = request.POST.get('note', '').strip()
    parsed_date = _parse_date_jjmmaaaa(date_str)
    if parsed_date is not None:
        rd.date = parsed_date
    if ohm_str:
        try:
            val = float(ohm_str.replace(',', '.'))
            rd.ohms = val
        except Exception:
            pass
    rd.note = note
    try:
        rd.updated_by = request.user
        rd.save()
    except OperationalError:
        messages.error(request, "Base non à jour: appliquez les migrations (assets).")
        return redirect(f"/installations/{inst.id}/{qs}")
    AuditLog.objects.create(actor=request.user, action='edit_installation_isolation', details=f'reading_id={rd.id}')
    messages.success(request, "Mesure d'isolement mise à jour.")
    return redirect(f"/installations/{inst.id}/{qs}")


def _action_delete_isolation(view, request, inst, qs):
    rid = request.POST.get('reading_id')
    InstallationIsolationReading.objects.filter(pk=rid, installation=inst).delete()
    AuditLog.objects.create(actor=request.user, action='delete_installation_isolation', details=f'reading_id={rid}')
    messages.success(request, "Mesure d'isolement supprimée.")
    return redirect(f"/installations/{inst.id}/{qs}")


# --- Tableau de dispatch -----------------------------------------------------

# Utilisé par InstallationDetailView.post comme dict {action: handler}, à la
# place de la chaîne if/elif d'origine — les contrôles de rôle par action
# restent dans InstallationDetailView.post (MAINTENANCE_WRITE_ACTIONS /
# INSTALLATION_WRITE_ACTIONS / INSTALLATION_DELETE_ACTIONS), ce fichier ne
# contient que l'exécution de chaque action une fois autorisée.
ACTION_HANDLERS = {
    'edit_installation': _action_edit_installation,
    'delete_installation': _action_delete_installation,
    'add_event': _action_add_event,
    'edit_event': _action_edit_event,
    'delete_event_attachment': _action_delete_event_attachment,
    'delete_event': _action_delete_event,
    'add_maintenance': _action_add_maintenance,
    'add_maintenance_attachment': _action_add_maintenance_attachment,
    'delete_maintenance_attachment': _action_delete_maintenance_attachment,
    'delete_maintenance': _action_delete_maintenance,
    'edit_maintenance': _action_edit_maintenance,
    'add_part': _action_add_part,
    'edit_part': _action_edit_part,
    'delete_part': _action_delete_part,
    'add_hour_reading': _action_add_hour_reading,
    'edit_hour_reading': _action_edit_hour_reading,
    'delete_hour_reading': _action_delete_hour_reading,
    'add_vibration': _action_add_vibration,
    'edit_vibration': _action_edit_vibration,
    'delete_vibration': _action_delete_vibration,
    'add_isolation': _action_add_isolation,
    'edit_isolation': _action_edit_isolation,
    'delete_isolation': _action_delete_isolation,
}
