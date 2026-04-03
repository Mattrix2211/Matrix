from enum import IntEnum


class RoleLevel(IntEnum):
    EQUIPIER = 1
    CHEF_SECTION = 2
    CHEF_SECTEUR = 3
    CHEF_SERVICE = 4
    COMMANDANT = 5
    MASTER_ADMIN = 6


ROLE_TO_LEVEL = {
    "EQUIPIER": RoleLevel.EQUIPIER,
    "CHEF_SECTION": RoleLevel.CHEF_SECTION,
    "CHEF_SECTEUR": RoleLevel.CHEF_SECTEUR,
    "CHEF_SERVICE": RoleLevel.CHEF_SERVICE,
    "COMMANDANT": RoleLevel.COMMANDANT,
    "ADMIN_NAVIRE": RoleLevel.CHEF_SERVICE,
    "MASTER_ADMIN": RoleLevel.MASTER_ADMIN,
}


def user_role_level(user) -> RoleLevel:
    if getattr(user, "is_superuser", False):
        return RoleLevel.MASTER_ADMIN
    profile = getattr(user, "profile", None)
    if not profile or not profile.role:
        return RoleLevel.EQUIPIER
    return ROLE_TO_LEVEL.get(profile.role, RoleLevel.EQUIPIER)
