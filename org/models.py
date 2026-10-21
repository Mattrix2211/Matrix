from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import JSONField
from matrix.core.fuseau import valider_fuseau
from matrix.core.models import TimeStampedModel

User = get_user_model()

class Ship(TimeStampedModel):
    # Types d'unité possibles : une unité n'est pas forcément un navire
    # opérationnel (école, centre de formation, bureau à terre...). Valeur par
    # défaut NAVIRE pour rester rétrocompatible avec les unités existantes.
    class TypeUnite(models.TextChoices):
        NAVIRE = "NAVIRE", "Navire"
        ECOLE = "ECOLE", "École"
        CENTRE_FORMATION = "CENTRE_FORMATION", "Centre de formation"
        BUREAU = "BUREAU", "Bureau"

    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True)
    type_unite = models.CharField(
        max_length=20, choices=TypeUnite.choices, default=TypeUnite.NAVIRE, verbose_name="Type d'unité"
    )
    # Classe du navire (ex : frégate de type La Fayette, sous-marin nucléaire
    # d'attaque type Suffren...). Texte libre car la nomenclature des classes
    # de la Marine Nationale n'est pas une liste fermée à figer dans le code.
    # Optionnel et sans valeur par défaut arbitraire : reste rétrocompatible
    # avec les unités déjà existantes, non concernées par les unités non-navires.
    classe_navire = models.CharField(max_length=100, blank=True, default="", verbose_name="Classe de navire")
    # Double équipage (FREMM, PSP, BSAM) : l'équipage à bord est une donnée
    # configurable (codes libres, ex. « A » / « B »), pas une règle en dur.
    double_equipage = models.BooleanField(default=False, verbose_name="Double équipage")
    equipage_a_bord = models.CharField(
        max_length=8, blank=True, default="", verbose_name="Équipage actuellement à bord"
    )
    # Fuseau IANA de saisie et d'affichage des dates d'effet (les instants restent en UTC) ;
    # vide = fuseau par défaut hérité du paramétrage (settings.TIME_ZONE), distinct d'un choix du bord.
    fuseau_horaire = models.CharField(
        max_length=64, blank=True, default="", validators=[valider_fuseau], verbose_name="Fuseau horaire de référence"
    )
    archived = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Unité"
        verbose_name_plural = "Unités"

    def __str__(self):
        return self.name

class CommandantAdjoint(models.TextChoices):
    """Fonctions de commandant adjoint à bord (COMAVIA seulement si l'unité a une capacité aviation)."""
    COMAEQ = "COMAEQ", "COMAEQ (équipage)"
    COMOPS = "COMOPS", "COMOPS (opérations)"
    COMANAV = "COMANAV", "COMANAV (navire)"
    COMAVIA = "COMAVIA", "COMAVIA (aviation)"


# Signification et domaine de responsabilité en clair de chaque sigle (relecture
# métier du 30/09/2026), affichés avec le sigle pour que l'écran reflète le rôle réel.
SIGNIFICATIONS_COMA = {
    "COMAEQ": "Commandant adjoint équipage",
    "COMOPS": "Commandant adjoint opérations",
    "COMANAV": "Commandant adjoint navire",
    "COMAVIA": "Commandant adjoint aviation",
}
RESPONSABILITES_COMA = {
    "COMAEQ": "Vie à bord, service courant, coordination du personnel à quai, adjoint protection, conduite nautique",
    "COMOPS": "Opérations, conduite des opérations, activité à la mer",
    "COMANAV": "Conservation du bâtiment et des équipements, adjoint sécurité, gestion technique des matériels, "
               "logistique opérationnelle",
    "COMAVIA": "Expertise aviation et sécurité aérienne sur les unités concernées",
}


class Service(TimeStampedModel):
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=255)
    # Commandant adjoint dont dépend le service ; vide = non configuré (repli sur les seuils de rôle).
    commandant_adjoint = models.CharField(
        max_length=16, choices=CommandantAdjoint.choices, blank=True, default="", verbose_name="Commandant adjoint"
    )
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


