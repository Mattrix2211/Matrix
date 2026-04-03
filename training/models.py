from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from bordops.core.models import TimeStampedModel, OwnedModel
from org.models import Sector, Ship, Service, Section

User = get_user_model()

class TrainingCourse(TimeStampedModel):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="training_courses")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    validity_days = models.PositiveIntegerField(default=365)

    def __str__(self):
        return self.title

class TrainingRequirement(TimeStampedModel):
    ROLE_CHOICES = (
        ("COMMANDANT", "Commandant"),
        ("CHEF_SERVICE", "Chef de service"),
        ("CHEF_SECTEUR", "Chef de secteur"),
        ("CHEF_SECTION", "Chef de section"),
        ("EQUIPIER", "Équipier"),
    )
    applies_to_role = models.CharField(max_length=32, choices=ROLE_CHOICES, blank=True, default="")
    applies_to_ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.CASCADE)
    applies_to_service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.CASCADE)
    applies_to_sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.CASCADE)
    applies_to_section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.CASCADE)
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="requirements")
    required = models.BooleanField(default=True)

class TrainingSession(TimeStampedModel):
    STATUS = (
        ("PLANNED", "Planifiée"),
        ("DONE", "Effectuée"),
        ("CANCELLED", "Annulée"),
    )
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="sessions")
    scheduled_at = models.DateTimeField()
    instructor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="instructed_sessions")
    attendees = models.ManyToManyField(User, blank=True, related_name="training_sessions")
    location = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS, default="PLANNED")

class TrainingRecord(TimeStampedModel, OwnedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="training_records")
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="records")
    completed_at = models.DateField()
    expires_at = models.DateField()
    validated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="validated_training_records")
    attachment = models.FileField(upload_to="training_certificates/", null=True, blank=True)

    @staticmethod
    def compute_expiry(completed_at, validity_days):
        return completed_at + timezone.timedelta(days=validity_days)
