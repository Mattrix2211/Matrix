import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import JSONField
from matrix.core.models import TimeStampedModel, OwnedModel
from org.models import Ship, Service, Sector, Section

User = get_user_model()

class InstallationBigrameChoice(models.Model):
    name = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Location(TimeStampedModel):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")

    class Meta:
        unique_together = ("ship", "name", "parent")

    def __str__(self):
        return self.name

class AssetType(TimeStampedModel):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="asset_types")

    class Meta:
        unique_together = ("sector", "name")

    def __str__(self):
        return f"{self.name} ({self.sector})"

class ChecklistTemplate(TimeStampedModel):
    name = models.CharField(max_length=255)
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="checklist_templates")
    asset_type = models.ForeignKey(AssetType, null=True, blank=True, on_delete=models.SET_NULL, related_name="checklist_templates")

    def __str__(self):
        return f"{self.name} ({self.sector})"

class ChecklistItemTemplate(TimeStampedModel):
    CHECK_TYPES = (
        ("checkbox", "Case à cocher"),
        ("number", "Numérique"),
        ("date", "Date"),
        ("text", "Texte"),
    )
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="items")
    label = models.CharField(max_length=255)
    field_type = models.CharField(max_length=20, choices=CHECK_TYPES, default="checkbox")
    required = models.BooleanField(default=False)
    requires_photo = models.BooleanField(default=False)
    unit = models.CharField(max_length=50, blank=True, default="")
    choices = JSONField(default=list, blank=True)
    order = models.PositiveIntegerField(default=0)

class AssetChecklistOverride(TimeStampedModel):
    asset = models.ForeignKey("Asset", on_delete=models.CASCADE, related_name="checklist_overrides")
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE, related_name="asset_overrides")
    extra_items = JSONField(default=list, blank=True)
    overrides = JSONField(default=dict, blank=True)

class Asset(TimeStampedModel, OwnedModel):
    STATUS = (
        ("OK", "OK"),
        ("IN_SERVICE", "En service"),
        ("OUT_OF_SERVICE", "Hors service"),
        ("FAULTY", "Défectueux"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT, related_name="assets")
    serial_number = models.CharField(max_length=255, blank=True, default="")
    internal_id = models.CharField(max_length=255, blank=True, default="")
    designation = models.CharField(max_length=255, blank=True, default="")
    nno = models.CharField(max_length=255, blank=True, default="")
    reference = models.CharField(max_length=255, blank=True, default="")
    marque = models.CharField(max_length=255, blank=True, default="")
    gisement = models.CharField(max_length=255, blank=True, default="")
    local = models.CharField(max_length=255, blank=True, default="")
    photo = models.FileField(upload_to="asset_photos/", null=True, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, related_name="assets")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="assets")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="assets")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="assets")
    status = models.CharField(max_length=32, choices=STATUS, default="OK")
    criticality = models.PositiveSmallIntegerField(default=1)
    folder = models.ForeignKey('AssetFolder', null=True, blank=True, on_delete=models.SET_NULL, related_name='assets')

    def __str__(self):
        return f"{self.asset_type.name} #{self.internal_id or self.serial_number or self.id}"

class AssetDocument(TimeStampedModel, OwnedModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="asset_docs/")
    name = models.CharField(max_length=255)


class Installation(TimeStampedModel, OwnedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    designation = models.CharField(max_length=255)
    reference = models.CharField(max_length=255, blank=True, default="")
    marque = models.CharField(max_length=255, blank=True, default="")
    gisement = models.CharField(max_length=255, blank=True, default="")
    local = models.CharField(max_length=255, blank=True, default="")
    bigrame = models.ForeignKey(InstallationBigrameChoice, null=True, blank=True, on_delete=models.SET_NULL, related_name="installations")
    photo = models.FileField(upload_to="installation_photos/", null=True, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, related_name="installations")
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, related_name="installations")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="installations")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="installations")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="installations")
    # Paramètres vibration: nombre de jours avant prochaine mesure selon l'état
    vib_days_a = models.PositiveIntegerField(default=180)
    vib_days_b = models.PositiveIntegerField(default=90)
    vib_days_c = models.PositiveIntegerField(default=30)
    ISO_PERIODICITY_CHOICES = (
        ("M", "Mensuel"),
        ("T", "Trimestriel"),
        ("A", "Annuel"),
    )
    iso_periodicity = models.CharField(max_length=1, choices=ISO_PERIODICITY_CHOICES, default="M")

    class Meta:
        ordering = ["ship__name", "service__name", "sector__name", "section__name", "designation"]

    def __str__(self):
        return f"{self.designation} ({self.ship} / {self.service} / {self.sector})"


