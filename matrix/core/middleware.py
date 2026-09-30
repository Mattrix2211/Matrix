"""Middlewares transverses de Matrix."""
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect

from matrix.core.authentication import MESSAGE_LECTURE_SEULE


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


class LectureSeuleEquipageMiddleware:
    """Double équipage : l'équipage à terre garde l'accès au bâtiment en
    LECTURE SEULE. Ce middleware couvre les pages web et l'API en session
    (org/equipages.py::est_en_lecture_seule). Il ne voit PAS l'utilisateur d'une
    requête API en authentification Basic (DRF authentifie après les
    middlewares) : celle-ci est couverte, ainsi que la session, par les classes
    d'authentification de matrix/core/authentication.py, qui s'appliquent à
    toutes les vues DRF. Écritures restant permises : voir
    org/equipages.py::ECRITURES_AUTORISEES. Sans effet sur un bâtiment à
    équipage unique."""

    METHODES_LECTURE = ("GET", "HEAD", "OPTIONS", "TRACE")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in self.METHODES_LECTURE:
            return self.get_response(request)
        from org.equipages import ecriture_autorisee_a_terre, est_en_lecture_seule

        action = request.POST.get("action") if request.path == "/parametre/" else None
        if ecriture_autorisee_a_terre(request.method, request.path, action) or not est_en_lecture_seule(request.user):
            return self.get_response(request)
        if request.path.startswith("/api/"):
            return JsonResponse({"detail": MESSAGE_LECTURE_SEULE}, status=403)
        if request.headers.get("HX-Request"):
            return HttpResponseForbidden(MESSAGE_LECTURE_SEULE)
        messages.warning(request, MESSAGE_LECTURE_SEULE)
        return redirect(request.META.get("HTTP_REFERER") or "home")
