import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import JSONField
from matrix.core.models import TimeStampedModel, OwnedModel
from org.models import Ship, Service, Sector, Section

User = get_user_model()

def _verifier_absence_de_cycle(equipement):
    """Empêche un rattachement parent qui créerait une boucle dans la hiérarchie
    (un équipement ne peut pas être son propre ancêtre), pour Installation et Asset."""
    if equipement.parent_id is None:
        return
    ancetres_vus = {equipement.pk}
    noeud = equipement.parent
    while noeud is not None:
        if noeud.pk in ancetres_vus:
            raise ValidationError({
                "parent": "Rattachement invalide : cela créerait une boucle dans la hiérarchie des équipements.",
            })
        ancetres_vus.add(noeud.pk)
        noeud = noeud.parent

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

class Deck(TimeStampedModel):
    """Pont d'un navire (ex: pont supérieur, pont principal).

    Sert de support au plan visuel cliquable du navire : un plan distinct par
    pont, avec une navigation ordonnée entre les ponts, sur lequel chaque
    matériel (Asset) peut être positionné précisément par une épingle
    (voir Asset.plan_deck/position_x/position_y).
    """
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="decks", verbose_name="Navire")
    name = models.CharField(max_length=255, verbose_name="Nom du pont")
    # Permet de trier les ponts dans la navigation (ex: du pont le plus haut au
    # plus bas), indépendamment de l'ordre alphabétique des noms.
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    # Image de fond du plan de ce pont, sur laquelle les épingles de matériel
    # (Asset.position_x/position_y) sont positionnées en pourcentage.
    # Optionnelle : un pont peut être créé avant que son plan ne soit
    # téléversé. Même convention que Asset.photo/Installation.photo
    # (FileField, dossier dédié).
    image = models.FileField(upload_to="deck_images/", null=True, blank=True, verbose_name="Image du plan")

    class Meta:
        ordering = ["ship__name", "order", "name"]
        unique_together = ("ship", "name")
        verbose_name = "Pont"
        verbose_name_plural = "Ponts"

    def __str__(self):
        return f"{self.name} ({self.ship.name})"


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
    # Plage attendue d'un relevé numérique (contrôle immédiat à la saisie du compte rendu).
    valeur_min = models.FloatField(null=True, blank=True, verbose_name="Valeur minimale")
    valeur_max = models.FloatField(null=True, blank=True, verbose_name="Valeur maximale")
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
    date_mise_en_service = models.DateField(null=True, blank=True, verbose_name="Date de mise en service")
    date_dernier_controle = models.DateField(null=True, blank=True, verbose_name="Date du dernier contrôle")
    date_peremption = models.DateField(null=True, blank=True, verbose_name="Date de péremption")
    folder = models.ForeignKey('AssetFolder', null=True, blank=True, on_delete=models.SET_NULL, related_name='assets')
    # Article du catalogue dont ce matériel est un exemplaire. SET_NULL : la fiche du bord
    # est une copie autonome et survit à la suppression (rare, réservée) de l'article.
    article_catalogue = models.ForeignKey(
        "ArticleCatalogue", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="exemplaires", verbose_name="Article du catalogue")
    # Rattachement hiérarchique optionnel (ex: un multimètre rattaché à une caisse à outils)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="sous_ensembles")
    # Positionnement précis sur le plan visuel du navire (épingle x/y),
    # remplace l'ancien système de zones rectangulaires groupant plusieurs
    # matériels par Emplacement (modèle Zone, supprimé). Un matériel n'a
    # qu'une seule épingle à la fois : le repositionner écrase l'ancienne
    # position. Les trois champs restent facultatifs, tant qu'aucune épingle
    # n'a été posée pour ce matériel.
    plan_deck = models.ForeignKey(
        Deck, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assets_positionnes", verbose_name="Pont du plan",
    )
    # Coordonnées normalisées (0-100%) de la largeur/hauteur de l'image du
    # pont, même convention que l'ancien Zone.points : la position reste
    # valide quelle que soit la résolution de l'image téléversée.
    position_x = models.FloatField(null=True, blank=True, verbose_name="Position X (%)")
    position_y = models.FloatField(null=True, blank=True, verbose_name="Position Y (%)")

    # États possibles pour le code couleur de l'épingle sur le plan interactif
    # (cf. assets/web_views.py::PlanNavireVueDeckView), repris à l'identique de
    # l'ancien Zone.etat_materiel mais calculé pour CE matériel uniquement
    # (une épingle = un seul matériel, plus de regroupement par zone).
    ETAT_OK = "OK"
    ETAT_ATTENTION = "ATTENTION"
    ETAT_DANGER = "DANGER"

    @property
    def etat_plan(self):
        """État de ce matériel pour l'affichage de son épingle sur le plan :
        - DANGER : matériel hors service ou défectueux.
        - ATTENTION : matériel en bon état déclaré, mais échéance de contrôle
          en retard (MaintenanceOccurrence.status = OVERDUE) ou ticket
          correctif encore ouvert (CorrectiveTicket hors CLOSED/CANCELLED) —
          Asset.status n'étant jamais remis à jour automatiquement à
          l'ouverture d'un ticket, sans ce second cas un matériel resté "OK"
          avec une réparation en cours s'afficherait à tort en vert.
        - OK : aucun signal d'alerte.
        """
        if self.status in ("OUT_OF_SERVICE", "FAULTY"):
            return self.ETAT_DANGER
        # Imports tardifs : maintenance.models et reports.services importent
        # tous les deux assets.models (dépendance inverse), un import en tête
        # de fichier créerait un import circulaire.
        from logistics.models import CorrectiveTicket
        from maintenance.models import MaintenanceOccurrence
        from reports.services import STATUTS_TICKET_FERMES
        en_retard = MaintenanceOccurrence.objects.filter(asset_id=self.pk, status="OVERDUE").exists()
        if en_retard:
            return self.ETAT_ATTENTION
        ticket_ouvert = CorrectiveTicket.objects.filter(
            asset_id=self.pk,
        ).exclude(status__in=STATUTS_TICKET_FERMES).exists()
        return self.ETAT_ATTENTION if ticket_ouvert else self.ETAT_OK

    def clean(self):
        super().clean()
        _verifier_absence_de_cycle(self)

    def save(self, *args, **kwargs):
        # clean() n'est pas appelé automatiquement par save() : sans ce contrôle
        # explicite, un .save() direct (hors formulaire/serializer) contournerait
        # totalement la protection anti-cycle sur le rattachement parent/enfant.
        _verifier_absence_de_cycle(self)
        super().save(*args, **kwargs)

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
    # Seuil minimal d'isolement (Ohms) en dessous duquel l'installation est en
    # danger électrique. Optionnel : si non renseigné, aucune dérive n'est
    # calculée sur l'isolement (voir assets/trend.py et notifications/tasks.py::
    # detect_installation_drift), la valeur exacte dépendant du matériel et
    # devant être fixée par le bord.
    isolation_seuil_ohms = models.PositiveIntegerField(null=True, blank=True)
    # Rattachement hiérarchique optionnel (ex: turbo -> moteur bâbord -> groupe propulsion)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="sous_ensembles")
    # Aucun champ de criticité n'existait sur Installation avant cette tâche. Ce
    # booléen simple permet de désigner les installations dont le passage en
    # "Terminée" d'une maintenance (MaintenanceExecution) exige une validation
    # par mot de passe (cf. OccurrenceExecuteView) — hypothèse la plus simple,
    # à valider/affiner par le Tech Lead si un critère plus fin est attendu.
    critique = models.BooleanField(default=False, verbose_name="Installation critique")

    class Meta:
        ordering = ["ship__name", "service__name", "sector__name", "section__name", "designation"]

    def clean(self):
        super().clean()
        _verifier_absence_de_cycle(self)

    def save(self, *args, **kwargs):
        # clean() n'est pas appelé automatiquement par save() : sans ce contrôle
        # explicite, un .save() direct (hors formulaire/serializer) contournerait
        # totalement la protection anti-cycle sur le rattachement parent/enfant.
        _verifier_absence_de_cycle(self)
        super().save(*args, **kwargs)

    def __str__(self):
        # On utilise le nom brut de chaque niveau (et non son __str__) car
        # Service.__str__ et Sector.__str__ remontent déjà toute la chaîne
        # hiérarchique (ex: Sector -> "Navire / Service / Secteur"). Concaténer
        # leurs __str__ ici dupliquait les segments navire/service dans le
        # libellé de l'installation (bug remonté par le QA).
        return f"{self.designation} ({self.ship.name} / {self.service.name} / {self.sector.name})"


