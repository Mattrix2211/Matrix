"""Brouillons enregistrés automatiquement côté serveur (docs/UX.md §5.4).

Côté navigateur : static/js/brouillon.js, activé par ``<form data-brouillon="cle">``
(ou tout conteneur portant cet attribut, comme la grille de saisie).

Un brouillon est strictement personnel : toutes les requêtes sont filtrées sur
l'utilisateur connecté, il n'existe aucun moyen de lire celui d'un autre.
Les champs sensibles (mots de passe, jetons) ne sont jamais conservés.
"""
import json
import re
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views import View

from .models import Brouillon

CLE_VALIDE = re.compile(r"^[A-Za-z0-9_.:\-/]{1,120}$")
# Champs sensibles : « password », « csrf » où qu'ils soient ; les autres mots (pass, mdp, token…)
# seulement comme mot entier, pour ne pas exclure à tort « passage » ou « compass ».
NOMS_SENSIBLES = re.compile(
    r"password|passwd|csrf|(^|[^a-z])(passe?|mdp|pwd|token|jeton|secret|signature)([^a-z]|$)", re.IGNORECASE
)


def nettoyer_contenu(contenu):
    """Contenu sans champ sensible ; None si le contenu n'est pas {nom: texte | [texte]}."""
    if not isinstance(contenu, dict):
        return None
    propre = {}
    for nom, valeur in contenu.items():
        if not isinstance(nom, str) or NOMS_SENSIBLES.search(nom):
            continue
        if isinstance(valeur, list):
            if not all(isinstance(v, str) for v in valeur):
                return None
        elif not isinstance(valeur, str):
            return None
        propre[nom] = valeur
    return propre


def brouillons_a_reprendre(user):
    """Brouillons de l'utilisateur à reprendre, du plus récent au plus ancien (page « Aujourd'hui »)."""
    return Brouillon.objects.filter(user=user).order_by("-updated_at")


def purger_brouillons_anciens():
    """Supprime les brouillons non modifiés depuis la durée de conservation ; renvoie leur nombre."""
    jours = settings.BROUILLONS_CONSERVATION_JOURS
    if jours <= 0:
        return 0
    limite = timezone.now() - timedelta(days=jours)
    return Brouillon.objects.filter(updated_at__lt=limite).delete()[0]


def _erreur(message, statut):
    return JsonResponse({"erreur": message}, status=statut)


def _adresse_sure(url):
    """Chemin interne seul : refuse tout ce qui pourrait mener hors du site (redirection ouverte)."""
    if not isinstance(url, str) or not url.startswith("/") or url.startswith(("//", "/\\")):
        return ""
    if "\\" in url or any(ord(c) < 32 or ord(c) == 127 for c in url):
        return ""
    analyse = urlparse(url)
    return "" if analyse.scheme or analyse.netloc else url


class BrouillonView(LoginRequiredMixin, View):
    """GET ?cle= : lire · POST : enregistrer (JSON ou formulaire) · verbe de suppression ?cle= : supprimer.

    La protection CSRF de Django reste active (en-tête X-CSRFToken). Un anonyme
    est redirigé vers la connexion, jamais servi.
    """

    def dispatch(self, request, *args, **kwargs):
        # La page indique pour quel marin elle a été ouverte : si un autre est connecté entre-temps
        # (cookies partagés entre onglets), on ne lit, n'écrit ni ne supprime rien.
        attendu = request.headers.get("X-Mx-Utilisateur")
        if request.user.is_authenticated and attendu is not None and attendu != str(request.user.pk):
            return _erreur("Une autre session est ouverte.", 409)
        return super().dispatch(request, *args, **kwargs)

    def handle_no_permission(self):
        return _erreur("Connexion requise.", 401)

    def get(self, request):
        cle = request.GET.get("cle", "")
        if not CLE_VALIDE.match(cle):
            return _erreur("Clé de brouillon invalide.", 400)
        brouillon = Brouillon.objects.filter(user=request.user, cle=cle).first()
        if brouillon is None:
            return JsonResponse({"existe": False})
        return JsonResponse({
            "existe": True,
            "contenu": brouillon.contenu,
            "mis_a_jour": brouillon.updated_at.isoformat(),
        })

    def post(self, request):
        if len(request.body) > settings.BROUILLONS_TAILLE_MAX:
            return _erreur("Brouillon trop volumineux.", 413)
        if (request.content_type or "").startswith("application/json"):
            try:
                donnees = json.loads(request.body or b"{}")
            except ValueError:
                return _erreur("Données illisibles.", 400)
            if not isinstance(donnees, dict):
                return _erreur("Données illisibles.", 400)
            cle, contenu = donnees.get("cle", ""), donnees.get("contenu")
            libelle, url = donnees.get("libelle", ""), donnees.get("url", "")
        else:
            cle = request.POST.get("cle", "")
            contenu = {n: (v[0] if len(v) == 1 else v) for n, v in request.POST.lists()
                       if n not in ("cle", "libelle", "url")}
            libelle, url = request.POST.get("libelle", ""), request.POST.get("url", "")
        if not isinstance(cle, str) or not CLE_VALIDE.match(cle):
            return _erreur("Clé de brouillon invalide.", 400)
        contenu = nettoyer_contenu(contenu)
        if contenu is None:
            return _erreur("Contenu de brouillon invalide.", 400)
        brouillon, _ = Brouillon.objects.update_or_create(
            user=request.user, cle=cle,
            defaults={
                "contenu": contenu,
                "libelle": libelle[:200] if isinstance(libelle, str) else "",
                "url": _adresse_sure(url)[:300],
            },
        )
        return JsonResponse({"existe": True, "mis_a_jour": brouillon.updated_at.isoformat()})

    def delete(self, request):
        cle = request.GET.get("cle", "")
        if not CLE_VALIDE.match(cle):
            return _erreur("Clé de brouillon invalide.", 400)
        Brouillon.objects.filter(user=request.user, cle=cle).delete()
        return JsonResponse({"existe": False})
