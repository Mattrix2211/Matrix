from django import template

from matrix.core.roles import RoleLevel, user_role_level

register = template.Library()


@register.filter
def peut_voir_vue_flotte(user):
    """Vrai si l'utilisateur peut accéder à la Vue flotte : chef de section
    (ou au-dessus), même seuil que dashboard.web_views.VueFlotteView
    (RoleLevel.CHEF_SECTION, voir matrix/core/roles.py). La vue s'adapte
    ensuite au périmètre effectif de l'utilisateur (section/secteur/navire/
    flotte selon son rôle, cf. dashboard.web_views._perimetre_agregation)."""
    if not getattr(user, "is_authenticated", False):
        return False
    return user_role_level(user) >= RoleLevel.CHEF_SECTION
