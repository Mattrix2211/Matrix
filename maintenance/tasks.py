from celery import shared_task
from django.core.management import call_command
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

@shared_task
def generate_installation_occurrences(days_ahead: int = 90):
    """Génère les occurrences de maintenance (calendrier et/ou compteur) pour les
    installations fixes, équivalent de generate_occurrences pour le matériel mobile.

    Enveloppe la commande de gestion du même nom (qui porte toute la logique métier
    et ses tests) afin de la rendre planifiable quotidiennement via Celery Beat.
    """
    call_command("generate_installation_occurrences", days_ahead=days_ahead)
    return {"status": "ok"}
