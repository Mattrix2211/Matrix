"""Signaux de l'app notifications : déclenche l'envoi Web Push à la création
d'une notification critique (cf. notifications/push.py)."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification, NotificationLevel


@receiver(post_save, sender=Notification)
def envoyer_push_si_danger(sender, instance, created, **kwargs):
    """Envoie une notification Web Push uniquement à la création d'une
    notification de niveau critique (DANGER) — les niveaux WARNING/INFO
    restent strictement in-app, pour ne pas noyer l'équipage d'alertes de
    moindre importance."""
    if not created or instance.level != NotificationLevel.DANGER:
        return
    from .push import envoyer_notification_push  # import tardif : évite tout risque de cycle au chargement des apps

    envoyer_notification_push(instance)
