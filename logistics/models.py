import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from matrix.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset, Installation
from org.models import Ship, Service, Sector, Section

User = get_user_model()

# Statuts CorrectiveTicket considérés "ouverts" (dossier encore actif) — référence
# unique pour les tableaux de bord (graphique service + Vue flotte), afin de ne pas
# dupliquer cette règle métier à plusieurs endroits.
STATUTS_TICKET_OUVERTS = [
    "REPORTED", "DIAGNOSED", "WAITING_PARTS", "PLANNED", "IN_REPAIR", "TESTING",
]

class CorrectiveTicket(TimeStampedModel, OwnedModel):
    STATUS = (
        ("REPORTED", "Signalé"),
        ("DIAGNOSED", "Diagnostiqué"),
        ("WAITING_PARTS", "En attente pièces"),
        ("PLANNED", "Planifié"),
        ("IN_REPAIR", "En réparation"),
        ("TESTING", "En test"),
        ("RETURNED_TO_SERVICE", "Remis en service"),
        ("CLOSED", "Fermé"),
        ("BLOCKED", "Bloqué"),
        ("CANCELLED", "Annulé"),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="tickets")
    created_by_text = models.CharField(max_length=255, blank=True, default="")
    reported_at = models.DateTimeField(default=timezone.now)
    planned_for = models.DateField(null=True, blank=True)
    description = models.TextField()
    severity = models.PositiveSmallIntegerField(default=3)
    status = models.CharField(max_length=24, choices=STATUS, default="REPORTED")
    # M2M plutôt qu'un FK unique : un ticket correctif peut mobiliser plusieurs
    # marins (ex. électricien + mécanicien), même logique que
    # MaintenanceOccurrence.assignees. Permet de construire "mes tickets" sur le
    # tableau de bord personnel (principe fondamental n°3 de CLAUDE.md), à
    # l'identique de mes_maintenances/mes_formations.
    assignees = models.ManyToManyField(User, blank=True, related_name="assigned_tickets")
    # Retour d'expérience (REX) : capturé directement sur le ticket plutôt que dans
    # un modèle séparé, la donnée brute existant déjà ici (description, historique
    # de statuts, actif concerné). blank=True au niveau modèle pour rester
    # rétrocompatible avec les tickets déjà existants (migration sans valeur par
    # défaut cassante) ; le caractère obligatoire au passage en statut CLOSED est
    # appliqué côté vue (TicketTransitionView), pas ici, pour ne pas bloquer les
    # autres transitions du cycle de vie.
    diagnostic_final = models.TextField(blank=True, default="", verbose_name="Diagnostic final")
    solution = models.TextField(blank=True, default="", verbose_name="Solution appliquée")
    # Signature de validation (T-FEAT signature) : le passage au statut RETURNED_TO_SERVICE
    # exige une ré-authentification légère (mot de passe courant, cf. TicketTransitionView)
    # avant d'être appliqué. AuditLog trace déjà "qui a fait quoi", mais ces deux champs
    # distinguent explicitement une validation engageante d'une simple modification.
    valide_par = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="tickets_valides", verbose_name="Validé par",
    )
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation")

class TicketStatusLog(TimeStampedModel):
    ticket = models.ForeignKey(CorrectiveTicket, on_delete=models.CASCADE, related_name="status_logs")
    old_status = models.CharField(max_length=24)
    new_status = models.CharField(max_length=24)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.TextField(blank=True, default="")

class PartRequest(TimeStampedModel, OwnedModel):
    STATUS = (
        ("OPEN", "Ouverte"),
        ("CLOSED", "Fermée"),
    )
    ticket = models.ForeignKey(CorrectiveTicket, on_delete=models.CASCADE, related_name="part_requests")
    requested_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    needed_by_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="OPEN")

class PartLineItem(TimeStampedModel):
    STATUS = (
        ("TO_ORDER", "À commander"),
        ("ORDERED", "Commandée"),
        ("SHIPPED", "Expédiée"),
        ("RECEIVED", "Reçue"),
        ("CONSUMED", "Consommée"),
        ("RETURNED", "Retournée"),
    )
    part_request = models.ForeignKey(PartRequest, on_delete=models.CASCADE, related_name="lines")
    reference = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    qty = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=16, choices=STATUS, default="TO_ORDER")
    vendor = models.CharField(max_length=255, blank=True, default="")
    order_number = models.CharField(max_length=255, blank=True, default="")
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ordered_at = models.DateField(null=True, blank=True)
    received_at = models.DateField(null=True, blank=True)

