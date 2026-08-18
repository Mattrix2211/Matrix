from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from matrix.core.models import TimeStampedModel, OwnedModel
from org.models import Sector, Ship, Service, Section

User = get_user_model()

class TrainingCourse(TimeStampedModel):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="training_courses")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    validity_days = models.PositiveIntegerField(default=365)
    # Arbre de compétences : formations à valider avant de pouvoir suivre celle-ci.
    # related_name="unlocks" : les formations que la validation de celle-ci débloque.
    prerequisites = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="unlocks"
    )

    def __str__(self):
        return self.title


def _verifier_absence_de_cycle_prerequis(course, nouveaux_ids):
    """Empêche qu'une formation ait, directement ou indirectement, elle-même comme
    prérequis. Même principe que _verifier_absence_de_cycle (assets/models.py) pour
    la hiérarchie parent/enfant des équipements, adapté à un graphe à plusieurs
    branches (une formation peut avoir plusieurs prérequis) plutôt qu'une simple
    chaîne à parent unique : on remonte les prérequis des prérequis en largeur, et on
    refuse si la formation elle-même réapparaît dans cette chaîne."""
    a_visiter = list(nouveaux_ids)
    vus = set()
    while a_visiter:
        pk = a_visiter.pop()
        if pk == course.pk:
            raise ValidationError(
                "Rattachement invalide : cela créerait une boucle dans la chaîne de prérequis."
            )
        if pk in vus:
            continue
        vus.add(pk)
        suivants = TrainingCourse.objects.filter(pk=pk).values_list("prerequisites__id", flat=True)
        a_visiter.extend(i for i in suivants if i is not None)


@receiver(m2m_changed, sender=TrainingCourse.prerequisites.through)
def _bloquer_cycle_prerequis(sender, instance, action, pk_set, **kwargs):
    """Contrôle exécuté à chaque ajout de prérequis (formulaire web, API, admin,
    shell) : un ManyToManyField n'est pas validé par full_clean() une fois
    l'instance enregistrée, contrairement à une ForeignKey — ce signal est donc le
    seul point de passage garanti pour empêcher une boucle, quel que soit
    l'appelant."""
    if action == "pre_add" and pk_set:
        _verifier_absence_de_cycle_prerequis(instance, pk_set)


def _prerequis_manquants(user, course, reference_date=None):
    """Renvoie la liste des formations prérequises à `course` que `user` n'a pas
    validées avec un enregistrement (TrainingRecord) non expiré à la date de
    référence (aujourd'hui par défaut). Liste vide si tous les prérequis sont
    remplis, ou s'il n'y en a aucun."""
    reference_date = reference_date or timezone.localdate()
    prerequis = list(course.prerequisites.all())
    if not prerequis:
        return []
    valides_ids = set(
        TrainingRecord.objects.filter(
            user=user, course_id__in=[p.id for p in prerequis], expires_at__gte=reference_date
        ).values_list("course_id", flat=True)
    )
    return [p for p in prerequis if p.id not in valides_ids]

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


@receiver(m2m_changed, sender=TrainingSession.attendees.through)
def _bloquer_inscription_sans_prerequis(sender, instance, action, pk_set, **kwargs):
    """Empêche d'inscrire un marin à une session si les formations prérequises de
    la formation concernée n'ont pas toutes un enregistrement (TrainingRecord)
    valide à la date de la session (référence retenue : la date de la session
    plutôt que la date d'inscription, un marin devant être qualifié le jour où la
    formation a effectivement lieu)."""
    if action != "pre_add" or not pk_set:
        return
    reference_date = instance.scheduled_at.date() if instance.scheduled_at else timezone.localdate()
    for user in User.objects.filter(pk__in=pk_set):
        manquants = _prerequis_manquants(user, instance.course, reference_date)
        if manquants:
            noms = ", ".join(p.title for p in manquants)
            raise ValidationError(
                f"Impossible d'inscrire {user.get_full_name() or user.get_username()} à cette "
                f"session : formation(s) prérequise(s) non validée(s) — {noms}."
            )


class TrainingRecord(TimeStampedModel, OwnedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="training_records")
    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="records")
    completed_at = models.DateField()
    expires_at = models.DateField()
    validated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="validated_training_records")
    attachment = models.FileField(upload_to="training_certificates/", null=True, blank=True)

    def clean(self):
        super().clean()
        # Référence retenue : la date de réalisation de cette formation (les
        # prérequis doivent être valides au moment où celle-ci est obtenue),
        # avec repli sur aujourd'hui si cette date n'est pas encore renseignée.
        if self.user_id and self.course_id:
            reference_date = self.completed_at or timezone.localdate()
            manquants = _prerequis_manquants(self.user, self.course, reference_date)
            if manquants:
                noms = ", ".join(p.title for p in manquants)
                raise ValidationError({
                    "course": (
                        "Impossible d'enregistrer cette validation : formation(s) "
                        f"prérequise(s) non validée(s) — {noms}."
                    ),
                })

    @staticmethod
    def compute_expiry(completed_at, validity_days):
        return completed_at + timezone.timedelta(days=validity_days)
