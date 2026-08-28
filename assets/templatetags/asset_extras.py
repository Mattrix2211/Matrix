import os
from django import template

from matrix.core.roles import RoleLevel, user_role_level

register = template.Library()

@register.filter
def basename(value: str) -> str:
    try:
        return os.path.basename(value or "")
    except Exception:
        return value or ""


@register.filter
def peut_configurer_plan_navire(user) -> bool:
    """Vrai si l'utilisateur peut accéder à la configuration du plan visuel du
    navire (ponts/zones) : CHEF_SERVICE et rôles supérieurs, même seuil que
    assets.web_views._peut_configurer_plan_navire — utilisé pour n'afficher
    le lien de navigation qu'aux utilisateurs autorisés (la vue revalide de
    toute façon ce même seuil côté serveur)."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user_role_level(user) >= RoleLevel.CHEF_SERVICE
