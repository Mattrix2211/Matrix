"""Middlewares transverses de Matrix."""
import logging

from django.contrib import messages
from django.db import DataError, connection
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse, QueryDict
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import redirect, render
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS

from .config_version import fermer_contexte, ouvrir_contexte
from .equipage import ACTIONS_RELEVE, equipage_a_terre_lecture_seule
from .scopes import soutien_a_terre

logger = logging.getLogger(__name__)

# psycopg2 signale le NUL par un ValueError sans type propre (psycopg 3 lève un DataError).
EXTRAIT_NUL = "NUL (0x00)"


def _sans_nul(parametres):
    propres = QueryDict(mutable=True, encoding=parametres.encoding)
    for cle, valeurs in parametres.lists():
        propres.setlist(cle.replace("\x00", ""), [v.replace("\x00", "") for v in valeurs])
    propres._mutable = False
    return propres


def _contient_nul(parametres):
    return any("\x00" in cle or any("\x00" in v for v in valeurs) for cle, valeurs in parametres.lists())


def utilisateur_de_requete(request):
    """Utilisateur de la session ; l'API accepte aussi l'authentification Basic, résolue ici."""
    if request.user.is_authenticated or not request.path.startswith("/api/"):
        return request.user
    try:
        resultat = BasicAuthentication().authenticate(request)
    except AuthenticationFailed:
        return request.user
    return resultat[0] if resultat else request.user


class SansNulMiddleware:
    """Retire le caractère NUL des paramètres d'URL et des formulaires envoyés (POST) : PostgreSQL
    le refuse dans toute requête texte (erreur 500), ce que SQLite laisse passer en développement."""

    TYPES_FORMULAIRE = ("application/x-www-form-urlencoded", "multipart/form-data")

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _nettoyer_a_la_lecture(request):
        """Nettoie le corps à son analyse (pas avant : lire request.POST d'avance interdirait request.body)."""
        analyser = request._load_post_and_files

        def analyser_et_nettoyer():
            analyser()
            if _contient_nul(request._post):
                request._post = _sans_nul(request._post)

        request._load_post_and_files = analyser_et_nettoyer

    def __call__(self, request):
        if "%00" in request.META.get("QUERY_STRING", "").lower():
            request.GET = _sans_nul(request.GET)
        if request.method == "POST" and request.content_type in self.TYPES_FORMULAIRE:
            self._nettoyer_a_la_lecture(request)
        return self.get_response(request)


class ErreurSaisieMiddleware(MiddlewareMixin):
    """Dernier recours pour deux erreurs de saisie attendues, reconnues à leur type : texte trop long pour sa
    colonne (DataError) et caractère NUL. Toute autre exception reste une erreur 500 visible : les vues
    contrôlent elles-mêmes leurs entiers, dates et longueurs avant d'écrire. Si la requête a déjà écrit en
    base, l'erreur reste aussi visible (500) : un message « recommencez » risquerait de créer des doublons."""

    ECRITURES = ("INSERT", "UPDATE", "DELETE")

    def __call__(self, request):
        request._ecriture_en_base = False

        def surveiller(execute, sql, params, many, context):
            resultat = execute(sql, params, many, context)
            if sql.lstrip()[:6].upper() in self.ECRITURES:
                request._ecriture_en_base = True
            return resultat

        with connection.execute_wrapper(surveiller):
            return super().__call__(request)

    @staticmethod
    def _est_erreur_de_saisie(exception):
        return isinstance(exception, DataError) or (isinstance(exception, ValueError) and EXTRAIT_NUL in str(exception))

    def process_exception(self, request, exception):
        if not self._est_erreur_de_saisie(exception) or request._ecriture_en_base:
            return None
        logger.warning("Saisie refusée sur %s %s", request.method, request.path, exc_info=exception)
        message = "Saisie refusée : une valeur est invalide ou trop longue. Rien n'a été enregistré : vérifiez les champs et recommencez."
        if request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"detail": message}, status=400)
        if request.method in ("GET", "HEAD"):
            return HttpResponseBadRequest(message, content_type="text/plain; charset=utf-8")
        messages.error(request, message)
        retour = request.headers.get("Referer", "")
        if not url_has_allowed_host_and_scheme(retour, allowed_hosts={request.get_host()}):
            retour = "/"
        if request.headers.get("HX-Request"):
            reponse = HttpResponse(status=204)
            reponse["HX-Redirect"] = retour
            return reponse
        return HttpResponseRedirect(retour)


