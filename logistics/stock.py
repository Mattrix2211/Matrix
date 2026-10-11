"""Prélèvement d'une pièce du stock pour un ticket correctif (fiche du ticket et compte rendu d'intervention)."""
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from threads.models import Message, Thread

from .models import CorrectiveTicket, StockPiece


class StockInsuffisant(Exception):
    """La quantité disponible a changé entre le contrôle et l'écriture."""


def prelever(user, piece, quantite, ticket):
    """Retire `quantite` unités de la pièce et trace le prélèvement dans le fil du ticket.

    L'écriture est conditionnelle en base : deux prélèvements concurrents ne vident jamais plus que le stock réel.
    """
    with transaction.atomic():
        modifiees = StockPiece.objects.filter(pk=piece.pk, quantite__gte=quantite).update(
            quantite=F("quantite") - quantite, updated_by=user, updated_at=timezone.now(),
        )
        if not modifiees:
            raise StockInsuffisant(piece.reference)
        thread, _ = Thread.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(CorrectiveTicket), object_id=str(ticket.pk),
        )
        Message.objects.create(
            thread=thread, author=user, is_system=True,
            body=f"Prélèvement stock : {quantite} x {piece.reference} ({piece.designation})",
        )
