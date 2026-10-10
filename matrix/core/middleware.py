"""Middlewares transverses de Matrix."""
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, QueryDict
from django.urls import reverse
from django.shortcuts import redirect, render
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import SAFE_METHODS

from .equipage import ACTIONS_RELEVE, equipage_a_terre_lecture_seule


def _sans_nul(parametres):
    propres = QueryDict(mutable=True, encoding=parametres.encoding)
    for cle, valeurs in parametres.lists():
        propres.setlist(cle.replace("\x00", ""), [v.replace("\x00", "") for v in valeurs])
    return propres


class SansNulMiddleware:
    """Retire le caractère NUL des paramètres d'URL : PostgreSQL le refuse dans toute requête
    texte (erreur 500), ce que SQLite laisse passer en développement. Les formulaires Django
    le rejettent déjà eux-mêmes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if "%00" in request.META.get("QUERY_STRING", "").lower():
            request.GET = _sans_nul(request.GET)
        return self.get_response(request)


class MotDePasseProvisoireMiddleware:
    """Tant que le marin n'a pas remplacé son mot de passe provisoire, seules la page de changement,
    la déconnexion et les fichiers statiques lui sont ouverts (redirection ; 403 pour l'API)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        utilisateur = request.user
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
                and request.path not in (reverse("logout"), reverse("login"))):
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


# Écritures restant permises à l'équipage à terre : uniquement personnelles ou de session.
CHEMINS_ECRITURE_A_TERRE = (
    "/login/", "/logout/", "/accounts/", "/session/", "/brouillons/", "/notifications/",
    "/api/notifications/", "/users/theme/", "/users/batiment/", "/users/barre-laterale/",
    "/calendar/personnel/", "/taches/commentaire/",
)
# Actions de /parametre/ permises à terre : la relève (la vue revérifie les commandants) et l'heure de notification personnelle.
ACTIONS_PARAMETRE_A_TERRE = (*ACTIONS_RELEVE, "update_notification_time")

MESSAGE_LECTURE_SEULE = "Lecture seule : votre équipage est à terre, cette action est réservée à l'équipage à bord."


class EquipageATerreMiddleware:
    """Refuse toute écriture (web et API) du marin d'un équipage à terre, hors CHEMINS_ECRITURE_A_TERRE.

    Refus par défaut : une nouvelle vue d'écriture est protégée sans rien déclarer.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in SAFE_METHODS and not self._exemptee(request):
            if equipage_a_terre_lecture_seule(self._utilisateur(request)):
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": MESSAGE_LECTURE_SEULE}, status=403)
                return render(request, "403.html", {"message_refus": MESSAGE_LECTURE_SEULE}, status=403)
        return self.get_response(request)

    @staticmethod
    def _exemptee(request):
        if request.path == "/parametre/":
            return request.POST.get("action") in ACTIONS_PARAMETRE_A_TERRE
        return request.path.startswith(CHEMINS_ECRITURE_A_TERRE)

    @staticmethod
    def _utilisateur(request):
        """Utilisateur de la session ; l'API accepte aussi l'authentification Basic, résolue ici."""
        if request.user.is_authenticated or not request.path.startswith("/api/"):
            return request.user
        try:
            resultat = BasicAuthentication().authenticate(request)
        except AuthenticationFailed:
            return request.user
        return resultat[0] if resultat else request.user
