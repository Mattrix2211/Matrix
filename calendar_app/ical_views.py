from django.http import HttpResponse
from django.utils import timezone
from icalendar import Calendar, Event
from maintenance.models import MaintenanceOccurrence
from training.models import TrainingSession

def user_ical_feed(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)
    cal = Calendar()
    cal.add('prodid', '-//Matrix//calendar//FR')
    cal.add('version', '2.0')
    # Maintenance occurrences assigned to user
    for occ in MaintenanceOccurrence.objects.filter(assignees=request.user).select_related('asset', 'plan'):
        ev = Event()
        ev.add('summary', f"Maintenance: {occ.asset}")
        ev.add('dtstart', timezone.datetime.combine(occ.scheduled_for, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()))
        ev.add('dtend', timezone.datetime.combine(occ.scheduled_for, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()))
        ev.add('description', f"Plan: {occ.plan}")
        cal.add_component(ev)
    # Training sessions for user
    for s in TrainingSession.objects.filter(attendees=request.user).select_related('course'):
        ev = Event()
        ev.add('summary', f"Formation: {s.course.title}")
        ev.add('dtstart', s.scheduled_at)
        ev.add('dtend', s.scheduled_at)
        cal.add_component(ev)
    return HttpResponse(cal.to_ical(), content_type='text/calendar')