class DocumentInstallation(TimeStampedModel, OwnedModel):
    """Document de référence d'une installation (plan, notice, procédure...), distinct des pièces
    jointes d'événements et d'entretiens."""
    TYPES = (
        ("plan", "Plan"),
        ("notice", "Notice"),
        ("procedure", "Procédure"),
        ("schema", "Schéma"),
        ("certificat", "Certificat"),
        ("autre", "Autre"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="documents")
    titre = models.CharField(max_length=255, verbose_name="Titre")
    type_document = models.CharField(max_length=20, choices=TYPES, default="autre", verbose_name="Type")
    fichier = models.FileField(upload_to="installation_docs/", verbose_name="Fichier")
    notes = models.TextField(blank=True, default="", verbose_name="Notes")

    class Meta:
        ordering = ["titre", "created_at"]
        verbose_name = "Document d'installation"
        verbose_name_plural = "Documents d'installation"

    def __str__(self):
        return self.titre


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

class ModeDeclenchement(models.TextChoices):
    """Mode de déclenchement d'une échéance de maintenance préventive."""
    CALENDRIER = "CALENDRIER", "Calendaire"
    COMPTEUR = "COMPTEUR", "Compteur (heures de marche)"
    LES_DEUX = "LES_DEUX", "Le premier des deux"

# Entretien préventif d'une installation
class InstallationMaintenance(TimeStampedModel, OwnedModel):
    COMPETENCE_CHOICES = (
        ("BORD", "Bord"),
        ("SLM", "SLM"),
        ("INDUSTRIEL", "Industriel"),
    )
    UNITE_INTERVALLE_CHOICES = (
        ("J", "Jour(s)"),
        ("S", "Semaine(s)"),
        ("M", "Mois"),
        ("A", "Année(s)"),
    )
    installation = models.ForeignKey(Installation, on_delete=models.CASCADE, related_name="maintenances")
    periodicity = models.CharField(max_length=64)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    planned_duration_min = models.PositiveIntegerField(default=0)
    people_count = models.PositiveSmallIntegerField(default=1)
    competence = models.CharField(max_length=16, choices=COMPETENCE_CHOICES, default="BORD")

    # Mode de suivi de l'échéance : calendaire, compteur, ou le premier des deux
    mode_declenchement = models.CharField(
        max_length=16,
        choices=ModeDeclenchement.choices,
        default=ModeDeclenchement.CALENDRIER,
    )

    # Branche calendaire structurée — en plus du champ 'periodicity' texte libre
    # existant (conservé pour affichage/rétrocompatibilité, ex: "3 mois")
    intervalle = models.PositiveIntegerField(null=True, blank=True)
    unite_intervalle = models.CharField(max_length=1, choices=UNITE_INTERVALLE_CHOICES, null=True, blank=True)

    # Branche compteur — s'appuie sur InstallationHourReading déjà existant
    seuil_heures = models.PositiveIntegerField(null=True, blank=True)
    derniere_echeance_heures = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

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


def _verifier_cycle_categorie(categorie):
    """Refuse un parent qui ferait de la catégorie son propre ancêtre."""
    vus = {categorie.pk}
    noeud = categorie.parent
    while noeud is not None:
        if noeud.pk in vus:
            raise ValidationError({"parent": "Rattachement invalide : cela créerait une boucle dans les catégories."})
        vus.add(noeud.pk)
        noeud = noeud.parent


class CategorieCatalogue(TimeStampedModel, OwnedModel):
    """Catégorie du catalogue de matériel, commun à toute la flotte (non rattaché
    à un navire). Géré à terre par les responsables de la spécialité."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="enfants", verbose_name="Catégorie parente")
    nom = models.CharField(max_length=255, verbose_name="Nom")
    specialite = models.ForeignKey("accounts.SpecialityChoice", on_delete=models.PROTECT, related_name="categories_catalogue", verbose_name="Spécialité")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    icone = models.CharField(max_length=64, blank=True, default="", verbose_name="Icône")
    photo = models.FileField(upload_to="catalogue_categories/", null=True, blank=True, verbose_name="Photo")
    actif = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        ordering = ["specialite__name", "ordre", "nom"]
        unique_together = ("parent", "nom")
        verbose_name = "Catégorie du catalogue"
        verbose_name_plural = "Catégories du catalogue"

    def clean(self):
        super().clean()
        _verifier_cycle_categorie(self)
        if self.parent_id and self.parent.specialite_id != self.specialite_id:
            raise ValidationError({"specialite": "Une sous-catégorie appartient à la spécialité de sa catégorie parente."})

    def save(self, *args, **kwargs):
        # clean() n'est pas appelé par save() : on protège aussi les écritures directes.
        _verifier_cycle_categorie(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class ArticleCatalogue(TimeStampedModel, OwnedModel):
    """Référence de matériel du catalogue de la flotte : le bord y sélectionne
    ce qu'il possède. La spécialité est celle de la catégorie."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categorie = models.ForeignKey(CategorieCatalogue, on_delete=models.PROTECT, related_name="articles", verbose_name="Catégorie")
    designation = models.CharField(max_length=255, verbose_name="Désignation")
    marque = models.CharField(max_length=255, blank=True, default="", verbose_name="Marque")
    reference = models.CharField(max_length=255, blank=True, default="", verbose_name="Modèle / référence")
    nno = models.CharField(max_length=255, blank=True, default="", verbose_name="NNO")
    photo = models.FileField(upload_to="catalogue_articles/", null=True, blank=True, verbose_name="Photo")
    caracteristiques = JSONField(default=dict, blank=True, verbose_name="Caractéristiques")
    duree_vie_mois = models.PositiveIntegerField(null=True, blank=True, verbose_name="Durée de vie ou de péremption type (mois)")
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        ordering = ["categorie__nom", "designation"]
        verbose_name = "Article du catalogue"
        verbose_name_plural = "Articles du catalogue"

    @property
    def specialite(self):
        return self.categorie.specialite

    def __str__(self):
        return self.designation


class ChefResponsableSpecialite(TimeStampedModel):
    """Chef désigné d'un responsable de spécialité : il vise la proposition d'article après sa vérification."""
    responsable = models.OneToOneField("accounts.ResponsableSpecialite", on_delete=models.CASCADE, related_name="chef_designe", verbose_name="Responsable de spécialité")
    chef = models.ForeignKey(User, on_delete=models.CASCADE, related_name="responsables_specialite_diriges", verbose_name="Chef du responsable")

    class Meta:
        verbose_name = "Chef de responsable de spécialité"
        verbose_name_plural = "Chefs de responsables de spécialité"

    def clean(self):
        super().clean()
        if self.responsable_id and self.chef_id == self.responsable.user_id:
            raise ValidationError({"chef": "Le chef doit être une autre personne que le responsable."})

    def __str__(self):
        return f"{self.chef} — chef de {self.responsable.user}"


class PropositionArticle(TimeStampedModel, OwnedModel):
    """Article proposé par le bord, absent du catalogue : il suit un circuit de visas
    puis devient un ArticleCatalogue. `created_by` est le rédacteur."""

    class Etat(models.TextChoices):
        VISA_SECTEUR = "visa_secteur", "Visa du chef de secteur"
        VISA_SERVICE = "visa_service", "Visa du chef de service"
        VISA_COMA = "visa_coma", "Visa du commandant adjoint"
        VERIFICATION = "verification", "Vérification par le responsable de spécialité"
        VISA_CHEF_SPECIALITE = "visa_chef_specialite", "Visa du chef du responsable de spécialité"
        PUBLIEE = "publiee", "Publiée au catalogue"
        REFUSEE = "refusee", "Renvoyée au rédacteur"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    etat = models.CharField(max_length=24, choices=Etat.choices, default=Etat.VISA_SERVICE, db_index=True)
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="propositions_article", verbose_name="Bâtiment")
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="propositions_article", verbose_name="Service d'origine")
    secteur = models.ForeignKey(Sector, null=True, blank=True, on_delete=models.SET_NULL, related_name="propositions_article", verbose_name="Secteur du rédacteur")
    # Rôle et équipage du rédacteur à la rédaction : ils fixent la première étape et le titulaire du commandant adjoint.
    role_redacteur = models.CharField(max_length=32)
    equipage = models.CharField(max_length=8, blank=True, default="")
    categorie = models.ForeignKey(CategorieCatalogue, on_delete=models.PROTECT, related_name="propositions", verbose_name="Catégorie")
    designation = models.CharField(max_length=255, verbose_name="Désignation")
    marque = models.CharField(max_length=255, blank=True, default="", verbose_name="Marque")
    reference = models.CharField(max_length=255, blank=True, default="", verbose_name="Modèle / référence")
    nno = models.CharField(max_length=255, blank=True, default="", verbose_name="NNO")
    photo = models.FileField(upload_to="catalogue_propositions/", null=True, blank=True, verbose_name="Photo")
    caracteristiques = JSONField(default=dict, blank=True, verbose_name="Caractéristiques")
    duree_vie_mois = models.PositiveIntegerField(null=True, blank=True, verbose_name="Durée de vie ou de péremption type (mois)")
    motif_refus = models.TextField(blank=True, default="")
    verificateur = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="propositions_article_verifiees")
    article = models.OneToOneField(ArticleCatalogue, null=True, blank=True, on_delete=models.SET_NULL, related_name="proposition", verbose_name="Article publié")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Proposition d'article"
        verbose_name_plural = "Propositions d'article"

    @property
    def specialite(self):
        return self.categorie.specialite

    def __str__(self):
        return self.designation


class EvenementProposition(TimeStampedModel):
    """Historique d'une proposition : chaque transition, avec son auteur et son motif."""

    class Action(models.TextChoices):
        SOUMISE = "soumise", "Soumise"
        RESOUMISE = "resoumise", "Soumise à nouveau"
        VISEE = "visee", "Visée"
        CORRIGEE = "corrigee", "Corrigée"
        VERIFIEE = "verifiee", "Vérifiée"
        REFUSEE = "refusee", "Renvoyée au rédacteur"
        PUBLIEE = "publiee", "Publiée"

    proposition = models.ForeignKey(PropositionArticle, on_delete=models.CASCADE, related_name="evenements")
    action = models.CharField(max_length=12, choices=Action.choices)
    etape = models.CharField(max_length=24, choices=PropositionArticle.Etat.choices, blank=True, default="")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="evenements_proposition_article")
    motif = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at", "pk"]
