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

    Sert de support au futur plan visuel cliquable du navire (voir Zone
    ci-dessous) : un plan distinct par pont, avec une navigation ordonnée
    entre les ponts. Cette tâche ne couvre que le modèle de données — l'image
    de fond et l'éditeur de zones arrivent dans une tâche suivante.
    """
    ship = models.ForeignKey(Ship, on_delete=models.CASCADE, related_name="decks", verbose_name="Navire")
    name = models.CharField(max_length=255, verbose_name="Nom du pont")
    # Permet de trier les ponts dans la navigation (ex: du pont le plus haut au
    # plus bas), indépendamment de l'ordre alphabétique des noms.
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    # Image de fond du plan de ce pont, sur laquelle les zones cliquables
    # (Zone ci-dessous) sont positionnées en pourcentage. Optionnelle : un
    # pont peut être créé avant que son plan ne soit téléversé. Même
    # convention que Asset.photo/Installation.photo (FileField, dossier dédié).
    image = models.FileField(upload_to="deck_images/", null=True, blank=True, verbose_name="Image du plan")

    class Meta:
        ordering = ["ship__name", "order", "name"]
        unique_together = ("ship", "name")
        verbose_name = "Pont"
        verbose_name_plural = "Ponts"

    def __str__(self):
        return f"{self.name} ({self.ship.name})"


class Zone(TimeStampedModel):
    """Zone cliquable délimitée sur le plan d'un pont.

    Le contour est stocké sous forme de liste de points normalisés en
    pourcentage (0 à 100) de la largeur/hauteur de l'image de fond du pont,
    plutôt qu'en pixels : la zone reste ainsi valide quelle que soit la
    résolution de l'image téléversée. Un simple rectangle (4 points) suffit
    pour cette première version, mais le format polygone évite d'enfermer une
    future zone de forme quelconque (ex: contour d'une coque) dans une
    nouvelle migration.
    """
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="zones", verbose_name="Pont")
    name = models.CharField(max_length=255, verbose_name="Nom de la zone")
    # Réutilise l'Emplacement (Location) déjà utilisé sur le matériel et les
    # installations : c'est ce lien qui permettra, dans une tâche suivante, de
    # filtrer le matériel affiché lors d'un clic sur la zone. Facultatif et en
    # SET_NULL, comme sur Asset/Installation : une zone peut être dessinée en
    # brouillon avant qu'un emplacement lui soit assigné, et la suppression
    # d'un emplacement ne doit pas être bloquée par une simple zone de plan.
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="zones", verbose_name="Emplacement",
    )
    # Contour normalisé (0-100%) : liste de points [{"x": .., "y": ..}, ...].
    # Un rectangle se représente avec 4 points, dans l'ordre des coins.
    points = JSONField(
        default=list,
        blank=True,
        verbose_name="Contour de la zone",
        help_text="Liste de points {x, y} en pourcentage (0-100) de l'image du pont.",
    )

    class Meta:
        ordering = ["deck__ship__name", "deck__order", "deck__name", "name"]
        verbose_name = "Zone"
        verbose_name_plural = "Zones"

    def __str__(self):
        return f"{self.name} ({self.deck})"

    # États possibles pour le code couleur du plan interactif (rendu de
    # consultation, cf. assets/web_views.py::PlanNavireVueDeckView). Le pire
    # état présent parmi le matériel de l'emplacement lié l'emporte toujours :
    # un seul élément hors service suffit à colorer toute la zone en rouge
    # (règle tranchée par le Tech Lead/PO pour cette tâche).
    ETAT_NEUTRE = "NEUTRE"
    ETAT_OK = "OK"
    ETAT_ATTENTION = "ATTENTION"
    ETAT_DANGER = "DANGER"

    @property
    def etat_materiel(self):
        """État agrégé du matériel rattaché à l'emplacement de cette zone.

        Périmètre volontairement limité au matériel mobile (Asset) : les
        installations fixes (Installation) ne sont pas prises en compte ici,
        ce n'est pas un oubli mais un choix de portée pour cette première
        version du plan interactif.

        - NEUTRE : zone brouillon (sans emplacement, cf. sous-tâche 1) ou
          emplacement sans aucun matériel répertorié — pour ne jamais afficher
          une fausse alerte verte sur une zone vide.
        - DANGER : au moins un matériel hors service ou défectueux (statut
          Asset.status OUT_OF_SERVICE/FAULTY), équivalent "périmé/hors service".
        - ATTENTION : aucun matériel en danger, mais au moins un matériel a une
          échéance de contrôle en retard (MaintenanceOccurrence.status =
          OVERDUE, réutilisant le système d'entretien préventif existant
          plutôt que d'inventer un nouveau champ "à contrôler"), OU au moins
          un ticket correctif encore ouvert (CorrectiveTicket hors CLOSED/
          CANCELLED) est lié à ce matériel. Ce second cas est nécessaire car
          Asset.status n'est jamais remis à jour automatiquement à
          l'ouverture d'un ticket correctif : sans cela, un matériel resté
          "OK" avec une réparation en cours s'afficherait à tort en vert.
        - OK : tout le matériel de l'emplacement est en bon état.
        """
        if self.location_id is None:
            return self.ETAT_NEUTRE
        materiels = list(self.location.assets.all())
        if not materiels:
            return self.ETAT_NEUTRE
        if any(m.status in ("OUT_OF_SERVICE", "FAULTY") for m in materiels):
            return self.ETAT_DANGER
        # Imports tardifs : maintenance.models et reports.services importent
        # tous les deux assets.models (dépendance inverse), un import en tête
        # de fichier créerait un import circulaire.
        from logistics.models import CorrectiveTicket
        from maintenance.models import MaintenanceOccurrence
        from reports.services import STATUTS_TICKET_FERMES
        ids_materiels = [m.pk for m in materiels]
        en_retard = MaintenanceOccurrence.objects.filter(
            asset_id__in=ids_materiels, status="OVERDUE",
        ).exists()
        if en_retard:
            return self.ETAT_ATTENTION
        ticket_ouvert = CorrectiveTicket.objects.filter(
            asset_id__in=ids_materiels,
        ).exclude(status__in=STATUTS_TICKET_FERMES).exists()
        return self.ETAT_ATTENTION if ticket_ouvert else self.ETAT_OK

    @property
    def rectangle_pourcent(self):
        """Boîte englobante du contour, en pourcentage (left/top/width/height),
        pour un positionnement CSS absolu simple sur le plan de consultation —
        même principe que boiteEnglobante() côté éditeur en JS
        (assets/plan_navire_deck.html), calculé ici côté serveur puisque la
        page de consultation est en lecture seule (pas de redessin à gérer).
        Renvoie None si le contour est vide/invalide."""
        if not self.points:
            return None
        try:
            xs = [float(p["x"]) for p in self.points]
            ys = [float(p["y"]) for p in self.points]
        except (TypeError, KeyError, ValueError):
            return None
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        return {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}


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
    # Rattachement hiérarchique optionnel (ex: un multimètre rattaché à une caisse à outils)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="sous_ensembles")

    def clean(self):
        super().clean()
        _verifier_absence_de_cycle(self)

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

    def __str__(self):
        # On utilise le nom brut de chaque niveau (et non son __str__) car
        # Service.__str__ et Sector.__str__ remontent déjà toute la chaîne
        # hiérarchique (ex: Sector -> "Navire / Service / Secteur"). Concaténer
        # leurs __str__ ici dupliquait les segments navire/service dans le
        # libellé de l'installation (bug remonté par le QA).
        return f"{self.designation} ({self.ship.name} / {self.service.name} / {self.sector.name})"


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
