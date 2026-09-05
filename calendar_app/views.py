from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q
from datetime import timedelta, datetime
from org.models import Ship, Service, Sector
from django.contrib.auth import get_user_model
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
from .models import PersonalEvent
from matrix.core.roles import user_role_level, RoleLevel
from matrix.core.scopes import scope_filters_for_user
from matrix.core.mixins import build_scope_q


def _perimetre_ticket(qs, user):
    """Restreint un queryset de tickets correctifs au périmètre (navire/
    service/secteur/section) de l'utilisateur, via le matériel mobile (asset)
    qui porte les 4 champs de périmètre. Réutilise scope_filters_for_user
    (aucun nouveau système de périmètre)."""
    filtres = scope_filters_for_user(user)
    if not filtres:
        return qs
    (cle, valeur), = filtres.items()
    return qs.filter(**{f"asset__{cle}": valeur})


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


def _appliquer_filtres_occurrences(qs, filters):
    """Applique les filtres navire/service/secteur/assigné choisis dans les
    menus déroulants du calendrier à un queryset d'occurrences de
    maintenance. Le périmètre (navire/service/secteur) est porté soit par
    l'actif mobile (asset), soit par l'installation fixe liée
    (installation_maintenance) — d'où le OU entre les deux chemins.
    Fonction commune à CalendarView (vue HTML) et calendar_events (API JSON
    consommée par FullCalendar), pour ne pas dupliquer cette logique."""
    if filters.get("ship"):
        qs = qs.filter(
            Q(asset__ship_id=filters["ship"])
            | Q(installation_maintenance__installation__ship_id=filters["ship"])
        )
    if filters.get("service"):
        qs = qs.filter(
            Q(asset__service_id=filters["service"])
            | Q(installation_maintenance__installation__service_id=filters["service"])
        )
    if filters.get("sector"):
        qs = qs.filter(
            Q(asset__sector_id=filters["sector"])
            | Q(installation_maintenance__installation__sector_id=filters["sector"])
        )
    if filters.get("user"):
        qs = qs.filter(assignees__id=filters["user"])
    return qs


def _evenements_personnels(user, start, end):
    """Événements personnels libres (rappels, notes) créés par l'utilisateur,
    dans la période affichée. Toujours restreints à leur propriétaire, quels
    que soient les filtres navire/service/secteur/utilisateur appliqués : un
    événement personnel n'a aucune portée organisationnelle, il n'est visible
    que par son créateur."""
    return PersonalEvent.objects.filter(owner=user, starts_at__date__range=(start, end))


def evenements_utilisateur_jour(user, day):
    """Événements de calendrier concernant précisément `user` pour le jour
    `day` : maintenances assignées, formations (assignées par un référent,
    réservées en libre-service, ou animées en tant que formateur), événements
    personnels libres. Même logique de filtrage que le filtre "user" de
    calendar_events/_collect_events (assignees, attendees | reservations |
    instructor, owner) — réutilisée ici par le digest quotidien « Ma
    journée »/« Ma journée de demain » (notifications.tasks) pour ne pas
    dupliquer l'agrégation. Le formateur d'une session doit voir sa journée
    de formation dans son digest même s'il n'est pas lui-même stagiaire."""
    maintenances = list(
        MaintenanceOccurrence.objects.filter(scheduled_for=day, assignees=user)
        .select_related("asset", "installation_maintenance__installation")
        .distinct()
    )
    formations = list(
        TrainingSession.objects.filter(scheduled_at__date=day)
        .filter(Q(attendees=user) | Q(reservations=user) | Q(instructor=user))
        .select_related("course")
        .distinct()
    )
    personnels = list(_evenements_personnels(user, day, day))
    return {"maintenances": maintenances, "formations": formations, "personnels": personnels}


def _peut_agir_occurrence(occ, user, ids_perimetre, niveau_role):
    """Vrai si `user` a le droit d'ouvrir/exécuter cette occurrence de
    maintenance depuis le popover du calendrier — RIGOUREUSEMENT la même
    règle que OccurrenceExecuteView (maintenance/web_views.py) : appartenir
    au périmètre de l'occurrence (matériel mobile ou installation fixe), ET
    (être assigné à l'occurrence OU être CHEF_SECTION et au-dessus). Ne
    duplique pas cette logique côté JavaScript : le booléen calculé ici est
    simplement transmis tel quel au calendrier via extendedProps."""
    if occ.id not in ids_perimetre:
        return False
    return niveau_role >= RoleLevel.CHEF_SECTION or user in occ.assignees.all()


