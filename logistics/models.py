import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from matrix.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset

User = get_user_model()

class CorrectiveTicket(TimeStampedModel, OwnedModel):
    STATUS = (
        ("REPORTED", "Signalé"),
        ("DIAGNOSED", "Diagnostiqué"),
        ("WAITING_PARTS", "En attente pièces"),
        ("PLANNED", "Planifié"),
        ("IN_REPAIR", "En réparation"),
        ("TESTING", "En test"),
        ("RETURNED_TO_SERVICE", "Remis en service"),
        ("CLOSED", "Fermé"),
        ("BLOCKED", "Bloqué"),
        ("CANCELLED", "Annulé"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="tickets")
    created_by_text = models.CharField(max_length=255, blank=True, default="")
    reported_at = models.DateTimeField(default=timezone.now)
    planned_for = models.DateField(null=True, blank=True)
    description = models.TextField()
    severity = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=24, choices=STATUS, default="REPORTED")

class TicketStatusLog(TimeStampedModel):
    ticket = models.ForeignKey(CorrectiveTicket, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=24)
    new_status = models.CharField(max_length=24)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True, default="")

class PartRequest(TimeStampedModel, OwnedModel):
    STATUS = (
        ("OPEN", "Ouverte"),
        ("CLOSED", "Fermée"),
    )
    ticket = models.ForeignKey(CorrectiveTicket, on_delete=models.CASCADE, related_name="part_requests")
    requested_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    needed_by_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="OPEN")

class PartLineItem(TimeStampedModel):
    STATUS = (
        ("TO_ORDER", "À commander"),
        ("ORDERED", "Commandée"),
        ("SHIPPED", "Expédiée"),
        ("RECEIVED", "Reçue"),
        ("CONSUMED", "Consommée"),
        ("RETURNED", "Retournée"),
    )
    part_request = models.ForeignKey(PartRequest, on_delete=models.CASCADE, related_name="lines")
    reference = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS, default="TO_ORDER")
    vendor = models.CharField(max_length=255, blank=True, default="")
    order_number = models.CharField(max_length=255, blank=True, default="")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordered_at = models.DateField(null=True, blank=True)
    received_at = models.DateField(null=True, blank=True)
