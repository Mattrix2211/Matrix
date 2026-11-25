"""Connexion surveillée : verrouillage après des essais répétés et expiration du mot de passe provisoire (AC-12).

Le compteur vit dans le cache du serveur : aucun service externe. Un identifiant verrouillé est refusé même avec le bon mot
de passe jusqu'à la fin du délai ; un succès remet le compteur à zéro.
"""
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.utils import timezone


def _cle(identifiant):
    return f"connexion-echecs:{(identifiant or '').lower()}"


def est_verrouille(identifiant):
    return cache.get(_cle(identifiant), 0) >= settings.TENTATIVES_CONNEXION_MAX


class ConnexionSurveilleeBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")
        if est_verrouille(username):
            return None
        utilisateur = super().authenticate(request, username=username, password=password, **kwargs)
        if utilisateur is None:
            cle = _cle(username)
            cache.set(cle, cache.get(cle, 0) + 1, settings.VERROUILLAGE_CONNEXION_MINUTES * 60)
            return None
        profil = getattr(utilisateur, "profile", None)
        if profil and profil.mot_de_passe_provisoire and profil.mot_de_passe_provisoire_expire_le \
                and profil.mot_de_passe_provisoire_expire_le < timezone.now():
            return None
        cache.delete(_cle(username))
        return utilisateur