class MotDePasseProvisoireMiddleware:
    """Tant que le marin n'a pas remplacé son mot de passe provisoire, seules la page de changement,
    la déconnexion et les fichiers statiques lui sont ouverts (redirection ; 403 pour l'API)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = utilisateur_de_requete(request)
        if utilisateur.is_authenticated and getattr(getattr(utilisateur, "profile", None), "mot_de_passe_provisoire", False):
            changement = reverse("password_change")
            libres = (changement, reverse("logout"), "/static/", "/service-worker.js")
            if not request.path.startswith(libres):
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": "Changement de mot de passe obligatoire."}, status=403)
                if request.headers.get("HX-Request"):
                    reponse = HttpResponse(status=204)
                    reponse["HX-Redirect"] = changement
                    return reponse
                return redirect(changement)
        return self.get_response(request)


class BatimentCourantMiddleware:
    """Publie le bâtiment choisi dans le sélecteur (utilisateur à terre) pour filtrer les listes de la requête."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .contexte_batiment import CLE_SESSION, batiment_filtre, selecteur_batiment

        courant = None
        if request.user.is_authenticated and not request.path.startswith("/api/"):
            choisi = request.session.get(CLE_SESSION)
            if choisi and any(b.pk == choisi for b in selecteur_batiment(request.user)):
                courant = choisi
        jeton = batiment_filtre.set(courant)
        try:
            return self.get_response(request)
        finally:
            batiment_filtre.reset(jeton)


class IdentitePageMiddleware:
    """Refuse (409) une écriture dont la page a été ouverte pour un autre marin que celui connecté
    (poste partagé : cookies communs à tous les onglets). L'identité vient de l'en-tête
    ``X-Mx-Utilisateur`` (htmx, fetch) ou du champ ``mx_utilisateur`` (formulaire) ajoutés par
    identite.js ; sans identité (page ancienne, sans JavaScript), la requête passe. Les brouillons
    contrôlent eux-mêmes l'identité (réponses JSON)."""

    METHODES_SURES = ("GET", "HEAD", "OPTIONS", "TRACE")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method not in self.METHODES_SURES and request.user.is_authenticated
                and not request.path.startswith(("/api/", "/admin/", "/brouillons/"))
                and request.path not in (reverse("logout"), reverse("login"), "/login/")):
            attendu = request.headers.get("X-Mx-Utilisateur")
            if attendu is None and request.content_type in ("application/x-www-form-urlencoded", "multipart/form-data"):
                try:
                    attendu = request.POST.get("mx_utilisateur")
                except Exception:
                    attendu = None
            if attendu is not None and attendu != str(request.user.pk):
                return HttpResponse(
                    "Une autre session est ouverte sur ce poste : rechargez la page.",
                    status=409, content_type="text/plain; charset=utf-8",
                )
        return self.get_response(request)


