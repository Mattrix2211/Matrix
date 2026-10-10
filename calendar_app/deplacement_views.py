"""Déplacement d'un événement du calendrier par glisser-déposer (droits,
périmètre, journal d'audit) — découpage de calendar_app/views.py."""
from datetime import datetime

from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils import timezone

from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.scopes import scope_filters_for_user
from matrix.core.mixins import build_scope_q
from accounts.models import AuditLog
from .models import PersonalEvent


def _perimetre_ticket(qs, user):
    """Restreint un queryset de tickets correctifs au périmètre (navire/
    service/secteur/section) de l'utilisateur, via le matériel mobile (asset)
    ou l'installation fixe visés, qui portent tous deux les 4 champs de périmètre. Réutilise scope_filters_for_user
    (aucun nouveau système de périmètre)."""
    filtres = scope_filters_for_user(user)
    if not filtres:
        return qs
    (cle, valeur), = filtres.items()
    return qs.filter(Q(**{f"asset__{cle}": valeur}) | Q(**{f"installation__{cle}": valeur}))


def _perimetre_session(qs, user):
    """Restreint un queryset de sessions de formation à l'AFFECTATION
    PERSONNELLE de l'utilisateur — présent (attendees), inscrit en
    libre-service (reservations), ou intervenant (instructor). La formation
    (TrainingCourse) est désormais une fiche globale partagée par tous les
    navires (portabilité des qualifications, cf. tâche Notion « Formation
    unique et portable entre navires ») : un filtrage par périmètre
    navire/service/secteur n'a donc plus de sens ici, une session ne se
    rattachant plus organisationnellement à personne en particulier — seule
    l'affectation individuelle du marin compte. Les autres types
    d'événements du calendrier central (maintenance, tickets...) restent
    filtrés par périmètre organisationnel, non touchés ici."""
    return qs.filter(Q(attendees=user) | Q(reservations=user) | Q(instructor=user)).distinct()


