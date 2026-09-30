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