class StockPiece(TimeStampedModel, OwnedModel):
    """Stock proactif de pièces de rechange, indépendant de tout ticket correctif.

    Permet de suivre un inventaire bord avec seuil d'alerte (quantite_minimale),
    contrairement à PartLineItem qui n'existe que rattaché à un CorrectiveTicket
    (logistique purement réactive).
    """
    reference = models.CharField(max_length=255, verbose_name="Référence")
    designation = models.CharField(max_length=255, verbose_name="Désignation")
    # NNO : Numéro de Nomenclature OTAN, référence militaire standard permettant
    # d'identifier une pièce de façon univoque entre bâtiments et armées. Texte
    # libre (pas de format imposé) et optionnel : rétrocompatible avec les
    # pièces déjà existantes, saisies avant l'ajout de ce champ.
    nno = models.CharField(max_length=50, blank=True, default="", verbose_name="NNO (Numéro de Nomenclature OTAN)")
    quantite = models.PositiveIntegerField(default=0, verbose_name="Quantité")
    quantite_minimale = models.PositiveIntegerField(default=0, verbose_name="Quantité minimale")
    # Seuil critique (optionnel) : franchi, il déclenche une alerte de niveau
    # supérieur (DANGER) à celle du seuil bas (WARNING), cf. notifications/tasks.py
    # ::notify_low_stock. Nullable plutôt qu'une valeur par défaut arbitraire, même
    # convention que Installation.isolation_seuil_ohms : sans valeur renseignée, le
    # comportement historique est conservé (pièce à quantité 0 = critique), pour
    # rester rétrocompatible avec les pièces déjà existantes sans backfill.
    quantite_critique = models.PositiveIntegerField(null=True, blank=True, verbose_name="Seuil critique")
    emplacement = models.CharField(max_length=255, blank=True, default="", verbose_name="Emplacement")
    # Note libre affichée dans la fiche détaillée de la pièce (pop-up), pour toute
    # information complémentaire ne méritant pas un champ dédié.
    note = models.TextField(blank=True, default="", verbose_name="Note")
    # Photo de la pièce, même mécanisme que les autres photos du projet
    # (Asset.photo, Installation.photo, InstallationPart.photo) : pas de nouveau
    # système de pièce jointe.
    photo = models.FileField(upload_to="stock_photos/", null=True, blank=True, verbose_name="Photo")
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Unité")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Service")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Secteur")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_pieces", verbose_name="Section")
    # Lien optionnel vers l'équipement affilié (une installation fixe OU un
    # matériel mobile, jamais les deux) : la pièce apparaît alors dans l'onglet
    # « Pièces » de la fiche de cet équipement. SET_NULL plutôt que CASCADE : la
    # suppression d'un équipement ne doit pas faire disparaître la pièce en stock,
    # seulement son rattachement.
    installation = models.ForeignKey(
        Installation, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pieces_stock", verbose_name="Installation liée",
    )
    asset = models.ForeignKey(
        Asset, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pieces_stock", verbose_name="Matériel lié",
    )

    class Meta:
        verbose_name = "Pièce en stock"
        verbose_name_plural = "Pièces en stock"
        ordering = ["reference"]

    def clean(self):
        super().clean()
        if self.installation_id and self.asset_id:
            raise ValidationError(
                "Une pièce ne peut être liée qu'à un seul équipement : une installation OU un matériel, pas les deux."
            )
        # Le lien doit rester dans le même périmètre que la pièce (même secteur),
        # même principe que le contrôle déjà appliqué côté vue sur le secteur posté.
        if self.installation_id and self.installation.sector_id != self.sector_id:
            raise ValidationError({"installation": "L'installation liée doit appartenir au même secteur que la pièce."})
        if self.asset_id and self.asset.sector_id != self.sector_id:
            raise ValidationError({"asset": "Le matériel lié doit appartenir au même secteur que la pièce."})

    @property
    def seuil_critique_effectif(self):
        """Seuil critique réellement appliqué : la valeur renseignée, ou 0 par
        défaut (comportement historique : seule une rupture totale était
        considérée comme critique avant l'ajout de ce champ)."""
        return self.quantite_critique if self.quantite_critique is not None else 0

    @property
    def est_critique(self):
        return self.quantite <= self.seuil_critique_effectif

    @property
    def est_bas(self):
        return not self.est_critique and self.quantite < self.quantite_minimale

    @property
    def equipement_lie(self):
        return self.installation or self.asset

    def __str__(self):
        return f"{self.reference} - {self.designation}"
