"""Mouvements de stock : seul point d'écriture de `StockPiece.quantite`.

La quantité d'une pièce est la somme de ses mouvements ; le champ `quantite` en est une copie
mise à jour ici, dans la même transaction que l'écriture du mouvement (verrou sur la pièce).
"""
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog
from threads.models import Message, Thread

from .models import CorrectiveTicket, MouvementStock, StockPiece


class StockInsuffisant(Exception):
    """Le mouvement rendrait le stock négatif."""

    def __init__(self, reference, disponible=None):
        super().__init__(reference)
        self.reference = reference
        self.disponible = disponible


class MotifRequis(Exception):
    """Un inventaire ou une correction exige un motif."""


def enregistrer_mouvement(user, piece, type_mouvement, quantite, motif="", ticket=None, ligne_pieces=None):
    """Écrit un mouvement et met à jour le stock de la pièce.

    `quantite` : nombre positif pour une entrée ou une sortie, effectif compté pour un inventaire
    (l'écart est calculé), variation signée pour une correction. Retourne le mouvement.
    """
    motif = (motif or "").strip()
    if type_mouvement in (MouvementStock.INVENTAIRE, MouvementStock.CORRECTION) and not motif:
        raise MotifRequis()
    with transaction.atomic():
        verrouillee = StockPiece.objects.select_for_update().get(pk=piece.pk)
        if type_mouvement == MouvementStock.INVENTAIRE:
            variation = quantite - verrouillee.quantite
        elif type_mouvement == MouvementStock.SORTIE:
            variation = -quantite
        else:
            variation = quantite
        solde = verrouillee.quantite + variation
        if solde < 0:
            raise StockInsuffisant(verrouillee.reference, verrouillee.quantite)
        mouvement = MouvementStock.objects.create(
            piece=verrouillee, type=type_mouvement, quantite=variation, solde_apres=solde, auteur=user,
            motif=motif, ticket=ticket, ligne_pieces=ligne_pieces,
        )
        StockPiece.objects.filter(pk=verrouillee.pk).update(quantite=solde, updated_by=user, updated_at=timezone.now())
        AuditLog.objects.create(
            actor=user, action="stock_mouvement",
            details=f"piece={verrouillee.pk}; type={type_mouvement}; variation={variation:+d}; solde={solde}; motif={motif!r}",
        )
    piece.quantite = solde
    return mouvement


def prelever(user, piece, quantite, ticket):
    """Sort `quantite` unités de la pièce pour un ticket et trace le prélèvement dans son fil."""
    with transaction.atomic():
        enregistrer_mouvement(
            user, piece, MouvementStock.SORTIE, quantite, motif=f"Intervention sur le ticket {ticket.pk}", ticket=ticket,
        )
        thread, _ = Thread.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(CorrectiveTicket), object_id=str(ticket.pk),
        )
        Message.objects.create(
            thread=thread, author=user, is_system=True,
            body=f"Prélèvement stock : {quantite} x {piece.reference} ({piece.designation})",
        )


def sortie_pour_ligne_consommee(user, ligne, pieces):
    """Sortie de stock quand une ligne de demande de pièces passe à « Consommée ».

    La pièce est retrouvée par sa référence parmi `pieces` (queryset déjà dans le périmètre) ;
    sans correspondance unique, ou si la ligne a déjà généré une sortie, rien n'est écrit.
    Retourne le mouvement, ou None.
    """
    if ligne.mouvements_stock.filter(type=MouvementStock.SORTIE).exists():
        return None
    candidates = list(pieces.filter(reference__iexact=ligne.reference)[:2])
    if len(candidates) != 1:
        return None
    ticket = ligne.part_request.ticket
    return enregistrer_mouvement(
        user, candidates[0], MouvementStock.SORTIE, ligne.qty,
        motif=f"Pièce consommée (demande de pièces du ticket {ticket.pk})", ticket=ticket, ligne_pieces=ligne,
    )
