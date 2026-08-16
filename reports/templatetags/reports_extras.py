from django import template

from matrix.core.roles import RoleLevel, user_role_level

register = template.Library()


@register.filter
def peut_generer_bilan(user):
    """Vrai si l'utilisateur peut générer le bilan PDF de son périmètre :
    chef de secteur/section (ou au-dessus) avec un périmètre propre défini
    sur son profil (`profile.scope`) — même seuil que le reste de l'application
    (`RoleLevel.CHEF_SECTION`, voir matrix/core/roles.py)."""
    if not getattr(user, "is_authenticated", False):
        return False
    if user_role_level(user) < RoleLevel.CHEF_SECTION:
        return False
    profile = getattr(user, "profile", None)
    # UserProfile.scope renvoie (None, None) — et non None — quand aucun périmètre
    # n'est affecté (voir accounts/models.py) : on teste le premier élément du tuple.
    return bool(profile and profile.scope[0])
