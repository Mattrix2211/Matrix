from django.db import models
from datetime import date, time
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from org.models import CommandantAdjoint, Ship, Service, Sector, Section
from matrix.core.models import TimeStampedModel

User = get_user_model()

class Roles(models.TextChoices):
    MASTER_ADMIN = "MASTER_ADMIN", "Administrateur général (obsolète : indicateur)"
    # Obsolète depuis L06 : l'administration technique est l'indicateur `administrateur_technique`, indépendant du rôle métier.
    ADMIN_NAVIRE = "ADMIN_NAVIRE", "Administrateur d'unité (obsolète)"
    COMMANDANT = "COMMANDANT", "Commandant"
    COMMANDANT_EN_SECOND = "COMMANDANT_EN_SECOND", "Commandant en second"
    ETAT_MAJOR = "ETAT_MAJOR", "État-major"
    CHEF_SERVICE = "CHEF_SERVICE", "Chef de service"
    CHEF_SECTEUR = "CHEF_SECTEUR", "Chef de secteur"
    CHEF_SECTION = "CHEF_SECTION", "Chef de section"
    EQUIPIER = "EQUIPIER", "Équipier"

class Themes(models.TextChoices):
    CLAIR = "clair", "Clair"
    SOMBRE = "sombre", "Sombre"


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=32, choices=Roles.choices)
    # Droits techniques d'unité (comptes, seuils dans leurs planchers) : indépendants du rôle métier, aucun droit métier.
    administrateur_technique = models.BooleanField(default=False, verbose_name="Administrateur technique")
    grade = models.CharField(max_length=64, blank=True, default="")
    specialite = models.CharField(max_length=128, blank=True, default="")
    fonction_service = models.CharField(max_length=128, blank=True, default="")
    matricule = models.CharField(max_length=64, blank=True, default="")
    # Équipage (« A », « B »…) pour un bâtiment à double équipage ; vide sinon.
    equipage = models.CharField(max_length=8, blank=True, default="", verbose_name="Équipage")
    # Fonction de commandant adjoint (rôle État-major) : sert au routage des visas par service.
    fonction_coma = models.CharField(
        max_length=16, choices=CommandantAdjoint.choices, blank=True, default="", verbose_name="Fonction de commandant adjoint"
    )
    date_naissance = models.DateField(null=True, blank=True)
    # Heure du matin : alertes d'échéance (installations) et digest « Ma journée ».
    notification_time = models.TimeField(default=time(8,0))
    # Heure du soir : digest « Ma journée de demain » (anticiper le lendemain
    # avant de quitter son poste) — distincte de notification_time car elle
    # sert un besoin différent (fin de journée, pas le matin).
    notification_time_soir = models.TimeField(default=time(18,0))

    # Thème d'affichage choisi manuellement par le marin (mode sombre pour l'usage
    # de nuit, docs/UX.md §17). Clair par défaut.
    theme = models.CharField(max_length=8, choices=Themes.choices, default=Themes.CLAIR)

    # Barre latérale repliée (docs/UX.md §7) : état mémorisé par marin, et non par
    # navigateur, car les postes du bord sont partagés. Dépliée par défaut.
    barre_laterale_repliee = models.BooleanField(default=False)
    # Préférences d'interface (groupes du menu, aides vues) : voir accounts/preferences.py. Jamais un contrôle d'accès.
    preferences_interface = models.JSONField(default=dict, blank=True)
    # Gouvernance globale de Matrix (AC-15) : indépendant du rôle métier, qu'il ne remplace pas ni ne donne.
    administrateur_general = models.BooleanField(default=False, verbose_name="Administrateur général")

    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.PROTECT, related_name="profiles")
    service = models.ForeignKey(Service, null=True, blank=True, on_delete=models.PROTECT, related_name="profiles")
    sector = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.PROTECT, related_name="profiles")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.PROTECT, related_name="profiles")

    allowed_sectors = models.ManyToManyField(Sector, blank=True, related_name="authorized_profiles")

    def __str__(self):
        return f"{self.user} ({self.role})"

    def save(self, *args, **kwargs):
        if self.role == Roles.ADMIN_NAVIRE:
            raise ValueError("Le rôle « administrateur d'unité » n'existe plus : utiliser l'indicateur administrateur_technique.")
        if self.role == Roles.MASTER_ADMIN:
            # Valeur historique acceptée en entrée seulement : l'administration générale est un indicateur, le rôle métier reste
            # celui qui a été explicitement attribué (équipier à défaut) ; aucun droit métier n'en découle.
            self.role, self.administrateur_general = Roles.EQUIPIER, True
            update_fields = kwargs.get("update_fields")
            if update_fields is not None and "administrateur_general" not in update_fields:
                kwargs["update_fields"] = [*update_fields, "administrateur_general"]
        super().save(*args, **kwargs)

    @property
    def navire_id_effectif(self):
        """Navire du marin, y compris quand il n'est rattaché que par son
        service, son secteur ou sa section (champ `ship` laissé vide)."""
        if self.ship_id:
            return self.ship_id
        if self.service_id:
            return self.service.ship_id
        if self.sector_id:
            return self.sector.service.ship_id
        if self.section_id:
            return self.section.sector.service.ship_id
        return None

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


