"""Double équipage : l'équipage à terre consulte le bâtiment en lecture seule."""
from django.contrib.auth import get_user_model

from accounts.models import AuditLog, Roles
from matrix.core.scopes import is_master_admin

MESSAGE_EQUIPAGE_OBLIGATOIRE = "L'équipage est obligatoire sur un bâtiment à double équipage."


def equipage_a_terre_lecture_seule(user):
    """Vrai si le marin appartient à l'équipage qui n'est pas à bord de son bâtiment à double équipage.

    Sans équipage renseigné, ou pour un bâtiment à équipage unique, aucune restriction.
    """
    profil = getattr(user, "profile", None)
    if profil is None or user.is_superuser:
        return False
    navire = profil.ship
    if navire is None or not navire.double_equipage or not profil.equipage:
        return False
    return profil.equipage != navire.equipage_a_bord


def suivi_a_terre_sans_validation(user):
    """Responsable de classe ou de spécialité à terre : il consulte et commente, il ne valide pas."""
    from training.models import navire_de

    return not is_master_admin(user) and navire_de(user) is None


def peut_changer_equipage_a_bord(user, navire):
    """Seul le commandant du bâtiment (ou l'administrateur général) fait la relève."""
    if is_master_admin(user):
        return True
    profil = getattr(user, "profile", None)
    return bool(profil and profil.role == Roles.COMMANDANT and profil.ship_id == navire.pk)


def tracer_changement_equipage(auteur, navire, avant):
    """Inscrit au journal toute modification du double équipage ; `avant` = (double_equipage, equipage_a_bord)."""
    apres = (navire.double_equipage, navire.equipage_a_bord)
    if avant != apres:
        AuditLog.objects.create(
            actor=auteur, action="changement_equipage",
            details=(
                f"navire={navire.name}; double_equipage={avant[0]} -> {apres[0]}; "
                f"equipage_a_bord={avant[1] or '—'} -> {apres[1] or '—'}"
            ),
        )


def equipage_manquant(navire, equipage):
    """Vrai si le bâtiment est à double équipage et que l'équipage du marin n'est pas renseigné."""
    return bool(navire and navire.double_equipage and not equipage)


def marins_sans_equipage(navire):
    """Marins d'un bâtiment à double équipage dont l'équipage n'est pas renseigné."""
    if not navire.double_equipage:
        return get_user_model().objects.none()
    return get_user_model().objects.filter(profile__ship=navire, profile__equipage="").order_by("last_name", "username")
