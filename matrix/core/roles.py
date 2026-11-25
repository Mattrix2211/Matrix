from enum import IntEnum


class RoleLevel(IntEnum):
    """Niveau hiérarchique numérique, du plus bas (Équipier) au plus haut (Administrateur général).

    Échelle MÉTIER : EQUIPIER … COMMANDANT. `ADMIN_NAVIRE` n'est plus un rôle mais le palier des droits TECHNIQUES, que seul
    un administrateur technique atteint (`niveau_pour_action`) ; aucun rôle métier n'y mène. MASTER_ADMIN reste au-dessus.
    """

    EQUIPIER = 1
    CHEF_SECTION = 2
    CHEF_SECTEUR = 3
    CHEF_SERVICE = 4
    ETAT_MAJOR = 5
    COMMANDANT_EN_SECOND = 6
    COMMANDANT = 7
    ADMIN_NAVIRE = 8
    MASTER_ADMIN = 9


ROLE_TO_LEVEL = {
    "EQUIPIER": RoleLevel.EQUIPIER,
    "CHEF_SECTION": RoleLevel.CHEF_SECTION,
    "CHEF_SECTEUR": RoleLevel.CHEF_SECTEUR,
    "CHEF_SERVICE": RoleLevel.CHEF_SERVICE,
    "ETAT_MAJOR": RoleLevel.ETAT_MAJOR,
    "COMMANDANT_EN_SECOND": RoleLevel.COMMANDANT_EN_SECOND,
    "COMMANDANT": RoleLevel.COMMANDANT,
    "MASTER_ADMIN": RoleLevel.MASTER_ADMIN,
}


# Le commandant en second a la même vision (lecture) que le commandant ;
# les écritures « tout-puissantes » restent à RoleLevel.COMMANDANT.
NIVEAU_VISION_COMMANDEMENT = RoleLevel.COMMANDANT_EN_SECOND


def user_role_level(user) -> RoleLevel:
    if getattr(user, "is_superuser", False):
        return RoleLevel.MASTER_ADMIN
    profile = getattr(user, "profile", None)
    if not profile or not profile.role:
        return RoleLevel.EQUIPIER
    return ROLE_TO_LEVEL.get(profile.role, RoleLevel.EQUIPIER)


# Rôles dont le grade ne vaut pas écriture sur les données du bord : leurs écritures passent par des workflows explicites.
ROLES_SANS_ECRITURE_HERITEE = ("COMMANDANT_EN_SECOND",)


def est_administrateur_technique(user) -> bool:
    """Droits techniques d'unité : indicateur du profil, ou administrateur général. N'ouvre aucun droit métier."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and (profile.administrateur_technique or profile.role == "MASTER_ADMIN"))


GENERAL, TECHNIQUE, SUPERUTILISATEUR_DJANGO = "general", "technique", "superutilisateur_django"


def statuts_d_administration(user) -> frozenset:
    """Statuts d'administration distincts d'un compte (AC-11), cumulables : administrateur général Matrix (rôle),
    administrateur technique du bâtiment (indicateur), superutilisateur Django (intervention exceptionnelle). Aucun n'est
    un profil métier : le niveau métier vient du seul rôle hiérarchique."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return frozenset()
    profile = getattr(user, "profile", None)
    statuts = set()
    if profile and profile.role == "MASTER_ADMIN":
        statuts.add(GENERAL)
    if profile and profile.administrateur_technique:
        statuts.add(TECHNIQUE)
    if user.is_superuser:
        statuts.add(SUPERUTILISATEUR_DJANGO)
    return frozenset(statuts)


def niveau_ecriture(user) -> RoleLevel:
    """Niveau pris en compte par les seuils d'écriture sur les données du bord : le soutien à terre et le
    commandant en second retombent au niveau équipier (ils gardent `user_role_level` pour la lecture et
    pour les workflows qui les nomment : programme du bâtiment, visas)."""
    from .scopes import soutien_a_terre

    niveau = user_role_level(user)
    if niveau == RoleLevel.MASTER_ADMIN:
        return niveau
    profile = getattr(user, "profile", None)
    if soutien_a_terre(user) or (profile and profile.role in ROLES_SANS_ECRITURE_HERITEE):
        return RoleLevel.EQUIPIER
    return niveau
