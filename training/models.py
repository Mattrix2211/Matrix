from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from matrix.core.models import TimeStampedModel, OwnedModel
from matrix.core.roles import RoleLevel, user_role_level
from org.models import Sector, Ship, Service, Section

User = get_user_model()

class TrainingCourse(TimeStampedModel):
    sector = models.ForeignKey(Sector, on_delete=models.CASCADE, related_name="training_courses")
    title = models.CharField(max_length=255)
    # Domaine métier de la formation (ex. "Sécurité/Incendie", "Habilitation
    # électrique", "Levage"...) : texte libre saisi par le chef, pas de liste
    # figée — même pattern que AssetType.category (assets/models.py), pour ne
    # pas décider à la place de la Marine la liste exhaustive des domaines
    # métier. Champ facultatif et rétrocompatible : les formations existantes
    # ont une catégorie vide, à compléter ensuite par les chefs.
    category = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    validity_days = models.PositiveIntegerField(default=365)
    # Arbre de compétences : formations à valider avant de pouvoir suivre celle-ci.
    # related_name="unlocks" : les formations que la validation de celle-ci débloque.
    prerequisites = models.ManyToManyField(
        "self", symmetrical=False, blank=True, related_name="unlocks"
    )
    # Référents : personnes précisément désignées comme habilitées à valider
    # CETTE formation (créer/modifier un TrainingRecord, gérer les présences
    # d'une session), choisies pour leur compétence sur le sujet plutôt que
    # pour leur rang ou leur secteur — un marin habilité peut ainsi être
    # référent d'une formation d'un secteur ou d'un navire différent du sien,
    # et inversement ne pas être référent d'une formation de son propre
    # secteur s'il n'a pas la compétence requise. Voir peut_valider_formation()
    # ci-dessous pour le contrôle d'accès associé.
    referents = models.ManyToManyField(
        User, blank=True, related_name="formations_referentes"
    )

    def __str__(self):
        return self.title


class ReferentFormationNavire(TimeStampedModel):
    """Référent formation désigné pour l'ENSEMBLE d'un navire — à ne pas
    confondre avec TrainingCourse.referents ci-dessus (référent d'UNE
    formation précise, choisi pour sa compétence sur ce sujet précis). Ce
    rôle donne autorité de validation sur TOUTES les formations du navire,
    quel que soit le secteur, pour un marin chargé de piloter le volet
    formation de tout le bord (ex. "cellule formation") sans lui donner pour
    autant le rang de COMMANDANT. Un seul référent par navire (OneToOneField
    sur Ship) ; désigné/retiré uniquement par un rôle de supervision globale
    (cf. peut_valider_formation ci-dessous et
    training/web_views.py::_peut_gerer_referent_navire)."""

    ship = models.OneToOneField(Ship, on_delete=models.CASCADE, related_name="referent_formation")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="navires_dont_il_est_referent_formation"
    )

    def __str__(self):
        return f"{self.user} — référent formation ({self.ship})"


# Rôle à partir duquel un utilisateur peut valider n'importe quelle formation,
# même s'il n'est pas désigné référent : supervision globale (COMMANDANT et
# au-dessus), même logique que is_master_admin (matrix/core/scopes.py) pour
# les rôles élevés qui court-circuitent un contrôle plus fin ailleurs dans le
# projet. En dessous de ce seuil — y compris un chef de rang supérieur mais
# non désigné référent ni référent formation du navire — seul le statut de
# référent compte : il est attribué pour la compétence sur la formation (ou,
# pour ReferentFormationNavire, pour la mission confiée sur tout le navire),
# pas pour la position hiérarchique.
NIVEAU_SUPERVISION_GLOBALE_FORMATION = RoleLevel.COMMANDANT


