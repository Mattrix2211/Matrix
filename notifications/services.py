"""Création de notifications en masse avec envoi du Web Push.

`bulk_create` ne déclenche pas le signal `post_save` (cf. signals.py) : une
notification de niveau DANGER créée en masse ne serait jamais poussée. Toute
création en masse de `Notification` doit donc passer par
`creer_notifications_en_masse`, seul point d'entrée prévu.
"""
import logging

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Notification, NotificationLevel
from .push import envoyer_notification_push

logger = logging.getLogger(__name__)


def compter_non_lues(utilisateur):
    """Notifications non lues du marin : unique source du compteur de la barre et du centre."""
    return Notification.objects.filter(user=utilisateur, is_read=False).count()


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


def traiter_actions(objet, utilisateurs=None, prefixe_verbe=""):
    """Solde les alertes d'action en attente portant sur `objet` (source résolue) ; l'historique reste.

    `utilisateurs` limite aux destinataires concernés ; `prefixe_verbe` à un type d'alerte."""
    alertes = Notification.objects.filter(
        content_type=ContentType.objects.get_for_model(objet), object_id=str(objet.pk),
        action_requise=True, traitee_le__isnull=True, verb__startswith=prefixe_verbe,
    )
    if utilisateurs is not None:
        alertes = alertes.filter(user__in=utilisateurs)
    return alertes.update(traitee_le=timezone.now(), is_read=True)
