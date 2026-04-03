from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Notification
from training.models import TrainingRecord
from maintenance.models import MaintenanceOccurrence

@shared_task
def notify_expiring_training(days_list=(30, 60, 90)):
    today = timezone.localdate()
    for days in days_list:
        target = today + timedelta(days=days)
        for rec in TrainingRecord.objects.filter(expires_at=target).select_related('user', 'course'):
            Notification.objects.get_or_create(
                user=rec.user,
                verb=f"Formation '{rec.course.title}' expire dans {days} jours"
            )
    return {"status": "ok"}

@shared_task
def notify_overdue_occurrences():
    for occ in MaintenanceOccurrence.objects.filter(status='OVERDUE').select_related('plan'):
        for u in occ.assignees.all():
            Notification.objects.get_or_create(user=u, verb=f"Occurrence en retard: {occ.id}")
    return {"status": "ok"}
