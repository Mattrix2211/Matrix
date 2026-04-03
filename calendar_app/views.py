from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from datetime import timedelta, datetime
from org.models import Ship, Service, Sector
from django.contrib.auth import get_user_model
from maintenance.models import MaintenanceOccurrence
from logistics.models import CorrectiveTicket
from training.models import TrainingSession
from bordops.core.roles import user_role_level, RoleLevel

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
        # Maintenance occurrences (préventif)
        occ_qs = MaintenanceOccurrence.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").filter(scheduled_for__range=(start, end))
        occ_qs = self._apply_scope_filters_occ(occ_qs, filters)
        for occ in occ_qs:
            events.append({
                "type": "maintenance",
                "title": f"Préventif - {occ.asset}",
                "start": occ.scheduled_for.isoformat(),
                "end": occ.scheduled_for.isoformat(),
                "url": f"/maintenance/occurrences/{occ.id}/execute/",
                "status": occ.status,
            })

        # Tickets (logistique) planifiés: on affiche tous, ou ceux avec statut PLANNED/IN_REPAIR/TESTING si on avait des dates; ici, on ne dispose pas d’échéance => montrer ouverts
        ticket_qs = CorrectiveTicket.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").exclude(status__in=["CLOSED", "CANCELLED"])  # proxy
        ticket_qs = self._apply_scope_filters_ticket(ticket_qs, filters)
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

    def _apply_scope_filters_occ(self, qs, filters):
        if filters.get("ship"):
            qs = qs.filter(asset__ship_id=filters["ship"])
        if filters.get("service"):
            qs = qs.filter(asset__service_id=filters["service"])
        if filters.get("sector"):
            qs = qs.filter(asset__sector_id=filters["sector"])
        if filters.get("user"):
            qs = qs.filter(assignees__id=filters["user"])
        return qs

    def _apply_scope_filters_ticket(self, qs, filters):
        if filters.get("ship"):
            qs = qs.filter(asset__ship_id=filters["ship"])
        if filters.get("service"):
            qs = qs.filter(asset__service_id=filters["service"])
        if filters.get("sector"):
            qs = qs.filter(asset__sector_id=filters["sector"])
        return qs


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
    # Occurrences de maintenance préventive
    occ_qs = MaintenanceOccurrence.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").filter(scheduled_for__range=(start, end))
    if filters.get("ship"):
        occ_qs = occ_qs.filter(asset__ship_id=filters["ship"])
    if filters.get("service"):
        occ_qs = occ_qs.filter(asset__service_id=filters["service"])
    if filters.get("sector"):
        occ_qs = occ_qs.filter(asset__sector_id=filters["sector"])
    if filters.get("user"):
        occ_qs = occ_qs.filter(assignees__id=filters["user"])
    if filters.get("status"):
        occ_qs = occ_qs.filter(status=filters["status"])
    if filters.get("type") and filters["type"] != "maintenance":
        occ_qs = occ_qs.none()
    for occ in occ_qs:
        couleur = _couleur_evenement("maintenance", occ.status)
        events.append({
            "id": f"occ-{occ.id}",
            "title": f"🔧 {occ.asset}",
            "start": occ.scheduled_for.isoformat(),
            "end": occ.scheduled_for.isoformat(),
            "url": f"/maintenance/occurrences/{occ.id}/execute/",
            "editable": user_role_level(request.user) >= RoleLevel.CHEF_SECTION,
            "extendedProps": {"type": "maintenance", "status": occ.status},
            **couleur,
        })
    # Tickets correctifs planifiés
    ticket_qs = CorrectiveTicket.objects.select_related("asset", "asset__ship", "asset__service", "asset__sector").exclude(status__in=["CLOSED", "CANCELLED"])
    if filters.get("ship"):
        ticket_qs = ticket_qs.filter(asset__ship_id=filters["ship"])
    if filters.get("service"):
        ticket_qs = ticket_qs.filter(asset__service_id=filters["service"])
    if filters.get("sector"):
        ticket_qs = ticket_qs.filter(asset__sector_id=filters["sector"])
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
        pk = ev_id
        try:
            t = CorrectiveTicket.objects.get(pk=pk)
        except CorrectiveTicket.DoesNotExist:
            return HttpResponseBadRequest("Ticket not found")
        t.planned_for = new_date
        t.save(update_fields=["planned_for"])
        return JsonResponse({"ok": True})
    if ev_type == "maintenance" and ev_id:
        try:
            occ = MaintenanceOccurrence.objects.get(pk=ev_id)
        except MaintenanceOccurrence.DoesNotExist:
            return HttpResponseBadRequest("Occurrence not found")
        if (request.user not in occ.assignees.all()) and (user_role_level(request.user) < RoleLevel.CHEF_SECTION):
            return HttpResponseForbidden()
        occ.scheduled_for = new_date
        occ.save(update_fields=["scheduled_for"])
        return JsonResponse({"ok": True})
    if ev_type == "training" and ev_id:
        # CHEF_SECTION+ peut déplacer les sessions de formation
        if user_role_level(request.user) < RoleLevel.CHEF_SECTION:
            return HttpResponseForbidden()
        try:
            s = TrainingSession.objects.get(pk=ev_id)
        except TrainingSession.DoesNotExist:
            return HttpResponseBadRequest("Session not found")
        # Utiliser l'heure fournie si présente, sinon 09:00 locale
        aware_dt = parsed_dt if timezone.is_aware(parsed_dt) else timezone.make_aware(parsed_dt)
        s.scheduled_at = aware_dt
        s.save(update_fields=["scheduled_at"])
        return JsonResponse({"ok": True})
    return HttpResponseBadRequest("Unsupported event type")