def peut_valider_formation(user, course):
    """Vrai si `user` peut créer/modifier/supprimer un enregistrement de
    validation (TrainingRecord) pour `course`, ou gérer les présences d'une
    session de cette formation (TrainingSession.attendees) : soit parce qu'il
    est désigné référent de cette formation précise (TrainingCourse.referents),
    soit parce qu'il est désigné référent formation de l'ensemble du navire
    auquel appartient `course` (ReferentFormationNavire, autorité valable sur
    toutes les formations du navire quel que soit le secteur), soit parce
    qu'il occupe un rôle de supervision globale (COMMANDANT et au-dessus)."""
    if user_role_level(user) >= NIVEAU_SUPERVISION_GLOBALE_FORMATION:
        return True
    if course.referents.filter(pk=user.pk).exists():
        return True
    return ReferentFormationNavire.objects.filter(
        ship_id=course.sector.service.ship_id, user=user
    ).exists()


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
    # Capacité maximale de places réservables en libre-service : illimitée si
    # laissée vide (aucun contrôle de capacité dans ce cas).
    capacite_max = models.PositiveIntegerField(null=True, blank=True)
    # Réservations self-service : intention d'un marin d'assister à cette
    # session, distincte de `attendees` (présence/réussite réellement
    # constatée, gérée uniquement par les référents — cf. peut_valider_formation
    # ci-dessus, à ne pas toucher). Un marin ne réserve/annule que SA PROPRE
    # réservation (contrôle fait dans training/web_views.py) ; les règles
    # métier (capacité, session toujours planifiée, prérequis, session pas
    # encore passée) sont appliquées ci-dessous par _controler_reservation,
    # seul point de passage garanti quel que soit l'appelant.
    reservations = models.ManyToManyField(User, blank=True, related_name="training_reservations")
    location = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS, default="PLANNED")

    def places_restantes(self):
        """Nombre de places encore réservables, ou None si la capacité est
        illimitée (capacite_max non renseignée). Utilise `len(...all())` plutôt
        que `.count()` pour réutiliser le cache d'un éventuel
        prefetch_related('reservations') fait par l'appelant (liste des
        sessions d'une formation), sans requête supplémentaire par session."""
        if self.capacite_max is None:
            return None
        return max(0, self.capacite_max - len(self.reservations.all()))


@receiver(m2m_changed, sender=TrainingSession.reservations.through)
def _controler_reservation(sender, instance, action, pk_set, **kwargs):
    """Contrôle les réservations self-service (TrainingSession.reservations,
    distinctes de attendees ci-dessous) : à l'ajout (pre_add), vérifie que la
    session est toujours planifiée, que la capacité maximale n'est pas
    dépassée, et que les prérequis de la formation sont validés — même
    principe défensif que _bloquer_inscription_sans_prerequis (attendees),
    seul point de passage garanti quel que soit l'appelant (vue web, API,
    admin, shell). À la suppression (pre_remove), interdit d'annuler une
    réservation sur une session déjà passée."""
    if action == "pre_add" and pk_set:
        if instance.status != "PLANNED":
            raise ValidationError(
                "Impossible de réserver une place : cette session n'est plus planifiée."
            )
        if instance.capacite_max is not None:
            deja_reserves = instance.reservations.count()
            if deja_reserves + len(pk_set) > instance.capacite_max:
                raise ValidationError(
                    "Impossible de réserver une place : cette session est complète."
                )
        reference_date = instance.scheduled_at.date() if instance.scheduled_at else timezone.localdate()
        for user in User.objects.filter(pk__in=pk_set):
            manquants = _prerequis_manquants(user, instance.course, reference_date)
            if manquants:
                noms = ", ".join(p.title for p in manquants)
                raise ValidationError(
                    f"Impossible de réserver une place pour {user.get_full_name() or user.get_username()} : "
                    f"formation(s) prérequise(s) non validée(s) — {noms}."
                )
    elif action == "pre_remove" and pk_set:
        if instance.scheduled_at and instance.scheduled_at <= timezone.now():
            raise ValidationError(
                "Impossible d'annuler cette réservation : la session a déjà eu lieu."
            )


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
