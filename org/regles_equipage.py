"""Règles de cohérence du double équipage (page Notion « Organigramme et rôles »
§9, §11 et décisions Matrix du 30/09/2026), écrites UNE seule fois et réutilisées
par le modèle (clean/save), l'administration Django, l'API et les vues.

Ce module n'importe aucun modèle : il est appelé depuis org/models.py."""


def titulaire_sans_equipage(ship, poste, titulaire):
    """Vrai si `titulaire` n'a aucun équipage alors que `poste` est un poste
    d'équipage d'un bâtiment à double équipage : on ne peut pas savoir de quel
    équipage il est."""
    return (
        ship.double_equipage and poste.equipage_id is not None
        and titulaire is not None and titulaire.profile.equipage_id is None
    )


def erreur_titulaire_equipage(ship, equipage, titulaire, sigle):
    """Message d'erreur français si `titulaire` ne peut pas tenir le poste
    `sigle` (COMAEQ, COMOPS, COMANAV, COMAVIA) de `equipage`, sinon None.

    En double équipage, le titulaire d'un poste de commandant adjoint doit
    appartenir à l'équipage concerné : ni sans équipage, ni de l'autre équipage."""
    if titulaire is None or equipage is None or not ship.double_equipage:
        return None
    equipage_du_marin = titulaire.profile.equipage_id
    if equipage_du_marin is None:
        return (
            f"Ce marin n'est rattaché à aucun équipage : rattachez-le d'abord à l'équipage "
            f"{equipage.nom} (page « Équipages »), puis désignez-le {sigle}."
        )
    if equipage_du_marin != equipage.pk:
        return f"Ce marin appartient à l'autre équipage : le {sigle} doit être de l'équipage {equipage.nom}."
    return None


def erreur_postes_du_titulaire(user, equipage_apres):
    """Message d'erreur français si `user`, titulaire d'un poste COMAEQ, COMOPS,
    COMANAV, COMAVIA ou de commandant en second d'un bâtiment à double équipage,
    ne peut pas passer à `equipage_apres` (None = aucun équipage, cas d'un
    changement de bâtiment) sans que le poste soit d'abord libéré, sinon None.

    Les postes de bâtiments à équipage unique ne sont pas concernés."""
    postes = [
        (poste.sigle, poste)
        for poste in user.commandants_adjoints_titulaire.select_related("ship", "equipage")
    ] + [
        (poste.get_libelle_display(), poste)
        for poste in user.postes_en_second.select_related("ship", "equipage")
    ]
    cible_id = equipage_apres.pk if equipage_apres is not None else None
    bloquants = [
        f"{nom} de l'équipage {poste.equipage.nom}"
        for nom, poste in postes
        if poste.equipage_id is not None and poste.ship.double_equipage and poste.equipage_id != cible_id
    ]
    if not bloquants:
        return None
    destination = f"l'équipage {equipage_apres.nom}" if equipage_apres is not None else "aucun équipage"
    return (
        f"{user.get_full_name() or user.username} est titulaire du poste {' et du poste '.join(bloquants)} : "
        f"libérez d'abord ce poste (Réglages, commandants adjoints ou commandant en second) avant de le "
        f"rattacher à {destination}."
    )


def erreur_poste_du_service(service, poste):
    """Message d'erreur si le poste de commandant adjoint `poste` ne peut pas
    porter `service` (autre unité ou autre équipage), sinon None."""
    if poste is None:
        return None
    if poste.ship_id != service.ship_id:
        return "Ce poste (COMAEQ, COMOPS, COMANAV, COMAVIA) n'appartient pas à l'unité du service."
    if poste.equipage_id != service.equipage_id:
        return "Le service et le poste doivent appartenir au même équipage."
    return None
