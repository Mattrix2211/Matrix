"""Connexion surveillée (AC-18) : limitation progressive par couple (identifiant, source), voir `accounts/securite.py`.

Un code de réinitialisation n'est pas un mot de passe : il n'ouvre jamais de session (AC-16).
"""
from django.contrib.auth.backends import ModelBackend

from . import securite


class ConnexionSurveilleeBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")
        source = securite.source_de(request) if request is not None else "inconnue"
        if securite.est_limite(username, source):
            return None
        utilisateur = super().authenticate(request, username=username, password=password, **kwargs)
        if utilisateur is None:
            # Le middleware d'authentification de l'API et DRF interrogent chacun le backend : un échec ne compte qu'une fois.
            base = getattr(request, "_request", request)
            if base is not None and getattr(base, "_echec_connexion_compte", False):
                return None
            if base is not None:
                base._echec_connexion_compte = True
            securite.enregistrer_echec(username, source)
            return None
        securite.enregistrer_reussite(username, source)
        return utilisateur
