from django import template

from matrix.core.roles import RoleLevel, user_role_level

register = template.Library()


@register.filter
def peut_voir_vue_flotte(user):
    """Vrai si l'utilisateur peut accéder à la Vue flotte : chef de service
    (ou au-dessus), même seuil que dashboard.web_views.VueFlotteView
    (RoleLevel.CHEF_SERVICE, voir matrix/core/roles.py)."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user_role_level(user) >= RoleLevel.CHEF_SERVICE