class AssetFolder(TimeStampedModel, OwnedModel):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    photo = models.FileField(upload_to="folder_photos/", null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

# Historique des installations
class InstallationEvent(TimeStampedModel, OwnedModel):
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="events")
    date = models.DateTimeField(default=timezone.now)
    label = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.installation} - {self.label}"

class InstallationEventAttachment(TimeStampedModel, OwnedModel):
    event = models.ForeignKey(InstallationEvent, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="installation_events/")
    name = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.name or self.file.name

    @property
    def filename(self) -> str:
        try:
            import os
            base = os.path.basename(self.name or self.file.name or "")
            return base
        except Exception:
            return self.name or self.file.name

# Pièces liées à une installation
class InstallationPart(TimeStampedModel, OwnedModel):
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="parts")
    name = models.CharField(max_length=255)
    nno = models.CharField(max_length=255, blank=True, default="")
    reference = models.CharField(max_length=255, blank=True, default="")
    marque = models.CharField(max_length=255, blank=True, default="")
    photo = models.FileField(upload_to="installation_parts/", null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

# Mesures d'isolement (Ohm)
class InstallationIsolationReading(TimeStampedModel, OwnedModel):
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="isolation_readings")
    date = models.DateField(default=timezone.localdate)
    ohms = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.installation} - {self.date} = {self.ohms} Ω"

# Heures de marche (relevés cumulés)
class InstallationHourReading(TimeStampedModel, OwnedModel):
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="hour_readings")
    date = models.DateField(default=timezone.localdate)
    hours = models.DecimalField(max_digits=10, decimal_places=2)
    is_visit = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.installation} - {self.date}: {self.hours} h"

# Vibrations (mesures qualitatives A/B/C avec note)
class InstallationVibrationReading(TimeStampedModel, OwnedModel):
    STATE_A = 'A'
    STATE_B = 'B'
    STATE_C = 'C'
    STATE_CHOICES = [
        (STATE_A, 'A'),
        (STATE_B, 'B'),
        (STATE_C, 'C'),
    ]

    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="vibration_readings")
    date = models.DateField(default=timezone.localdate)
    state = models.CharField(max_length=1, choices=STATE_CHOICES)
    note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.installation} - {self.date}: {self.state}"

# Champs personnalisés d'une installation (infos libres)
class InstallationExtraField(TimeStampedModel, OwnedModel):
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="extra_fields")
    label = models.CharField(max_length=255)
    value = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "label"]

    def __str__(self):
        return f"{self.installation} - {self.label}"

# Entretien préventif d'une installation
class InstallationMaintenance(TimeStampedModel, OwnedModel):
    COMPETENCE_CHOICES = (
        ("BORD", "Bord"),
        ("SLM", "SLM"),
        ("INDUSTRIEL", "Industriel"),
    )
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="maintenances")
    periodicity = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    planned_duration_min = models.PositiveIntegerField(default=0)
    people_count = models.PositiveSmallIntegerField(default=1)
    competence = models.CharField(max_length=16, choices=COMPETENCE_CHOICES, default="BORD")

    class Meta:
        ordering = ["periodicity", "title"]

    def __str__(self):
        return f"{self.installation} - {self.title} ({self.periodicity})"

class InstallationMaintenanceAttachment(TimeStampedModel, OwnedModel):
    maintenance = models.ForeignKey(InstallationMaintenance, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="installation_maintenance/")
    name = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.name or self.file.name

    @property
    def filename(self) -> str:
        try:
            import os
            base = os.path.basename(self.name or self.file.name or "")
            return base
        except Exception:
            return self.name or self.file.name
