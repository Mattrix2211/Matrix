from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import JSONField
from bordops.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset, ChecklistTemplate
from assets.models import AssetType
from django.db.models.signals import post_save
from django.dispatch import receiver
from logistics.models import CorrectiveTicket, TicketStatusLog

User = get_user_model()

class MaintenancePlan(TimeStampedModel, OwnedModel):
    SCOPE = (
        ("ASSET_TYPE", "Par type d'actif"),
        ("ASSET", "Par actif"),
    )
    scope = models.CharField(max_length=16, choices=SCOPE)
    asset_type = models.ForeignKey(AssetType, null=True, blank=True, on_delete=models.CASCADE, related_name="maintenance_plans")
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.CASCADE, related_name="maintenance_plans")
    name = models.CharField(max_length=255)
    every_n_days = models.PositiveIntegerField(default=90)
    expected_duration_min = models.PositiveIntegerField(default=30)
    checklist_template = models.ForeignKey(ChecklistTemplate, null=True, blank=True, on_delete=models.SET_NULL)
    requires_validation = models.BooleanField(default=False)
    validation_role = models.CharField(max_length=32, blank=True, default="CHEF_SECTION")

class MaintenanceOccurrence(TimeStampedModel, OwnedModel):
    STATUS = (
        ("PLANNED", "Planifiée"),
        ("ASSIGNED", "Assignée"),
        ("IN_PROGRESS", "En cours"),
        ("WAITING_VALIDATION", "En validation"),
        ("DONE", "Terminée"),
        ("OVERDUE", "En retard"),
        ("CANCELLED", "Annulée"),
    )
    plan = models.ForeignKey(MaintenancePlan, on_delete=models.CASCADE, related_name="occurrences")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="occurrences")
    scheduled_for = models.DateField()
    status = models.CharField(max_length=24, choices=STATUS, default="PLANNED")
    priority = models.PositiveSmallIntegerField(default=3)
    assignees = models.ManyToManyField(User, blank=True, related_name="assigned_occurrences")

class OccurrenceStatusLog(TimeStampedModel):
    occurrence = models.ForeignKey(MaintenanceOccurrence, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=24)
    new_status = models.CharField(max_length=24)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True, default="")

class MaintenanceExecution(TimeStampedModel, OwnedModel):
    CONFORMITY = (
        ("CONFORME", "Conforme"),
        ("NON_CONFORME", "Non conforme"),
        ("A_SURVEILLER", "À surveiller"),
    )
    occurrence = models.OneToOneField(MaintenanceOccurrence, on_delete=models.CASCADE, related_name="execution")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="executions")
    results = JSONField(default=dict, blank=True)
    measurements = JSONField(default=dict, blank=True)
    conformity = models.CharField(max_length=24, choices=CONFORMITY, blank=True, default="")
    notes = models.TextField(blank=True, default="")


@receiver(post_save, sender=MaintenanceExecution)
def create_corrective_on_non_conform(sender, instance: "MaintenanceExecution", created, **kwargs):
    if instance.conformity == "NON_CONFORME":
        occ = instance.occurrence
        asset = occ.asset
        ticket, created_ticket = CorrectiveTicket.objects.get_or_create(
            asset=asset,
            description=f"Anomalie détectée sur maintenance {occ.id}",
            defaults={"severity": 3}
        )
        if created_ticket:
            TicketStatusLog.objects.create(ticket=ticket, old_status="REPORTED", new_status="REPORTED")
