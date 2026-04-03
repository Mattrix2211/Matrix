from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import MaintenancePlan, MaintenanceOccurrence

@shared_task
def generate_occurrences(days_ahead: int = 90):
    today = timezone.localdate()
    until = today + timedelta(days=days_ahead)
    for plan in MaintenancePlan.objects.all():
        # naive generation: every_n_days from today for assets in scope
        if plan.scope == "ASSET_TYPE" and plan.asset_type:
            assets = plan.asset_type.assets.all()
        elif plan.scope == "ASSET" and plan.asset:
            assets = [plan.asset]
        else:
            continue
        for asset in assets:
            d = today
            while d <= until:
                MaintenanceOccurrence.objects.get_or_create(
                    plan=plan, asset=asset, scheduled_for=d,
                    defaults={"status": "PLANNED"}
                )
                d += timedelta(days=plan.every_n_days or 90)
    return {"status": "ok"}

@shared_task
def compute_overdue():
    today = timezone.localdate()
    qs = MaintenanceOccurrence.objects.filter(status__in=["PLANNED", "ASSIGNED"], scheduled_for__lt=today)
    return qs.update(status="OVERDUE")