class FonctionQuartChoice(models.Model):
    """Référentiel configurable des fonctions de quart (ex. Barre, Veille,
    Machine avant) — même pattern que ServiceFunctionChoice ci-dessus, mais
    distinct : une fonction de QUART (rotation de postes courte) n'a pas le
    même sens métier qu'une fonction de SERVICE/garde, et la nomenclature des
    deux n'a aucune raison de coïncider (CLAUDE.md §6 : configuration plutôt
    que code en dur, décision de cadrage du 09/09/2026 sur le module
    Quarts/services). Utilisé par quarts.models.Quart.fonction — ServiceGarde
    réutilise ServiceFunctionChoice ci-dessus, qui existait déjà pour la
    fonction de service du profil marin."""

    name = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fonction de quart"
        verbose_name_plural = "Fonctions de quart"

    def __str__(self):
        return self.name


class TypeAbsence(models.Model):
    """Référentiel configurable des types d'absence (permission, mission,
    maladie, congé...) utilisé par absences.Absence : rien n'est figé dans le code."""

    name = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Type d'absence"
        verbose_name_plural = "Types d'absence"
        ordering = ("name",)

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


class FonctionAConfirmer(TimeStampedModel):
    """Fonction de commandant adjoint portée par la fiche d'un ancien administrateur d'unité (migration L06) :
    sans effet tant qu'une autorité habilitée ne l'a pas confirmée, corrigée ou refusée."""

    class Statut(models.TextChoices):
        EN_ATTENTE = "EN_ATTENTE", "En attente"
        CONFIRMEE = "CONFIRMEE", "Confirmée"
        CORRIGEE = "CORRIGEE", "Corrigée"
        REFUSEE = "REFUSEE", "Refusée"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="fonctions_a_confirmer")
    ship = models.ForeignKey(Ship, null=True, blank=True, on_delete=models.SET_NULL, related_name="fonctions_a_confirmer")
    fonction_ancienne = models.CharField(max_length=16, choices=CommandantAdjoint.choices)
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    fonction_retenue = models.CharField(max_length=16, choices=CommandantAdjoint.choices, blank=True, default="")
    decide_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="fonctions_decidees")
    decide_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=models.Q(statut="EN_ATTENTE"), name="une_fonction_en_attente_par_compte"),
        ]


class CompteurConnexion(models.Model):
    """Compteur technique temporaire de la limitation des connexions (AC-18) — distinct des journaux d'audit.

    Une ligne par couple (identifiant, source) ; la source « * » porte le compteur global de l'identifiant.
    Purgé après `CONSERVATION_COMPTEURS_JOURS` d'inactivité : sa purge n'efface jamais l'`AuditLog`."""

    identifiant = models.CharField(max_length=150)
    source = models.CharField(max_length=64)
    essais = models.PositiveIntegerField(default=0)
    niveau = models.PositiveIntegerField(default=0)
    bloque_jusqua = models.DateTimeField(null=True, blank=True)
    derniere_reussite = models.DateTimeField(null=True, blank=True)
    derniere_activite = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["identifiant", "source"], name="un_compteur_par_identifiant_et_source")]


