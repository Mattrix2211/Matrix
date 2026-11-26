"""Connexion surveillée (AC-18) : limitation progressive par couple (identifiant, source) et par poste connu, voir
`accounts/securite.py`.

Un code de réinitialisation n'est pas un mot de passe : il n'ouvre jamais de session (AC-16).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from . import securite


class ConnexionSurveilleeBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get("username")
        source = securite.source_de(request) if request is not None else "inconnue"
        poste = securite.poste_valide(securite.postes_de(request), username) if request is not None else None
        if securite.est_limite(username, source, poste):
            # Même coût de calcul qu'un identifiant inexistant : le temps de réponse ne révèle ni le compte ni le blocage.
            get_user_model()().set_password(password)
            return None
        utilisateur = super().authenticate(request, username=username, password=password, **kwargs)
        if utilisateur is None:
            # Le middleware d'authentification de l'API et DRF interrogent chacun le backend : un échec ne compte qu'une fois.
            base = getattr(request, "_request", request)
            if base is not None and getattr(base, "_echec_connexion_compte", False):
                return None
            if base is not None:
                base._echec_connexion_compte = True
            securite.enregistrer_echec(username, source, poste=poste)
            return None
        # Le poste connu ne se retient que pour une connexion de navigateur, jamais pour une authentification Basic de l'API.
        base = getattr(request, "_request", request)
        navigateur = request if base is not None and not getattr(base, "META", {}).get("HTTP_AUTHORIZATION") else None
        securite.enregistrer_reussite(username, source, navigateur)
        return utilisateur
