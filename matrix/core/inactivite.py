"""Déconnexion automatique après inactivité, pour les postes partagés (docs/UX.md §2.3).

Le serveur est l'autorité : il mémorise dans la session l'heure de la dernière activité
humaine et déconnecte au-delà du délai configuré. Les requêtes automatiques (compteur de
notifications, brouillons), repérées par l'en-tête ``X-Mx-Automatique``, ne la renouvellent pas.
Côté navigateur : static/js/inactivite.js (préavis, « Rester connecté », enregistrement des brouillons).
"""
import time
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, resolve_url
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

CLE_SESSION = "derniere_activite"
ENTETE_AUTOMATIQUE = "X-Mx-Automatique"
# Bornes de sécurité du délai (secondes) : une valeur hors bornes ou illisible revient au défaut.
DELAI_DEFAUT, DELAI_MIN, DELAI_MAX = 900, 60, 8 * 3600
AVERTISSEMENT_DEFAUT, AVERTISSEMENT_MIN = 60, 10
# Écriture de la session au plus toutes les N secondes, pour ne pas la mettre à jour à chaque requête.
PAS_ECRITURE = 5


def _entier(valeur, defaut, minimum, maximum):
    try:
        nombre = int(str(valeur).strip())
    except (TypeError, ValueError):
        return defaut
    return nombre if minimum <= nombre <= maximum else defaut


def delai_inactivite():
    return _entier(settings.INACTIVITE_DELAI_SECONDES, DELAI_DEFAUT, DELAI_MIN, DELAI_MAX)


def delai_avertissement():
    """Préavis affiché avant la déconnexion, au plus la moitié du délai."""
    maximum = delai_inactivite() // 2
    defaut = min(AVERTISSEMENT_DEFAUT, maximum)
    return _entier(settings.INACTIVITE_AVERTISSEMENT_SECONDES, defaut, AVERTISSEMENT_MIN, maximum)


def _suivant_sur(request, url):
    """Adresse de retour acceptée seulement si elle reste sur ce site (pas de redirection ouverte)."""
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return url
    return None


def _page_courante(request):
    """Page où se trouvait le marin : celle de la requête, ou l'en-tête htmx pour un fragment."""
    if request.headers.get("HX-Request") == "true":
        courante = urlparse(request.headers.get("HX-Current-URL", ""))
        if courante.netloc != request.get_host():
            return None
        return _suivant_sur(request, courante.path + (f"?{courante.query}" if courante.query else ""))
    if request.method in ("GET", "HEAD"):
        return _suivant_sur(request, request.get_full_path())
    return None


def url_connexion(request, expire, suivant=None):
    """Page de connexion, avec le message d'inactivité (expire) et la page de retour (suivant)."""
    parametres = {}
    if expire:
        parametres["expire"] = 1
    suivant = _suivant_sur(request, suivant)
    if suivant:
        parametres["next"] = suivant
    base = resolve_url(settings.LOGIN_URL)
    return f"{base}?{urlencode(parametres)}" if parametres else base


def tracer_expiration(utilisateur):
    from accounts.models import AuditLog

    AuditLog.objects.create(
        actor=utilisateur, action="session_expiree", details=f"inactivité supérieure à {delai_inactivite()} s"
    )


def _est_automatique(request):
    return bool(request.headers.get(ENTETE_AUTOMATIQUE))


def _attend_du_json(request):
    return "application/json" in request.headers.get("Accept", "")


class InactiviteMiddleware:
    """Expire la session d'un marin inactif et renvoie les requêtes sans session valide vers la
    connexion de façon exploitable : redirection pour une page, ``HX-Redirect`` pour htmx
    (au lieu d'une page de connexion injectée dans un fragment), 401 pour les requêtes automatiques.
    L'API REST garde ses réponses 401/403."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = request.user
        if utilisateur.is_authenticated:
            maintenant = int(time.time())
            derniere = request.session.get(CLE_SESSION)
            if not isinstance(derniere, int):
                derniere = None
            # La déconnexion volontaire de l'inactivité (/logout/) est traitée par sa propre vue.
            if (
                derniere is not None and maintenant - derniere > delai_inactivite()
                and request.path != reverse("logout")
            ):
                tracer_expiration(utilisateur)
                logout(request)
                if request.path.startswith("/api/"):
                    return self.get_response(request)
                return self._vers_connexion(request, expire=True)
            if not _est_automatique(request) and (derniere is None or maintenant - derniere >= PAS_ECRITURE):
                request.session[CLE_SESSION] = maintenant

        reponse = self.get_response(request)
        if (
            reponse.status_code == 302 and not request.user.is_authenticated
            and (request.headers.get("HX-Request") == "true" or _est_automatique(request) or _attend_du_json(request))
            and urlparse(reponse["Location"]).path == resolve_url(settings.LOGIN_URL)
        ):
            return self._vers_connexion(request, expire=False)
        return reponse

    @staticmethod
    def _vers_connexion(request, expire):
        if _est_automatique(request) or _attend_du_json(request):
            return JsonResponse({"detail": "Session expirée."}, status=401)
        cible = url_connexion(request, expire, _page_courante(request))
        if request.headers.get("HX-Request") == "true":
            reponse = HttpResponse()
            reponse["HX-Redirect"] = cible
            return reponse
        return redirect(cible)


class SessionInactiviteView(LoginRequiredMixin, View):
    """GET : temps restant avant l'expiration (sans la prolonger, grâce à l'en-tête automatique).
    POST : « Rester connecté », renouvelle la session."""

    def get(self, request):
        maintenant = int(time.time())
        ecoule = maintenant - request.session.get(CLE_SESSION, maintenant)
        return JsonResponse({"restant": max(0, delai_inactivite() - ecoule)})

    def post(self, request):
        request.session[CLE_SESSION] = int(time.time())
        return JsonResponse({"restant": delai_inactivite()})
