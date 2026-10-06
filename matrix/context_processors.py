from accounts.models import Roles
from matrix.core.contexte_batiment import batiment_courant, selecteur_batiment
from matrix.core.navigation import construire_navigation
from notifications.models import Notification


def compteur_notifications(request):
    """Notifications non lues du marin connecté : une seule requête COUNT,
    aucune pour un anonyme."""
    utilisateur = getattr(request, "user", None)
    if not utilisateur or not utilisateur.is_authenticated:
        return {}
    return {"notifications_non_lues": Notification.objects.filter(user=utilisateur, is_read=False).count()}


def theme_utilisateur(request):
    """Thème d'affichage du marin connecté (« clair » par défaut, « sombre » sur choix manuel)."""
    utilisateur = getattr(request, "user", None)
    profil = getattr(utilisateur, "profile", None) if utilisateur and utilisateur.is_authenticated else None
    return {"theme_utilisateur": profil.theme if profil else "clair"}


def navigation_laterale(request):
    """Barre latérale (docs/UX.md §7) : groupes visibles selon les droits et les
    modules du bâtiment, entrée courante, état replié mémorisé dans le profil."""
    utilisateur = getattr(request, "user", None)
    if not utilisateur or not utilisateur.is_authenticated:
        return {}
    profil = getattr(utilisateur, "profile", None)
    return {
        "navigation_laterale": construire_navigation(utilisateur, request.path),
        "barre_laterale_repliee": bool(profil and profil.barre_laterale_repliee),
    }


def barre_superieure(request):
    """Identité et contexte de la barre supérieure (docs/UX.md §8) : nom, grade et
    rôle du marin connecté, bâtiment courant et, pour un utilisateur à terre qui
    suit plusieurs bâtiments, la liste des bâtiments de son périmètre."""
    utilisateur = getattr(request, "user", None)
    if not utilisateur or not utilisateur.is_authenticated:
        return {}
    profil = getattr(utilisateur, "profile", None)
    if utilisateur.is_superuser:
        role = Roles.MASTER_ADMIN.label
    else:
        role = profil.get_role_display() if profil and profil.role else Roles.EQUIPIER.label
    batiments = selecteur_batiment(utilisateur)
    return {
        "identite_utilisateur": {
            "nom": utilisateur.get_full_name() or utilisateur.username,
            "grade": profil.grade if profil else "",
            "role": role,
            "fonction": profil.fonction_service if profil else "",
        },
        "batiment_courant": batiment_courant(request, batiments),
        "batiments_selectionnables": batiments,
    }