def calendar_event_move(request):
    if not request.user.is_authenticated:
        raise PermissionDenied
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    # permission: CHEF_SECTION+ ou assigné (pour une occurrence)
    ev_type = request.POST.get("type")
    ev_id = request.POST.get("id")
    date_str = request.POST.get("date")
    try:
        parsed_dt = datetime.fromisoformat(date_str)
        new_date = parsed_dt.date()
    except Exception:
        return HttpResponseBadRequest("Invalid date")
    if ev_type == "ticket" and ev_id:
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            # Le queryset est restreint au périmètre de l'appelant avant la
            # récupération : un ticket hors périmètre n'existe pas pour lui,
            # même s'il en devine l'identifiant.
            t = _perimetre_ticket(CorrectiveTicket.objects.all(), request.user).get(pk=ev_id)
        except CorrectiveTicket.DoesNotExist:
            raise PermissionDenied
        t.planned_for = new_date
        t.save(update_fields=["planned_for"])
        # Journal d'audit transverse : modification de la planification d'un
        # ticket depuis le calendrier central, potentiellement par un chef
        # non assigné au ticket — cf. tâche Notion « Unifier les modèles
        # d'historique/audit ».
        AuditLog.objects.create(
            actor=request.user, action="calendar_move_ticket",
            details=f"ticket={t.pk}; planned_for={new_date.isoformat()}",
        )
        return JsonResponse({"ok": True})
    if ev_type == "maintenance" and ev_id:
        try:
            occ = MaintenanceOccurrence.objects.get(pk=ev_id)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest("Occurrence not found")
        est_assigne = request.user in occ.assignees.all()
        if not est_assigne:
            # Un utilisateur non assigné doit être CHEF_SECTION+ ET l'occurrence
            # doit appartenir à son périmètre (via le matériel mobile ou
            # l'installation fixe rattachée) — un assigné garde toujours la main
            # sur sa propre occurrence, quel que soit son rôle ou son périmètre.
            if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
                raise PermissionDenied
            perimetre = build_scope_q(request.user, "asset__", "installation_maintenance__installation__")
            if not MaintenanceOccurrence.objects.filter(perimetre, pk=ev_id).exists():
                raise PermissionDenied
        occ.scheduled_for = new_date
        occ.save(update_fields=["scheduled_for"])
        if not est_assigne:
            # Journal d'audit transverse : seul le cas d'un chef qui replanifie
            # l'occurrence d'un TIERS est tracé (action à enjeu, cf. tâche
            # Notion « Unifier les modèles d'historique/audit ») — un assigné
            # qui déplace sa propre occurrence reste un geste courant,
            # équivalent à un événement personnel.
            AuditLog.objects.create(
                actor=request.user, action="calendar_move_occurrence",
                details=f"occurrence={occ.pk}; scheduled_for={new_date.isoformat()}",
            )
        return JsonResponse({"ok": True})
    if ev_type == "training" and ev_id:
        # CHEF_SECTION+ peut déplacer une session de formation, à condition
        # d'y être personnellement affecté (présent, inscrit en libre-service,
        # ou intervenant) — le filtrage n'est plus par périmètre
        # organisationnel mais par affectation personnelle (_perimetre_session
        # ci-dessus, cf. tâche Notion « Formation unique et portable entre
        # navires »).
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied
        try:
            # Le queryset est restreint au périmètre de l'appelant avant la
            # récupération : une session hors périmètre n'existe pas pour lui,
            # même s'il en devine l'identifiant.
            s = _perimetre_session(TrainingSession.objects.all(), request.user).get(pk=ev_id)
        except TrainingSession.DoesNotExist:
            raise PermissionDenied
        # Utiliser l'heure fournie si présente, sinon 09:00 locale
        aware_dt = parsed_dt if timezone.is_aware(parsed_dt) else timezone.make_aware(parsed_dt)
        s.scheduled_at = aware_dt
        s.save(update_fields=["scheduled_at"])
        # Journal d'audit transverse : replanification d'une session de
        # formation partagée (impacte tous les inscrits/présents), cf. tâche
        # Notion « Unifier les modèles d'historique/audit ».
        AuditLog.objects.create(
            actor=request.user, action="calendar_move_training_session",
            details=f"session={s.pk}; course={s.course_id}; scheduled_at={aware_dt.isoformat()}",
        )
        return JsonResponse({"ok": True})
    if ev_type == "personal" and ev_id:
        try:
            # Un événement personnel n'appartient qu'à son créateur : aucune
            # dérogation de rôle possible, contrairement aux autres types.
            pe = PersonalEvent.objects.get(pk=ev_id, owner=request.user)
        except PersonalEvent.DoesNotExist:
            raise PermissionDenied
        aware_dt = parsed_dt if timezone.is_aware(parsed_dt) else timezone.make_aware(parsed_dt)
        champs_modifies = ["starts_at"]
        # Date de fin optionnelle : envoyée par le redimensionnement par
        # glisser (eventResize) de la vue calendrier, absente lors d'un
        # simple déplacement (eventDrop) — même endpoint pour les deux, comme
        # pour les autres types d'événements ci-dessus.
        end_date_str = request.POST.get("end_date")
        if end_date_str:
            try:
                parsed_end = datetime.fromisoformat(end_date_str)
            except ValueError:
                return HttpResponseBadRequest("Date de fin invalide")
            aware_end = parsed_end if timezone.is_aware(parsed_end) else timezone.make_aware(parsed_end)
            if aware_end <= aware_dt:
                return HttpResponseBadRequest("La date de fin doit être postérieure à la date de début.")
            pe.ends_at = aware_end
            champs_modifies.append("ends_at")
        elif pe.ends_at:
            # Simple déplacement (eventDrop, sans redimensionnement) d'un
            # événement qui a déjà une durée : on décale la date de fin du
            # même delta que la date de début, pour conserver la durée —
            # comportement standard d'un calendrier. Sans ce décalage,
            # ends_at resterait figé sur son ancienne valeur et pourrait
            # devenir antérieur à starts_at (incohérence silencieuse en
            # base, cf. régression signalée par le QA).
            delta = aware_dt - pe.starts_at
            pe.ends_at = pe.ends_at + delta
            champs_modifies.append("ends_at")
        pe.starts_at = aware_dt
        pe.save(update_fields=champs_modifies)
        return JsonResponse({"ok": True})
    return HttpResponseBadRequest("Unsupported event type")
