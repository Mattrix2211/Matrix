from enum import IntEnum


class RoleLevel(IntEnum):
    """Niveau hiérarchique numérique, du plus bas (Équipier) au plus haut (Administrateur général).

    Ordre complet documenté dans CLAUDE.md :
    MASTER_ADMIN > ADMIN_NAVIRE > COMMANDANT > ETAT_MAJOR > CHEF_SERVICE > CHEF_SECTEUR > CHEF_SECTION > EQUIPIER
    """

    EQUIPIER = 1
    CHEF_SECTION = 2
    CHEF_SECTEUR = 3
    CHEF_SERVICE = 4
    ETAT_MAJOR = 5
    COMMANDANT = 6
    ADMIN_NAVIRE = 7
    MASTER_ADMIN = 8


ROLE_TO_LEVEL = {
    "EQUIPIER": RoleLevel.EQUIPIER,
    "CHEF_SECTION": RoleLevel.CHEF_SECTION,
    "CHEF_SECTEUR": RoleLevel.CHEF_SECTEUR,
    "CHEF_SERVICE": RoleLevel.CHEF_SERVICE,
    "ETAT_MAJOR": RoleLevel.ETAT_MAJOR,
    "COMMANDANT": RoleLevel.COMMANDANT,
    "ADMIN_NAVIRE": RoleLevel.ADMIN_NAVIRE,
    "MASTER_ADMIN": RoleLevel.MASTER_ADMIN,
}


def user_role_level(user) -> RoleLevel:
    if getattr(user, "is_superuser", False):
        return RoleLevel.MASTER_ADMIN
    profile = getattr(user, "profile", None)
    if not profile or not profile.role:
        return RoleLevel.EQUIPIER
    return ROLE_TO_LEVEL.get(profile.role, RoleLevel.EQUIPIER)
