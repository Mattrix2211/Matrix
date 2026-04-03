from django.db import models
from datetime import date, time
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from org.models import Ship, Service, Sector, Section
from matrix.core.models import TimeStampedModel

User = get_user_model()

class Roles(models.TextChoices):
    MASTER_ADMIN = "MASTER_ADMIN", "Administrateur général"
    ADMIN_NAVIRE = "ADMIN_NAVIRE", "Administrateur navire"
    COMMANDANT = "COMMANDANT", "Commandant"
    ETAT_MAJOR = "ETAT_MAJOR", "État-major"
    CHEF_SERVICE = "CHEF_SERVICE", "Chef de service"
    CHEF_SECTEUR = "CHEF_SECTEUR", "Chef de secteur"
    CHEF_SECTION = "CHEF_SECTION", "Chef de section"
    EQUIPIER = "EQUIPIER", "Équipier"

class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=32, choices=Roles.choices)
    grade = models.CharField(max_length=64, blank=True, default="")
    specialite = models.CharField(max_length=128, blank=True, default="")
    fonction_service = models.CharField(max_length=128, blank=True, default="")
    matricule = models.CharField(max_length=64, blank=True, default="")
    date_naissance = models.DateField(null=True, blank=True)
    notification_time = models.TimeField(default=time(8,0))

    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.SET_NULL, related_name="profiles")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.SET_NULL, related_name="profiles")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="profiles")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="profiles")

    allowed_sectors = models.ManyToManyField(Sector, blank=True, related_name="authorized_profiles")

    def __str__(self):
        return f"{self.user} ({self.role})"

    @property
    def scope(self):
        if self.section_id:
            return ("section", self.section_id)
        if self.sector_id:
            return ("sector", self.sector_id)
        if self.service_id:
            return ("service", self.service_id)
        if self.ship_id:
            return ("ship", self.ship_id)
        return (None, None)

    @property
    def age(self):
        if not self.date_naissance:
            return None
        today = date.today()
        years = today.year - self.date_naissance.year
        if (today.month, today.day) < (self.date_naissance.month, self.date_naissance.day):
            years -= 1
        return years

class GradeChoice(models.Model):
    name = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class SpecialityChoice(models.Model):
    name = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ServiceFunctionChoice(models.Model):
    name = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class RoleAvailability(models.Model):
    code = models.CharField(max_length=64, choices=Roles.choices, unique=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} ({'actif' if self.active else 'inactif'})"


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_actor")
    action = models.CharField(max_length=128)
    target_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_target_user")
    details = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.created_at} {self.actor} {self.action}"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    # Crée automatiquement un profil pour tout nouvel utilisateur
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={"role": Roles.EQUIPIER})