class ContexteConfigurationMiddleware:
    """Ouvre le contexte de requête où les versions de configuration (seuils,
    modules) ne sont validées en base qu'une seule fois (config_version.py)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        jeton = ouvrir_contexte()
        try:
            return self.get_response(request)
        finally:
            fermer_contexte(jeton)


class ModuleActivationMiddleware:
    """Bloque l'accès direct par URL aux vues WEB (pages HTML) d'un module
    désactivé sur le navire de l'utilisateur connecté (tâche Notion « Modules
    activables par bâtiment »), en complément du masquage des entrées de menu
    (matrix/templates/base.html, filtre org_extras::module_actif).

    Volontairement limité à la couche web (chemins hors "/api/" et
    "/admin/") : l'API REST, les tâches Celery et les enchaînements métier
    internes entre modules (ex. création automatique d'un ticket correctif
    logistics depuis une exécution maintenance) continuent de fonctionner
    normalement quel que soit l'état du module — désactiver un module ne
    supprime ni ne bloque jamais une donnée déjà créée (CLAUDE.md, principe
    n°6 : configuration plutôt que suppression). Voir matrix/core/modules.py
    pour le registre des modules désactivables et le détail de ce choix.

    Résout le module concerné à partir du nom du module Python où la vue est
    définie (ex. "assets.web_views" -> app "assets"), en s'appuyant sur
    l'attribut `view_class` que Django pose sur toute vue basée sur une
    classe (`View.as_view()`) — sans avoir à modifier individuellement
    chacune des vues des modules désactivables.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith("/api/") or request.path.startswith("/admin/"):
            return None
        if not getattr(request.user, "is_authenticated", False):
            # Un utilisateur non connecté n'a pas de navire résolu (module_actif
            # renvoie alors toujours "activé") : la vue elle-même gère la
            # redirection vers la connexion (LoginRequiredMixin), rien à faire ici.
            return None

        view_class = getattr(view_func, "view_class", None)
        if view_class is None:
            return None

        from .modules import REGISTRE_PAR_CLE, module_actif_pour_user

        app_label = view_class.__module__.split(".")[0]
        module = REGISTRE_PAR_CLE.get(app_label)
        if module is None or module_actif_pour_user(app_label, request.user):
            return None

        messages.warning(
            request,
            f"Le module « {module.libelle} » est désactivé sur votre unité. "
            "Contactez le commandant ou l'administrateur de l'unité pour le réactiver "
            "(Paramètres > Modules).",
        )
        return redirect("home")


# Écritures personnelles ou de session, permises à tout marin en lecture seule.
CHEMINS_PERSONNELS = (
    "/login/", "/logout/", "/accounts/", "/session/", "/brouillons/", "/notifications/",
    "/api/notifications/", "/users/theme/", "/users/batiment/", "/users/barre-laterale/",
    "/calendar/personnel/",
)
# Écritures restant permises à l'équipage à terre : personnelles, fils de discussion, demandes et annonces.
CHEMINS_ECRITURE_A_TERRE = (*CHEMINS_PERSONNELS, "/taches/commentaire/", "/demandes/", "/annonces/")
# Soutien à terre (sans bâtiment) : écritures personnelles, commentaires et circuits du catalogue flotte
# (responsables de spécialité) ; les vues revérifient leurs droits. Tout le reste est refusé par défaut.
CHEMINS_ECRITURE_SOUTIEN = (
    *CHEMINS_PERSONNELS, "/taches/commentaire/", "/catalogue/", "/fiches/", "/api/assets/catalogue-",
    "/api/threads/messages/", "/api/threads/attachments/",
)
# Actions de /parametre/ permises à terre : la relève (la vue revérifie les commandants) et l'heure de notification personnelle.
ACTIONS_PARAMETRE_A_TERRE = (*ACTIONS_RELEVE, "update_notification_time")

MESSAGE_LECTURE_SEULE = "Lecture seule : votre équipage est à terre, cette action est réservée à l'équipage à bord."
MESSAGE_SOUTIEN_A_TERRE = "Soutien à terre : vous consultez et commentez, la modification des données du bord est réservée à l'équipage embarqué."


class EquipageATerreMiddleware:
    """Refuse toute écriture (web et API) de l'équipage à terre et du soutien à terre, hors chemins permis.

    Refus par défaut : une nouvelle vue d'écriture est protégée sans rien déclarer.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in SAFE_METHODS:
            utilisateur = utilisateur_de_requete(request)
            message = self._refus(request, utilisateur)
            if message:
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": message}, status=403)
                return render(request, "403.html", {"message_refus": message}, status=403)
        return self.get_response(request)

    @staticmethod
    def _refus(request, utilisateur):
        """Message de refus si l'écriture n'est pas permise à cet utilisateur, sinon chaîne vide."""
        if equipage_a_terre_lecture_seule(utilisateur):
            if request.path == "/parametre/":
                permis = request.POST.get("action") in ACTIONS_PARAMETRE_A_TERRE
            else:
                permis = request.path.startswith(CHEMINS_ECRITURE_A_TERRE)
            return "" if permis else MESSAGE_LECTURE_SEULE
        if soutien_a_terre(utilisateur):
            if request.path == "/parametre/":
                permis = request.POST.get("action") == "update_notification_time"
            else:
                permis = request.path.startswith(CHEMINS_ECRITURE_SOUTIEN) or request.path.endswith("/commentaire/")
            return "" if permis else MESSAGE_SOUTIEN_A_TERRE
        return ""