class DemandeReinitialisation(TimeStampedModel):
    """Réinitialisation de mot de passe à usage unique (AC-16) ou récupération d'un administrateur général (AC-17).

    Le code n'authentifie jamais : il ne sert qu'à définir un nouveau mot de passe. Seules des empreintes salées sont
    conservées. Pour un compte porteur d'autorité, deux codes (initiateur, vérificateur indépendant) sont exigés."""

    class Statut(models.TextChoices):
        EN_ATTENTE_VERIFICATION = "EN_ATTENTE_VERIFICATION", "En attente de vérification d'identité"
        ACTIVE = "ACTIVE", "Active"
        UTILISEE = "UTILISEE", "Utilisée"
        EXPIREE = "EXPIREE", "Expirée"
        ANNULEE = "ANNULEE", "Annulée"
        BLOQUEE = "BLOQUEE", "Bloquée (trop d'essais)"

    class Nature(models.TextChoices):
        REINITIALISATION = "REINITIALISATION", "Réinitialisation"
        RECUPERATION = "RECUPERATION", "Récupération d'un administrateur général"

    OUVERTES = ("EN_ATTENTE_VERIFICATION", "ACTIVE")

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="demandes_reinitialisation")
    nature = models.CharField(max_length=16, choices=Nature.choices, default=Nature.REINITIALISATION)
    initiateur = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reinitialisations_initiees")
    verificateur = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reinitialisations_verifiees")
    operateur_initiateur = models.CharField(max_length=128, blank=True, default="")
    operateur_verificateur = models.CharField(max_length=128, blank=True, default="")
    justification = models.TextField(blank=True, default="")
    verification_requise = models.BooleanField(default=False)
    attribuer_administrateur_general = models.BooleanField(default=False)
    code_initiateur = models.CharField(max_length=255)
    code_verificateur = models.CharField(max_length=255, blank=True, default="")
    statut = models.CharField(max_length=24, choices=Statut.choices, default=Statut.ACTIVE)
    expire_le = models.DateTimeField()
    essais = models.PositiveIntegerField(default=0)
    utilisee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=models.Q(statut__in=["EN_ATTENTE_VERIFICATION", "ACTIVE"]),
                                    name="une_demande_ouverte_par_compte"),
        ]


class OperateurRecuperation(TimeStampedModel):
    """Opérateur habilité à la récupération d'un administrateur général (AC-17) : identité système et phrase secrète
    personnelle (empreinte salée), indépendantes des comptes applicatifs."""

    nom = models.CharField(max_length=128)
    identifiant_systeme = models.CharField(max_length=128, unique=True)
    phrase = models.CharField(max_length=255)
    actif = models.BooleanField(default=True)


class InitialisationBatiment(TimeStampedModel):
    """Trace unique de l'initialisation des premières autorités d'un bâtiment (AC-09) : l'unicité par bâtiment verrouille la
    procédure, y compris contre deux exécutions simultanées."""

    ship = models.OneToOneField(Ship, on_delete=models.PROTECT, related_name="initialisation")
    operateur = models.CharField(max_length=128)
    autorisation = models.CharField(max_length=200)
    commandant = models.ForeignKey(User, on_delete=models.PROTECT, related_name="initialisations_commandant")
    administrateur_technique = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.PROTECT, related_name="initialisations_technique")


class InstanceDemo(models.Model):
    """Marqueur d'une base de démonstration : une base marquée ne démarre pas en production."""
    cree_le = models.DateTimeField(auto_now_add=True)
    commande = models.CharField(max_length=64)
    identifiant = models.CharField(max_length=64, blank=True, default="")  # identifiant d'instance écrit par la préparation

    def __str__(self):
        return f"Base de démonstration ({self.commande}, {self.cree_le:%Y-%m-%d})"


class ResponsableSpecialite(TimeStampedModel):
    """Marin désigné responsable d'une spécialité pour TOUTE LA FLOTTE (tous
    navires confondus) — rôle transverse, indépendant de la hiérarchie
    Navire → Service → Secteur → Section et du rôle hiérarchique du marin
    (CLAUDE.md), au même titre que training.ReferentFormation est
    indépendant du rang. Donne accès en LECTURE SEULE au dashboard
    spécialité (dashboard/web_views.py::DashboardSpecialiteView) : aucun
    droit d'écriture supplémentaire sur les fiches des marins concernés.

    Désignation réservée à MASTER_ADMIN (référentiel commun à toute la
    flotte, même seuil que les grades/spécialités — cf.
    matrix/core/role_thresholds.py::REGISTRE_ACTIONS,
    "responsabilite_transverse_gestion").

    Plusieurs responsables possibles pour une même spécialité (FK simple
    répétable, pas de OneToOneField), même pattern que ReferentFormation."""

    specialite = models.ForeignKey(SpecialityChoice, on_delete=models.CASCADE, related_name="responsables")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="specialites_dont_il_est_responsable")

    class Meta:
        unique_together = ("specialite", "user")
        verbose_name = "Responsable de spécialité"
        verbose_name_plural = "Responsables de spécialité"

    def __str__(self):
        return f"{self.user} — responsable spécialité ({self.specialite})"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    # Crée automatiquement un profil pour tout nouvel utilisateur
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={"role": Roles.EQUIPIER})