class RoleThresholdConfig(TimeStampedModel):
    """Seuils de rôle minimal requis par action, configurables par navire.

    Remplace les constantes RoleLevel codées en dur qui étaient dispersées
    dans assets/views.py, maintenance/views.py, threads/views.py,
    accounts/views.py, assets/web_views.py et maintenance/web_views.py
    (tâche Notion « Seuils de rôle configurables par navire »). Même
    principe que SectorConfig ci-dessus : un JSONField configurable, avec
    repli sur une valeur par défaut raisonnable si rien n'est configuré —
    voir matrix/core/role_thresholds.py pour le registre des actions
    configurables et leurs valeurs par défaut (qui reproduisent exactement
    les seuils codés en dur avant ce système, pour ne rien casser).

    `ship=None` porte la configuration GLOBALE (flotte entière), utilisée
    par les actions de portée flotte (ex. référentiels communs à tout le
    bord : grades, spécialités — modèles non rattachés à un navire
    précis). Un seul enregistrement ship=None doit exister en pratique
    (appliqué par convention côté vue via get_or_create, pas par
    contrainte SQL stricte : NULL n'est jamais comparé pour l'unicité).
    """
    ship = models.OneToOneField(
        Ship, null=True, blank=True, on_delete=models.CASCADE, related_name="role_threshold_config"
    )
    thresholds = JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Configuration des seuils de rôle"
        verbose_name_plural = "Configurations des seuils de rôle"

    def __str__(self):
        return f"Seuils de rôle — {self.ship}" if self.ship_id else "Seuils de rôle — configuration globale (flotte)"


class ModuleActivation(TimeStampedModel):
    """Active ou désactive un module applicatif (une app Django) pour un
    navire donné (tâche Notion « Modules activables par bâtiment »).

    Absence d'enregistrement pour un couple (ship, module) = module ACTIVÉ
    (comportement par défaut, rétrocompatible avec tous les navires déjà
    existants — voir matrix/core/modules.py pour le registre des modules
    désactivables, leur résolution avec repli sur "activé" par défaut, et
    la liste documentée des apps de socle jamais désactivables).

    Contrairement à RoleThresholdConfig ci-dessus, il n'existe pas de
    configuration GLOBALE (ship=None) : un module s'active/se désactive
    toujours pour un navire précis, jamais pour toute la flotte d'un coup.
    """
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="modules_actives")
    module = models.CharField(max_length=50, verbose_name="Module")
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("ship", "module")
        verbose_name = "Activation de module"
        verbose_name_plural = "Activations de module"

    def __str__(self):
        return f"{self.ship} — {self.module} ({'activé' if self.active else 'désactivé'})"


class ResponsableClasseNavire(TimeStampedModel):
    """Marin désigné responsable d'une classe de navire pour TOUTE LA FLOTTE
    (tous les navires portant cette classe) — même principe transverse que
    accounts.ResponsableSpecialite, décliné sur Ship.classe_navire plutôt
    que sur la spécialité d'un marin.

    `classe_navire` est un texte libre (comme Ship.classe_navire ci-dessus,
    nomenclature Marine non fermée) : la responsabilité porte sur la VALEUR
    de classe, pas sur un navire précis — elle couvre donc tout navire
    existant ou futur portant cette classe. Donne accès en LECTURE SEULE au
    dashboard classe de navire (dashboard/web_views.py::DashboardClasseNavireView),
    aucun droit d'écriture supplémentaire.

    Désignation réservée à MASTER_ADMIN, même seuil configurable que
    ResponsableSpecialite (cf. matrix/core/role_thresholds.py::REGISTRE_ACTIONS,
    "responsabilite_transverse_gestion")."""

    classe_navire = models.CharField(max_length=100, verbose_name="Classe de navire")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="classes_navire_dont_il_est_responsable"
    )

    class Meta:
        unique_together = ("classe_navire", "user")
        verbose_name = "Responsable de classe de navire"
        verbose_name_plural = "Responsables de classe de navire"

    def __str__(self):
        return f"{self.user} — responsable classe ({self.classe_navire})"


