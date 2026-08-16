from django.http import HttpResponse
from django.utils import timezone
from icalendar import Calendar, Event
from maintenance.models import MaintenanceOccurrence
from training.models import TrainingSession
from calendar_app.views import _titre_occurrence

def user_ical_feed(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    cal = Calendar()
    cal.add('prodid', '-//Matrix//calendar//FR')
    cal.add('version', '2.0')
    # Occurrences de maintenance assignées à l'utilisateur : matériel mobile
    # (plan + asset) ou installation fixe (installation_maintenance).
    occ_qs = MaintenanceOccurrence.objects.filter(assignees=request.user).select_related(
        'asset', 'plan', 'installation_maintenance', 'installation_maintenance__installation',
    )
    for occ in occ_qs:
        ev = Event()
        ev.add('summary', f"Maintenance: {_titre_occurrence(occ)}")
        ev.add('dtstart', timezone.datetime.combine(occ.scheduled_for, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()))
        ev.add('dtend', timezone.datetime.combine(occ.scheduled_for, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()))
        description = f"Plan: {occ.plan}" if occ.plan_id else f"Entretien installation: {occ.installation_maintenance.title}"
        ev.add('description', description)
        cal.add_component(ev)
    # Training sessions for user
    for s in TrainingSession.objects.filter(attendees=request.user).select_related('course'):
        ev = Event()
        ev.add('summary', f"Formation: {s.course.title}")
        ev.add('dtstart', s.scheduled_at)
        ev.add('dtend', s.scheduled_at)
        cal.add_component(ev)
    return HttpResponse(cal.to_ical(), content_type='text/calendar')
