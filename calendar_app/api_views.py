"""API JSON du calendrier (source d'événements FullCalendar) — découpage de
calendar_app/views.py."""
from datetime import datetime, timedelta

from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.utils import timezone

from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.mixins import build_scope_q
from matrix.core.icones import classe_icone
from .evenements_sources import (
    _absences_periode,
    _appliquer_filtres_occurrences,
    _appliquer_filtres_tickets,
    _creneaux_garde_assignes,
    _creneaux_quart_assignes,
    _evenements_personnels,
    _peut_agir_occurrence,
    _peut_agir_ticket,
    _rondes_a_faire,
    _taches_a_faire,
)


def _parse_common_period(request):
    """Détermine la période (start, end inclus) demandée par l'appelant.

    FullCalendar (event source de type URL) envoie automatiquement des
    paramètres `start`/`end` FRAIS à chaque navigation (Précédent/Aujourd'hui/
    Suivant, changement de vue...), même si le paramètre `date` transmis par
    le gabarit reste figé côté client sur sa valeur de chargement initial —
    c'est cette dernière valeur qu'on utilisait par erreur, ce qui figeait les
    événements affichés sur la période initiale (cf. bug Notion « Précédent/
    Aujourd'hui/Suivant ne rafraîchissent pas les événements affichés »).
    On donne donc la priorité à `start`/`end` quand ils sont fournis, avec un
    repli sur `view`+`date` sinon, pour ne pas casser d'éventuels autres
    appelants de cet endpoint qui n'enverraient que `view`+`date`."""
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")
    if start_str and end_str:
        try:
            start = datetime.fromisoformat(start_str[:10]).date()
            # FullCalendar envoie une borne de fin EXCLUSIVE (minuit du
            # lendemain du dernier jour affiché) : on la ramène au dernier
            # jour réellement inclus dans la grille, pour un filtrage
            # `__range` (inclusif des deux côtés) cohérent avec le reste du
            # code.
            fin_exclusive = datetime.fromisoformat(end_str[:10]).date()
            end = fin_exclusive - timedelta(days=1) if fin_exclusive > start else fin_exclusive
            return start, end
        except (ValueError, TypeError):
            pass  # repli sur view/date ci-dessous en cas de valeur invalide

    view = request.GET.get("view", "month")
    date_str = request.GET.get("date")
    today = timezone.localdate()
    base = today
    if date_str:
        try:
            base = datetime.fromisoformat(date_str).date()
        except Exception:
            base = today
    if view == "day":
        start, end = base, base
    elif view == "week":
        start = base - timedelta(days=base.weekday())
        end = start + timedelta(days=6)
    else:
        start = base.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1, day=1)
        else:
            next_month = start.replace(month=start.month + 1, day=1)
        end = next_month - timedelta(days=1)
    return start, end


_COULEUR_STATUT_MAINTENANCE = {
    "OVERDUE":            {"backgroundColor": "#dc3545", "borderColor": "#b02a37", "textColor": "#fff"},
    "DONE":               {"backgroundColor": "#6c757d", "borderColor": "#565e64", "textColor": "#fff"},
    "CANCELLED":          {"backgroundColor": "#adb5bd", "borderColor": "#9aa0a6", "textColor": "#333"},
    "WAITING_VALIDATION": {"backgroundColor": "#0dcaf0", "borderColor": "#0aa8cc", "textColor": "#000"},
}
_COULEUR_PAR_TYPE = {
    "maintenance":   {"backgroundColor": "#0d6efd", "borderColor": "#0a58ca", "textColor": "#fff"},
    "ticket":        {"backgroundColor": "#b8500a", "borderColor": "#964008", "textColor": "#fff"},
    "training":      {"backgroundColor": "#198754", "borderColor": "#146c43", "textColor": "#fff"},
    "personal":      {"backgroundColor": "#6f42c1", "borderColor": "#59339d", "textColor": "#fff"},
    # Teintes assombries par rapport à un simple "teal"/"pink" Bootstrap : un
    # texte blanc sur #20c997/#d63384 ne respecte pas le contraste WCAG AA
    # (ratio < 4.5:1) — #0b7285/#a61e4d passent largement (ratio > 5:1).
    "quart":         {"backgroundColor": "#0b7285", "borderColor": "#095c6b", "textColor": "#fff"},
    "service_garde": {"backgroundColor": "#a61e4d", "borderColor": "#84173d", "textColor": "#fff"},
    "tache":         {"backgroundColor": "#2b6a3f", "borderColor": "#1f4f2e", "textColor": "#fff"},
    "ronde":         {"backgroundColor": "#5f3dc4", "borderColor": "#4c2fa0", "textColor": "#fff"},
    "absence":       {"backgroundColor": "#7c4a03", "borderColor": "#5c3702", "textColor": "#fff"},
}