def _peut_agir_ticket(ticket, ids_perimetre, niveau_role):
    """Vrai si l'utilisateur a le droit de faire transitionner ce ticket
    correctif depuis le popover du calendrier — même règle que
    TicketTransitionView/TicketAssignView (logistics/web_views.py) :
    appartenir au périmètre du ticket (matériel mobile) ET être CHEF_SECTION
    et au-dessus."""
    return ticket.pk in ids_perimetre and niveau_role >= RoleLevel.CHEF_SECTION


def _appliquer_filtres_tickets(qs, filters):
    """Applique les filtres navire/service/secteur choisis dans les menus
    déroulants du calendrier à un queryset de tickets correctifs. Fonction
    commune à CalendarView et calendar_events, pour ne pas dupliquer cette
    logique."""
    if filters.get("ship"):
        qs = qs.filter(asset__ship_id=filters["ship"])
    if filters.get("service"):
        qs = qs.filter(asset__service_id=filters["service"])
    if filters.get("sector"):
        qs = qs.filter(asset__sector_id=filters["sector"])
    return qs


class CalendarView(LoginRequiredMixin, TemplateView):
    """Calendrier central unique (colonne vertébrale, CLAUDE.md) : PAS de
    restriction automatique de périmètre à l'affichage, quel que soit le
    rôle — tout le monde voit tout par défaut ("vue globale"), et bascule en
    "vue personnelle" en choisissant son propre nom dans le filtre
    "Utilisateur" (ou en consultant "Ma journée"/le tableau de bord). C'est
    volontaire : un CHEF_SERVICE planifiant une session de formation doit
    voir TOUTES les sessions déjà programmées sur le calendrier (disponibilité
    des salles/formateurs), pas seulement celles où il est lui-même affecté.

    Sur les autres types d'événements (maintenance, tickets), les menus
    déroulants navire/service/secteur restent en plus disponibles pour
    affiner la vue globale par périmètre organisationnel — mais n'ont plus
    d'effet sur les sessions de formation depuis qu'une formation
    (TrainingCourse) est une fiche globale partagée par tous les navires
    (portabilité des qualifications) : une session de formation ne se
    rattache plus à un périmètre organisationnel précis, seule l'affectation
    personnelle du marin (attendees/reservations/instructor, cf.
    _perimetre_session ci-dessus) a un sens pour elle. La vue globale reste
    donc utile pour la formation comme pour les autres types d'événements —
    seul son critère de filtrage change (affectation personnelle plutôt que
    périmètre organisationnel)."""

    template_name = "calendar/index.html"

    def get(self, request, *args, **kwargs):
        view = request.GET.get("view", "month")
        date_str = request.GET.get("date")
        today = timezone.localdate()
        base = today
        if date_str:
            try:
                base = datetime.fromisoformat(date_str).date()
            except Exception:
                base = today

        filters = self._parse_filters(request)

        if view == "day":
            start, end = base, base
        elif view == "week":
            start = base - timedelta(days=base.weekday())
            end = start + timedelta(days=6)
        else:
            start = base.replace(day=1)
            # naïf: aller au mois suivant et reculer d’un jour
            if start.month == 12:
                next_month = start.replace(year=start.year + 1, month=1, day=1)
            else:
                next_month = start.replace(month=start.month + 1, day=1)
            end = next_month - timedelta(days=1)

        events = self._collect_events(request, start, end, filters)

        User = get_user_model()
        ctx = {
            "view": view,
            "date": base,
            "start": start,
            "end": end,
            "events": events,
            "ships": Ship.objects.all(),
            "services": Service.objects.select_related("ship").all(),
            "sectors": Sector.objects.select_related("service", "service__ship").all(),
            "users": User.objects.order_by("username").all(),
            "active_filters": filters,
            "mes_evenements_personnels": PersonalEvent.objects.filter(
                owner=request.user, starts_at__gte=timezone.now()
            ).order_by("starts_at")[:20],
        }
        return render(request, self.template_name, ctx)

    def _parse_filters(self, request):
        return {
            "ship": request.GET.get("ship") or None,
            "service": request.GET.get("service") or None,
            "sector": request.GET.get("sector") or None,
            "user": request.GET.get("user") or None,
            "type": request.GET.get("type") or None,
            "status": request.GET.get("status") or None,
        }

    def _collect_events(self, request, start, end, filters):
        events = []
        # Maintenance occurrences (préventif) : matériel mobile (asset) ou installation fixe.
        occ_qs = MaintenanceOccurrence.objects.select_related(
            "asset", "asset__ship", "asset__service", "asset__sector",
            "installation_maintenance", "installation_maintenance__installation",
            "installation_maintenance__installation__ship",
            "installation_maintenance__installation__service",
            "installation_maintenance__installation__sector",
        ).filter(scheduled_for__range=(start, end))
        occ_qs = _appliquer_filtres_occurrences(occ_qs, filters)
        for occ in occ_qs:
            events.append({
                "type": "maintenance",
                "title": f"Préventif - {occ.titre_affiche}",
                "start": occ.scheduled_for.isoformat(),
                "end": occ.scheduled_for.isoformat(),
                "url": f"/maintenance/occurrences/{occ.id}/execute/",
                "status": occ.status,
            })

        # Tickets (logistique) planifiés: on affiche tous, ou ceux avec statut PLANNED/IN_REPAIR/TESTING si on avait des dates; ici, on ne dispose pas d’échéance => montrer ouverts
        ticket_qs = CorrectiveTicket.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").exclude(status__in=["CLOSED", "CANCELLED"])  # proxy
        ticket_qs = _appliquer_filtres_tickets(ticket_qs, filters)
        for t in ticket_qs:
            events.append({
                "type": "ticket",
                "title": f"Ticket - {t.asset}",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "url": f"/logistics/tickets/{t.pk}/",
                "status": t.status,
            })

        # Sessions de formation : assignées par un référent (attendees),
        # réservées en libre-service par le marin (reservations, cf. T-FORM
        # réservation), OU animées en tant que formateur (instructor) — un
        # marin doit voir les trois sur son calendrier personnel (filtre
        # "Utilisateur" = lui-même), d'où le OU plutôt qu'un simple filtre sur
        # attendees. Même liste de champs que _perimetre_session ci-dessus
        # (utilisée pour l'autorisation de déplacement), pour rester cohérent.
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
            events.append({
                "type": "training",
                "title": f"Formation - {course_title}",
                "start": s.scheduled_at.isoformat(),
                "end": s.scheduled_at.isoformat(),
                "url": "/training/",  # placeholder detail si disponible
                "status": s.status,
            })

        # Événements personnels libres : uniquement ceux du marin connecté.
        if not filters.get("type") or filters["type"] == "personal":
            for pe in _evenements_personnels(request.user, start, end):
                events.append({
                    "type": "personal",
                    "title": f"Personnel - {pe.title}",
                    "start": pe.starts_at.isoformat(),
                    "end": pe.starts_at.isoformat(),
                    "url": "",
                    "status": None,
                })
        return events


