from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import JSONField
from bordops.core.models import TimeStampedModel

User = get_user_model()

class Ship(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    archived = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Service(TimeStampedModel):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    archived = models.BooleanField(default=False)

    class Meta:
        unique_together = ("ship", "name")

    def __str__(self):
        return f"{self.ship} / {self.name}"

class Sector(TimeStampedModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="sectors")
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=7, default="#0d6efd")
    archived = models.BooleanField(default=False)

    class Meta:
        unique_together = ("service", "name")

    def __str__(self):
        return f"{self.service} / {self.name}"

class Section(TimeStampedModel):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=255)
    archived = models.BooleanField(default=False)

    class Meta:
        unique_together = ("sector", "name")

    def __str__(self):
        return f"{self.sector} / {self.name}"

class SectorConfig(TimeStampedModel):
    sector = models.OneToOneField(Sector, on_delete=models.CASCADE, related_name="config")
    ui_preferences = JSONField(default=dict, blank=True)
    status_overrides = JSONField(default=dict, blank=True)
    alert_thresholds = JSONField(default=dict, blank=True)
    dashboard_widgets = JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Config {self.sector}"


class DynamicFieldDefinition(TimeStampedModel):
    TYPE_CHOICES = (
        ("text", "Texte"),
        ("number", "Nombre"),
        ("date", "Date"),
        ("choice", "Choix"),
        ("checkbox", "Case à cocher"),
    )
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="dynamic_fields")
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    required = models.BooleanField(default=False)
    unit = models.CharField(max_length=20, blank=True, default="")
    choices = JSONField(default=list, blank=True)
    applies_to = models.CharField(max_length=50, blank=True, default="", help_text="asset_type|checklist_template")

    def __str__(self):
        return f"{self.name} ({self.sector})"
