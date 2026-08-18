import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from matrix.core.models import TimeStampedModel, OwnedModel
from assets.models import Asset
from org.models import Ship, Service, Sector, Section

User = get_user_model()

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
    quantite = models.PositiveIntegerField(default=0, verbose_name="Quantité")
    quantite_minimale = models.PositiveIntegerField(default=0, verbose_name="Quantité minimale")
    emplacement = models.CharField(max_length=255, blank=True, default="", verbose_name="Emplacement")
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Navire")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Service")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="stock_pieces", verbose_name="Secteur")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_pieces", verbose_name="Section")

    class Meta:
        verbose_name = "Pièce en stock"
        verbose_name_plural = "Pièces en stock"
        ordering = ["reference"]

    def __str__(self):
        return f"{self.reference} - {self.designation}"
