"""Poste connu (AC-18) : dépose le cookie signé qui permet au titulaire de ne pas subir le blocage d'une adresse partagée."""
from django.conf import settings

from . import securite


class PosteConnuMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        reponse = self.get_response(request)
        emis = getattr(request, "_poste_emis", None)
        if emis:
            identifiant, jeton = emis
            reponse.set_cookie(
                securite.COOKIE_POSTE, securite.cookie_poste(securite.postes_de(request), identifiant, jeton),
                max_age=settings.CONSERVATION_COMPTEURS_JOURS * 86400, httponly=True, samesite="Lax",
                secure=settings.SESSION_COOKIE_SECURE)
        return reponse
