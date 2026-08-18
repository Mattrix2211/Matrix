from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q
from datetime import timedelta, datetime
from org.models import Ship, Service, Sector
from django.contrib.auth import get_user_model
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
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
    """Restreint un queryset de sessions de formation au périmètre de
    l'utilisateur, via la formation (course) qui n'est rattachée qu'à un
    secteur (une formation n'est jamais propre à une section précise).
    Si le périmètre de l'utilisateur est plus fin qu'un secteur (section),
    aucune correspondance n'est possible : on ne renvoie rien plutôt que de
    risquer une fuite hors périmètre."""
    filtres = scope_filters_for_user(user)
    if not filtres:
        return qs
    (cle, valeur), = filtres.items()
    chemins = {
        "sector_id": "course__sector_id",
        "service_id": "course__sector__service_id",
        "ship_id": "course__sector__service__ship_id",
    }
    chemin = chemins.get(cle)
    if not chemin:
        return qs.none()
    return qs.filter(**{chemin: valeur})


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

        # Sessions de formation
        ses_qs = TrainingSession.objects.select_related("course", "instructor").filter(scheduled_at__date__range=(start, end))
        if filters.get("sector"):
            ses_qs = ses_qs.filter(course__sector_id=filters["sector"])
        if filters.get("user"):
            ses_qs = ses_qs.filter(attendees__id=filters["user"])
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
    # Occurrences de maintenance préventive : matériel mobile (asset) ou installation fixe.
    occ_qs = MaintenanceOccurrence.objects.select_related(
        "asset", "asset__ship", "asset__service", "asset__sector",
        "installation_maintenance", "installation_maintenance__installation",
        "installation_maintenance__installation__ship",
        "installation_maintenance__installation__service",
        "installation_maintenance__installation__sector",
    ).filter(scheduled_for__range=(start, end))
    occ_qs = _appliquer_filtres_occurrences(occ_qs, filters)
    if filters.get("status"):
        occ_qs = occ_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "maintenance":
        occ_qs = occ_qs.none()
    for occ in occ_qs:
        couleur = _couleur_evenement("maintenance", occ.status)
        events.append({
            "id": f"occ-{occ.id}",
            "title": f"🔧 {occ.titre_affiche}",
            "start": occ.scheduled_for.isoformat(),
            "end": occ.scheduled_for.isoformat(),
            "url": f"/maintenance/occurrences/{occ.id}/execute/",
            "editable": user_role_level(request.user) >= RoleLevel.CHEF_SECTION,
            "extendedProps": {"type": "maintenance", "status": occ.status},
            **couleur,
        })
    # Tickets correctifs planifiés
    ticket_qs = CorrectiveTicket.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").exclude(status__in=["CLOSED", "CANCELLED"])
    ticket_qs = _appliquer_filtres_tickets(ticket_qs, filters)
    if filters.get("status"):
        ticket_qs = ticket_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "ticket":
        ticket_qs = ticket_qs.none()
    for t in ticket_qs:
        if t.planned_for and (start <= t.planned_for <= end):
            couleur = _couleur_evenement("ticket")
            events.append({
                "id": f"tic-{t.pk}",
                "title": f"🛠 {t.asset}",
                "start": t.planned_for.isoformat(),
                "end": t.planned_for.isoformat(),
                "url": f"/logistics/tickets/{t.pk}/",
                "editable": user_role_level(request.user) >= RoleLevel.CHEF_SECTION,
                "extendedProps": {"type": "ticket", "status": t.status},
                **couleur,
            })
    # Sessions de formation
    ses_qs = TrainingSession.objects.select_related("course", "instructor").filter(scheduled_at__date__range=(start, end))
    if filters.get("sector"):
        ses_qs = ses_qs.filter(course__sector_id=filters["sector"])
    if filters.get("user"):
        ses_qs = ses_qs.filter(attendees__id=filters["user"])
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
            "editable": user_role_level(request.user) >= RoleLevel.CHEF_SECTION,
            "extendedProps": {"type": "training", "status": s.status},
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
        # CHEF_SECTION+ peut déplacer les sessions de formation de son périmètre
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
    return HttpResponseBadRequest("Unsupported event type")
