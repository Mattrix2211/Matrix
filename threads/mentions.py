"""Mentions @identifiant : une réponse est attendue du marin cité, jusqu'à ce qu'il réponde dans le fil."""
import re

from django.db.models.signals import post_save
from django.dispatch import receiver

from matrix.core.mixins import utilisateurs_visibles_par
from notifications.models import Notification, NotificationLevel
from notifications.services import traiter_actions

from .models import Message

PREFIXE_MENTION = "Réponse attendue"
_MENTION = re.compile(r"(?<![\w@])@([\w.+-]+)")


def _nom(user):
    return user.get_full_name() or user.get_username()


@receiver(post_save, sender=Message)
def traiter_mentions(sender, instance, created, **kwargs):
    if not created or instance.is_system or instance.author_id is None:
        return
    objet = instance.thread.content_object
    if objet is None:
        return
    auteur = instance.author
    # Répondre dans le fil solde les réponses attendues de l'auteur.
    traiter_actions(objet, [auteur], PREFIXE_MENTION)
    noms = set(_MENTION.findall(instance.body))
    if not noms:
        return
    cites = list(
        utilisateurs_visibles_par(auteur).filter(username__in=noms, is_active=True).exclude(pk=auteur.pk)
    )
    instance.mentions.set(cites)
    for user in cites:
        Notification.objects.create(
            user=user, level=NotificationLevel.WARNING, target=objet, action_requise=True,
            verb=f"{PREFIXE_MENTION} : {_nom(auteur)} vous a cité dans « {objet} ».",
        )
