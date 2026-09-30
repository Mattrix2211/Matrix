"""Création de notifications en masse avec envoi du Web Push.

`bulk_create` ne déclenche pas le signal `post_save` (cf. signals.py) : une
notification de niveau DANGER créée en masse ne serait jamais poussée. Toute
création en masse de `Notification` doit donc passer par
`creer_notifications_en_masse`, seul point d'entrée prévu.
"""
import logging

from django.db import transaction

from .models import Notification, NotificationLevel
from .push import envoyer_notification_push

logger = logging.getLogger(__name__)


def creer_notifications_en_masse(notifications):
    """Enregistre une liste de `Notification` non sauvegardées en une requête
    et envoie le Web Push des seules notifications de niveau DANGER, une fois
    la transaction validée (rien n'est poussé si elle est annulée).

    Les notifications créées ici ne passent pas par `save()` : le signal
    `post_save` ne les pousse donc jamais une seconde fois. Un échec d'envoi
    est journalisé et n'affecte ni les notifications ni l'appelant.
    """
    creees = Notification.objects.bulk_create(list(notifications))
    critiques = [n for n in creees if n.level == NotificationLevel.DANGER]
    if critiques:
        transaction.on_commit(lambda: _pousser(critiques))
    return creees


def _pousser(notifications):
    for notification in notifications:
        try:
            envoyer_notification_push(notification)
        except Exception:  # un échec du push ne doit jamais bloquer ni annuler les notifications
            logger.exception("Échec de l'envoi Web Push de la notification %s", notification.pk)
