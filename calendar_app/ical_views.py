from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from icalendar import Calendar, Event
from maintenance.models import MaintenanceOccurrence
from training.models import TrainingSession
from .models import PersonalEvent

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
        ev.add('summary', f"Maintenance: {occ.titre_affiche}")
        ev.add('dtstart', timezone.datetime.combine(occ.scheduled_for, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()))
        ev.add('dtend', timezone.datetime.combine(occ.scheduled_for, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()))
        description = f"Plan: {occ.plan}" if occ.plan_id else f"Entretien installation: {occ.installation_maintenance.title}"
        ev.add('description', description)
        cal.add_component(ev)
    # Sessions de formation de l'utilisateur : assignées par un référent
    # (attendees), réservées en libre-service (reservations, cf. T-FORM
    # réservation) OU animées en tant que formateur (instructor) — même
    # mécanisme de calendrier personnel que ci-dessus.
    ses_qs = TrainingSession.objects.filter(
        Q(attendees=request.user) | Q(reservations=request.user) | Q(instructor=request.user)
    ).select_related('course').distinct()
    for s in ses_qs:
        ev = Event()
        ev.add('summary', f"Formation: {s.course.title}")
        ev.add('dtstart', s.scheduled_at)
        ev.add('dtend', s.scheduled_at)
        cal.add_component(ev)
    # Événements personnels libres du marin (rappels, notes).
    for pe in PersonalEvent.objects.filter(owner=request.user):
        ev = Event()
        ev.add('summary', f"Personnel: {pe.title}")
        ev.add('dtstart', pe.starts_at)
        ev.add('dtend', pe.starts_at)
        if pe.note:
            ev.add('description', pe.note)
        cal.add_component(ev)
    return HttpResponse(cal.to_ical(), content_type='text/calendar')