def _parse_common_period(request):
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
    "maintenance": {"backgroundColor": "#0d6efd", "borderColor": "#0a58ca", "textColor": "#fff"},
    "ticket":      {"backgroundColor": "#fd7e14", "borderColor": "#d96307", "textColor": "#fff"},
    "training":    {"backgroundColor": "#198754", "borderColor": "#146c43", "textColor": "#fff"},
    "personal":    {"backgroundColor": "#6f42c1", "borderColor": "#59339d", "textColor": "#fff"},
}

def _couleur_evenement(ev_type, status=None):
    if ev_type == "maintenance" and status in _COULEUR_STATUT_MAINTENANCE:
        return _COULEUR_STATUT_MAINTENANCE[status]
    return _COULEUR_PAR_TYPE.get(ev_type, {"backgroundColor": "#6c757d", "borderColor": "#565e64", "textColor": "#fff"})


def calendar_events(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
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
            "title": f"🔧 {occ.titre_affiche}",
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
    ticket_qs = CorrectiveTicket.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").exclude(status__in=["CLOSED", "CANCELLED"])
    ticket_qs = _appliquer_filtres_tickets(ticket_qs, filters)
    if filters.get("status"):
        ticket_qs = ticket_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "ticket":
        ticket_qs = ticket_qs.none()
    # Même principe que pour les occurrences ci-dessus : périmètre calculé une
    # seule fois pour tout le lot de tickets affichés.
    ids_ticket_perimetre = set(
        ticket_qs.filter(build_scope_q(request.user, "asset__")).values_list("pk", flat=True)
    )
    for t in ticket_qs:
        if t.planned_for and (start <= t.planned_for <= end):
            couleur = _couleur_evenement("ticket")
            events.append({
                "id": f"tic-{t.pk}",
                "title": f"🛠 {t.asset}",
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
            "title": f"📚 {course_title}",
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
    # Événements personnels libres : uniquement ceux du marin connecté,
    # affichés à côté des événements auto-générés sur son calendrier.
    if not filters.get("type") or filters["type"] == "personal":
        for pe in _evenements_personnels(request.user, start, end):
            couleur = _couleur_evenement("personal")
            events.append({
                "id": f"per-{pe.id}",
                "title": f"📌 {pe.title}",
                "start": pe.starts_at.isoformat(),
                "end": pe.starts_at.isoformat(),
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
    return JsonResponse(events, safe=False)


def calendar_event_move(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
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
            return HttpResponseForbidden()
        try:
            # Le queryset est restreint au périmètre de l'appelant avant la
            # récupération : un ticket hors périmètre n'existe pas pour lui,
            # même s'il en devine l'identifiant.
            t = _perimetre_ticket(CorrectiveTicket.objects.all(), request.user).get(pk=ev_id)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseForbidden()
        t.planned_for = new_date
        t.save(update_fields=["planned_for"])
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
                return HttpResponseForbidden()
            perimetre = build_scope_q(request.user, "asset__", "installation_maintenance__installation__")
            if not MaintenanceOccurrence.objects.filter(perimetre, pk=ev_id).exists():
                return HttpResponseForbidden()
        occ.scheduled_for = new_date
        occ.save(update_fields=["scheduled_for"])
        return JsonResponse({"ok": True})
    if ev_type == "training" and ev_id:
        # CHEF_SECTION+ peut déplacer une session de formation, à condition
        # d'y être personnellement affecté (présent, inscrit en libre-service,
        # ou intervenant) — le filtrage n'est plus par périmètre
        # organisationnel mais par affectation personnelle (_perimetre_session
        # ci-dessus, cf. tâche Notion « Formation unique et portable entre
        # navires »).
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            return HttpResponseForbidden()
        try:
            # Le queryset est restreint au périmètre de l'appelant avant la
            # récupération : une session hors périmètre n'existe pas pour lui,
            # même s'il en devine l'identifiant.
            s = _perimetre_session(TrainingSession.objects.all(), request.user).get(pk=ev_id)
        except TrainingSession.DoesNotExist:
            return HttpResponseForbidden()
        # Utiliser l'heure fournie si présente, sinon 09:00 locale
        aware_dt = parsed_dt if timezone.is_aware(parsed_dt) else timezone.make_aware(parsed_dt)
        s.scheduled_at = aware_dt
        s.save(update_fields=["scheduled_at"])
        return JsonResponse({"ok": True})
    if ev_type == "personal" and ev_id:
        try:
            # Un événement personnel n'appartient qu'à son créateur : aucune
            # dérogation de rôle possible, contrairement aux autres types.
            pe = PersonalEvent.objects.get(pk=ev_id, owner=request.user)
        except PersonalEvent.DoesNotExist:
            return HttpResponseForbidden()
        aware_dt = parsed_dt if timezone.is_aware(parsed_dt) else timezone.make_aware(parsed_dt)
        pe.starts_at = aware_dt
        pe.save(update_fields=["starts_at"])
        return JsonResponse({"ok": True})
    return HttpResponseBadRequest("Unsupported event type")


def _parse_personal_event_datetime(date_str):
    """Convertit la valeur du champ datetime-local du formulaire en date/heure
    « aware », en tenant compte du fuseau horaire local du bord."""
    naive_dt = datetime.fromisoformat(date_str)
    if timezone.is_aware(naive_dt):
        return naive_dt
    return timezone.make_aware(naive_dt)


@login_required
def personal_event_save(request):
    """Crée ou modifie un événement personnel libre du marin connecté.
    Un identifiant présent dans le formulaire déclenche une modification
    (limitée aux événements dont il est propriétaire), son absence une
    création — un seul formulaire suffit pour les deux usages."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    titre = (request.POST.get("title") or "").strip()
    date_str = request.POST.get("starts_at") or ""
    note = (request.POST.get("note") or "").strip()
    event_id = request.POST.get("id") or None

    if not titre or not date_str:
        messages.error(request, "Le titre et la date sont obligatoires.")
        return redirect("calendar-index")
    try:
        starts_at = _parse_personal_event_datetime(date_str)
    except ValueError:
        messages.error(request, "Date invalide.")
        return redirect("calendar-index")

    if event_id:
        evenement = get_object_or_404(PersonalEvent, pk=event_id, owner=request.user)
        evenement.title = titre
        evenement.starts_at = starts_at
        evenement.note = note
        evenement.save(update_fields=["title", "starts_at", "note"])
        messages.success(request, "Événement personnel modifié.")
    else:
        PersonalEvent.objects.create(owner=request.user, title=titre, starts_at=starts_at, note=note)
        messages.success(request, "Événement personnel ajouté à votre calendrier.")
    return redirect("calendar-index")


@login_required
def personal_event_delete(request, pk):
    """Supprime un événement personnel — réservé à son propriétaire."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")
    evenement = get_object_or_404(PersonalEvent, pk=pk, owner=request.user)
    evenement.delete()
    messages.success(request, "Événement personnel supprimé.")
    return redirect("calendar-index")