# Concept d'icône (table centrale matrix/core/icones.py) par type d'événement :
# le gabarit du calendrier affiche l'icône devant le titre (aucun emoji).
_CONCEPT_ICONE_PAR_TYPE = {
    "maintenance": "maintenance",
    "ticket": "ticket",
    "training": "formation",
    "quart": "quart",
    "service_garde": "garde",
    "ronde": "ronde",
    "tache": "tache",
    "personal": "personnel",
    "absence": "absence",
}


def _couleur_evenement(ev_type, status=None):
    if ev_type == "maintenance" and status in _COULEUR_STATUT_MAINTENANCE:
        return _COULEUR_STATUT_MAINTENANCE[status]
    return _COULEUR_PAR_TYPE.get(ev_type, {"backgroundColor": "#6c757d", "borderColor": "#565e64", "textColor": "#fff"})


def calendar_events(request):
    if not request.user.is_authenticated:
        raise PermissionDenied
    start, end = _parse_common_period(request)
    filters = {
        "ship": request.GET.get("ship") or None,
        "service": request.GET.get("service") or None,
        "sector": request.GET.get("sector") or None,
        "user": request.GET.get("user") or None,
        "type": request.GET.get("type") or None,
        "status": request.GET.get("status") or None,
    }
    events = []
    niveau_role = user_role_level(request.user)
    # Occurrences de maintenance préventive : matériel mobile (asset) ou installation fixe.
    occ_qs = MaintenanceOccurrence.objects.select_related(
        "asset", "asset__ship", "asset__service", "asset__sector",
        "installation_maintenance", "installation_maintenance__installation",
        "installation_maintenance__installation__ship",
        "installation_maintenance__installation__service",
        "installation_maintenance__installation__sector",
    ).prefetch_related("assignees").filter(scheduled_for__range=(start, end))
    occ_qs = _appliquer_filtres_occurrences(occ_qs, filters)
    if filters.get("status"):
        occ_qs = occ_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "maintenance":
        occ_qs = occ_qs.none()
    # Périmètre réel (matériel ou installation) de chaque occurrence — calculé
    # une seule fois pour tout le lot, réutilisé par _peut_agir_occurrence
    # pour ne pas déclencher une requête par événement.
    ids_occ_perimetre = set(
        occ_qs.filter(build_scope_q(request.user, "asset__", "installation_maintenance__installation__"))
        .values_list("id", flat=True)
    )
    for occ in occ_qs:
        couleur = _couleur_evenement("maintenance", occ.status)
        events.append({
            "id": f"occ-{occ.id}",
            "title": str(occ.titre_affiche),
            "start": occ.scheduled_for.isoformat(),
            "end": occ.scheduled_for.isoformat(),
            "url": f"/maintenance/occurrences/{occ.id}/execute/",
            "editable": niveau_role >= RoleLevel.CHEF_SECTION,
            "extendedProps": {
                "type": "maintenance",
                "status": occ.status,
                "peut_agir": _peut_agir_occurrence(occ, request.user, ids_occ_perimetre, niveau_role),
            },
            **couleur,
        })
    # Tickets correctifs planifiés
    ticket_qs = CorrectiveTicket.objects.select_related("asset", "installation").exclude(status__in=["CLOSED", "CANCELLED"])
    ticket_qs = _appliquer_filtres_tickets(ticket_qs, filters)
    if filters.get("status"):
        ticket_qs = ticket_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "ticket":
        ticket_qs = ticket_qs.none()
    # Même principe que pour les occurrences ci-dessus : périmètre calculé une
    # seule fois pour tout le lot de tickets affichés.
    ids_ticket_perimetre = set(
        ticket_qs.filter(build_scope_q(request.user, "asset__", "installation__")).values_list("pk", flat=True)
    )
    for t in ticket_qs:
        if t.planned_for and (start <= t.planned_for <= end):
            couleur = _couleur_evenement("ticket")
            events.append({
                "id": f"tic-{t.pk}",
                "title": str(t.equipement),
                "start": t.planned_for.isoformat(),
                "end": t.planned_for.isoformat(),
                "url": f"/logistics/tickets/{t.pk}/",
                "editable": niveau_role >= RoleLevel.CHEF_SECTION,
                "extendedProps": {
                    "type": "ticket",
                    "status": t.status,
                    "peut_agir": _peut_agir_ticket(t, ids_ticket_perimetre, niveau_role),
                },
                **couleur,
            })
    # Sessions de formation : assignées par un référent (attendees),
    # réservées en libre-service par le marin (reservations, cf. T-FORM
    # réservation), OU animées en tant que formateur (instructor) — mêmes
    # conventions que _collect_events ci-dessus.
    # Formation désormais globale (plus de secteur, cf. _perimetre_session
    # ci-dessus) : le filtre "sector" du calendrier ne s'applique plus aux
    # sessions de formation, uniquement aux autres types d'événements.
    ses_qs = TrainingSession.objects.select_related("course", "instructor").filter(scheduled_at__date__range=(start, end))
    if filters.get("user"):
        ses_qs = ses_qs.filter(
            Q(attendees__id=filters["user"]) | Q(reservations__id=filters["user"]) | Q(instructor__id=filters["user"])
        ).distinct()
    if filters.get("status"):
        ses_qs = ses_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "training":
        ses_qs = ses_qs.none()
    for s in ses_qs:
        course_title = getattr(s.course, "title", None) or getattr(s.course, "name", str(s.course))
        couleur = _couleur_evenement("training")
        events.append({
            "id": f"trn-{s.id}",
            "title": str(course_title),
            "start": s.scheduled_at.isoformat(),
            "end": s.scheduled_at.isoformat(),
            "url": "/training/",
            "editable": niveau_role >= RoleLevel.CHEF_SECTION,
            # Pas d'action rapide proposée pour une session de formation
            # depuis le popover : la validation d'une formation dépend du
            # marin concerné (peut_valider_formation exige un navire précis
            # par candidature, cf. training/models.py), pas de la session
            # dans son ensemble — reproduire ce calcul par événement ferait
            # perdre son sens à un simple booléen. Seul le lien "Voir la
            # fiche complète" est proposé pour ce type.
            "extendedProps": {"type": "training", "status": s.status, "peut_agir": False},
            **couleur,
        })
    # Créneaux de quart : affectation personnelle du marin (marin), pas de
    # périmètre organisationnel — même principe que les sessions de
    # formation ci-dessus. Seules les listes déjà PUBLIÉES sont montrées
    # (cf. _creneaux_quart_assignes). Aucune action rapide ni déplacement
    # depuis le calendrier pour cette V1 (l'échange de service est une tâche
    # séparée à venir, cf. quarts/models.py) : "editable" toujours faux.
    if not filters.get("type") or filters["type"] == "quart":
        quart_qs = _creneaux_quart_assignes(start, end, filters.get("user") or None, request.user)
        for c in quart_qs:
            couleur = _couleur_evenement("quart")
            events.append({
                "id": f"qrt-{c.id}",
                "title": str(c.poste),
                "start": c.debut.isoformat(),
                "end": c.fin.isoformat(),
                "url": f"/quarts/quart/{c.quart_id}/",
                "editable": False,
                "extendedProps": {"type": "quart", "status": None, "peut_agir": False},
                **couleur,
            })
    # Créneaux de service de garde : même principe que les créneaux de quart
    # ci-dessus (cf. _creneaux_garde_assignes).
    if not filters.get("type") or filters["type"] == "service_garde":
        garde_qs = _creneaux_garde_assignes(start, end, filters.get("user") or None, request.user)
        for c in garde_qs:
            couleur = _couleur_evenement("service_garde")
            events.append({
                "id": f"svc-{c.id}",
                "title": str(c.poste),
                "start": c.debut.isoformat(),
                "end": c.fin.isoformat(),
                "url": f"/quarts/garde/{c.service_garde_id}/",
                "editable": False,
                "extendedProps": {"type": "service_garde", "status": None, "peut_agir": False},
                **couleur,
            })
    # Absences/indisponibilités : même principe que les créneaux de quart/
    # garde ci-dessus (affectation personnelle, cf. _absences_periode).
    if not filters.get("type") or filters["type"] == "absence":
        absence_qs = _absences_periode(start, end, filters.get("user") or None, request.user)
        for a in absence_qs:
            couleur = _couleur_evenement("absence")
            events.append({
                "id": f"abs-{a.id}",
                "title": f"{a.type_absence}",
                "start": a.date_debut.isoformat(),
                "end": (a.date_fin + timedelta(days=1)).isoformat(),
                "url": "/absences/",
                "editable": False,
                "extendedProps": {"type": "absence", "status": a.statut, "peut_agir": False},
                **couleur,
            })
    # Rondes à faire : affectation personnelle (ou périmètre du marin).
    if not filters.get("type") or filters["type"] == "ronde":
        for ronde in _rondes_a_faire(request.user, start, end):
            events.append({
                "id": f"rnd-{ronde.id}",
                "title": str(ronde.nom),
                "start": ronde.date_prevue.isoformat(),
                "end": ronde.date_prevue.isoformat(),
                "url": f"/rondes/{ronde.id}/",
                "editable": False,
                "extendedProps": {"type": "ronde", "status": ronde.statut, "peut_agir": False},
                **_couleur_evenement("ronde"),
            })
    # Tâches attribuées par un chef : échéance sur le calendrier du marin.
    if not filters.get("type") or filters["type"] == "tache":
        for tache in _taches_a_faire(request.user, start, end):
            events.append({
                "id": f"tch-{tache.id}",
                "title": tache.titre,
                "start": tache.echeance.isoformat(),
                "end": tache.echeance.isoformat(),
                "url": f"/taches/{tache.id}/",
                "editable": False,
                "extendedProps": {"type": "tache", "status": tache.statut, "peut_agir": False},
                **_couleur_evenement("tache"),
            })
    # Événements personnels libres : uniquement ceux du marin connecté,
    # affichés à côté des événements auto-générés sur son calendrier.
    if not filters.get("type") or filters["type"] == "personal":
        for pe in _evenements_personnels(request.user, start, end):
            couleur = _couleur_evenement("personal")
            events.append({
                "id": f"per-{pe.id}",
                "title": str(pe.title),
                "start": pe.starts_at.isoformat(),
                # Sans date de fin renseignée, on retombe sur l'ancien
                # comportement (événement ponctuel, sans durée) — FullCalendar
                # affiche très bien un événement sans "end".
                "end": pe.ends_at.isoformat() if pe.ends_at else pe.starts_at.isoformat(),
                "url": "",
                "editable": True,
                # Un événement personnel n'appartient qu'à son créateur
                # (_evenements_personnels ne renvoie que ceux du marin
                # connecté) : la modification/suppression lui sont donc
                # toujours ouvertes ici. Vérifié explicitement (plutôt que
                # supposé) pour rester robuste si ce filtrage change un jour.
                "extendedProps": {
                    "type": "personal",
                    "status": None,
                    "note": pe.note,
                    "peut_agir": pe.owner_id == request.user.id,
                },
                **couleur,
            })
    for evenement in events:
        concept = _CONCEPT_ICONE_PAR_TYPE.get(evenement["extendedProps"]["type"])
        if concept:
            evenement["extendedProps"]["icone"] = classe_icone(concept)
    return JsonResponse(events, safe=False)
