from typing import Dict, Any, Optional
from django.contrib.auth import get_user_model


def scope_filters_for_user(user) -> Dict[str, Any]:
    if not user.is_authenticated:
        return {}
    profile = getattr(user, "profile", None)
    if not profile:
        return {}
    level, obj_id = profile.scope
    if level == "ship":
        return {"ship_id": obj_id}
    if level == "service":
        return {"service_id": obj_id}
    if level == "sector":
        return {"sector_id": obj_id}
    if level == "section":
        return {"section_id": obj_id}
    return {}


def is_master_admin(user) -> bool:
    """Vrai si l'utilisateur a un accès multi-navires (flotte entière) :
    superutilisateur ou rôle MASTER_ADMIN, seul niveau au-dessus de ADMIN_NAVIRE
    dans la hiérarchie (matrix/core/roles.py). Tous les autres rôles (ADMIN_NAVIRE
    compris) sont rattachés à un navire précis. Même règle que celle déjà
    appliquée dans org/views.py::_is_master_admin, centralisée ici pour être
    réutilisée par toute vue nécessitant un périmètre "navire entier" (ex. Vue
    flotte du tableau de bord)."""
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "MASTER_ADMIN")


def ship_id_for_user(user) -> Optional[int]:
    """Renvoie l'id du navire rattaché au profil de l'utilisateur, ou None si
    aucun navire n'est renseigné. Contrairement à scope_filters_for_user() (qui
    renvoie le niveau le plus précis du profil), ceci renvoie toujours le
    navire, quel que soit le service/secteur/section également renseigné —
    utile pour les vues agrégées à l'échelle du bâtiment entier."""
    profile = getattr(user, "profile", None)
    ship = getattr(profile, "ship", None)
    return ship.id if ship else None