class ReleveEquipage(TimeStampedModel):
    """Relève du double équipage : proposée par un commandant avec sa date d'effet, validée par l'autre.

    Une seule relève ouverte (en attente ou planifiée) par unité ; les décisions passées sont conservées.
    Validée avant sa date d'effet, elle est planifiée et ne change rien tant que cette date n'est pas atteinte.
    « Validée » signifie appliquée.
    """

    class Statut(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente"
        PLANIFIEE = "planifiee", "Planifiée"
        VALIDEE = "validee", "Validée"
        REFUSEE = "refusee", "Refusée"
        ANNULEE = "annulee", "Annulée"

    STATUTS_OUVERTS = (Statut.EN_ATTENTE, Statut.PLANIFIEE)

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="releves")
    equipage_propose = models.CharField(max_length=8)
    propose_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="releves_proposees")
    statut = models.CharField(max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    decide_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="releves_decidees")
    decide_le = models.DateTimeField(null=True, blank=True)
    # Date d'effet prévue (UTC), saisie à la proposition ; distincte de la décision et de l'application réelle.
    date_effet = models.DateTimeField(null=True, blank=True)
    appliquee_le = models.DateTimeField(null=True, blank=True)
    annulee_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="releves_annulees")
    annulee_le = models.DateTimeField(null=True, blank=True)
    motif_annulation = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["ship"], condition=models.Q(statut__in=["en_attente", "planifiee"]),
                name="une_releve_ouverte_par_unite",
            )
        ]


class PeriodeEquipage(TimeStampedModel):
    """Période pendant laquelle un équipage est à bord, créée à l'application d'une relève.

    Jamais reconstituée : avant la première période enregistrée, l'équipage à bord est inconnu.
    """

    class Source(models.TextChoices):
        RELEVE = "releve", "Relève"

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="periodes_equipage")
    equipage = models.CharField(max_length=8)
    debut = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.RELEVE)
    releve = models.OneToOneField(ReleveEquipage, null=True, blank=True, on_delete=models.SET_NULL, related_name="periode")

    class Meta:
        ordering = ("-debut",)
        constraints = [
            models.UniqueConstraint(
                fields=["ship"], condition=models.Q(fin__isnull=True), name="une_periode_ouverte_par_unite"
            )
        ]


class SynthesePassation(TimeStampedModel):
    """Synthèse de passation du bâtiment à la relève, figée à sa génération et conservée.

    Une seule par relève validée (`releve` unique) ; le contenu est un instantané JSON, jamais recalculé.
    """

    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="syntheses_passation")
    releve = models.OneToOneField(
        ReleveEquipage, null=True, blank=True, on_delete=models.SET_NULL, related_name="synthese"
    )
    equipage_sortant = models.CharField(max_length=8, blank=True, default="")
    equipage_montant = models.CharField(max_length=8)
    auteur = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name="syntheses_passation")
    contenu = JSONField(default=dict)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Synthèse de passation"
        verbose_name_plural = "Synthèses de passation"

    def __str__(self):
        return f"Passation {self.equipage_sortant or '?'} → {self.equipage_montant} sur {self.ship} ({self.created_at:%d/%m/%Y})"


class ParametresPassation(TimeStampedModel):
    """Réglage de la synthèse de passation, commun à la flotte (un seul enregistrement, modifié dans les Réglages)."""
    active = models.BooleanField(default=True, verbose_name="Synthèse de passation à la relève")

    class Meta:
        verbose_name = "Réglage de la synthèse de passation"
        verbose_name_plural = "Réglage de la synthèse de passation"

    def __str__(self):
        return "Réglage de la synthèse de passation"

    @classmethod
    def courants(cls):
        return cls.objects.first() or cls()
