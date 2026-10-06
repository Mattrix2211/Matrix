"""Double équipage : l'équipage à terre consulte le bâtiment en lecture seule."""


def equipage_a_terre_lecture_seule(user, navire=None):
    """Vrai si le marin appartient à l'équipage qui n'est pas à bord d'un bâtiment à double équipage.

    Sans équipage renseigné, ou pour un bâtiment à équipage unique, aucune restriction.
    """
    profil = getattr(user, "profile", None)
    if profil is None or user.is_superuser:
        return False
    navire = navire or profil.ship
    if navire is None or not navire.double_equipage or not profil.equipage:
        return False
    return profil.equipage != navire.equipage_a_bord
