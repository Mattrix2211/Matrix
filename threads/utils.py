"""Utilitaires pour rattacher un fil de discussion (Thread) générique à un
objet métier (ticket correctif, occurrence de maintenance, ...).

Le contrôle d'accès (lecture et écriture) reste entièrement porté par la vue
appelante, sur l'objet parent (périmètre, assignation ou rôle selon le
module) : ces fonctions ne recréent aucun système de droits sur les threads
eux-mêmes, elles se contentent de lire/écrire les messages une fois l'accès
à l'objet déjà vérifié.
"""
from django.contrib.contenttypes.models import ContentType

from .models import Message, Thread


def commentaires_de(obj):
    """Messages (système et libres) du fil de discussion rattaché à un objet,
    triés du plus ancien au plus récent. Ne crée pas le fil s'il n'existe pas
    encore : consulter un objet sans aucun message ne doit rien écrire en base."""
    content_type = ContentType.objects.get_for_model(obj)
    return (
        Message.objects.filter(thread__content_type=content_type, thread__object_id=str(obj.pk))
        .select_related("author")
        .order_by("created_at")
    )


def ajouter_commentaire(obj, auteur, corps):
    """Ajoute un commentaire de suivi libre (non système) au fil de discussion
    d'un objet, en créant ce fil à la volée s'il n'existe pas encore — même
    principe que les messages système déjà créés par OccurrenceExecuteView
    (maintenance/web_views.py) et CorrectiveTicketViewSet.transition
    (logistics/views.py)."""
    content_type = ContentType.objects.get_for_model(obj)
    thread, _ = Thread.objects.get_or_create(content_type=content_type, object_id=str(obj.pk))
    return Message.objects.create(thread=thread, author=auteur, body=corps, is_system=False)
