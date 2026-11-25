"""Aides communes aux tests : statut d'administrateur général (AC-15), distinct du superutilisateur Django."""
from django.contrib.auth import get_user_model

from accounts.models import UserProfile


def administrateur_general(utilisateur):
    """Donne le statut d'administrateur général (indicateur du profil) et renvoie le compte rechargé.

    Un superutilisateur Django n'est pas un administrateur général : les tests qui exercent la gouvernance le déclarent."""
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"administrateur_general": True})
    return get_user_model().objects.get(pk=utilisateur.pk)
