"""Mentions @identifiant : une réponse est attendue du marin cité, jusqu'à ce qu'il réponde dans le fil."""
import re
from types import SimpleNamespace

from django.contrib.contenttypes.models import ContentType

from django.db.models.signals import post_save
from django.dispatch import receiver

from matrix.core.mixins import utilisateurs_visibles_par
from notifications.liens import liens_accessibles
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
    candidats = utilisateurs_visibles_par(auteur)
    if hasattr(objet, "acteurs"):  # dossier à plusieurs acteurs : ses participants sont citables
        candidats = candidats | objet.acteurs()
    cites = list(candidats.filter(username__in=noms, is_active=True).exclude(pk=auteur.pk).distinct())
    instance.mentions.set(cites)
    for user in cites:
        # Une seule alerte en attente par marin et par objet, même cité plusieurs fois.
        if Notification.objects.filter(
            user=user, action_requise=True, traitee_le__isnull=True, verb__startswith=PREFIXE_MENTION,
            content_type=ContentType.objects.get_for_model(objet), object_id=str(objet.pk),
        ).exists():
            continue
        alerte = Notification.objects.create(
            user=user, level=NotificationLevel.WARNING, target=objet, action_requise=True,
            verb=f"{PREFIXE_MENTION} : {_nom(auteur)} vous a cité dans « {objet} ».",
        )
        # Pas d'accès à l'objet : le titre ne doit pas fuiter par l'alerte.
        relue = Notification.objects.select_related("content_type").get(pk=alerte.pk)
        if alerte.pk not in liens_accessibles(SimpleNamespace(user=user), [relue]):
            alerte.delete()
