"""Écriture des commandants adjoints : bornée aux services qui leur sont rattachés.

Le niveau « état-major » commun au COMAEQ, au COMOPS, au COMANAV et au COMAVIA franchit les seuils d'écriture de tout le
bâtiment. Ici, un état-major n'écrit que sur les services dont `Service.commandant_adjoint` est sa fonction ; sur les
autres il garde la lecture et les droits d'un équipier. Les autres rôles ne sont pas concernés (leur périmètre
hiérarchique borne déjà leurs écritures), ni les workflows qui nomment explicitement un commandant adjoint (visas).
"""
from django.db.models import Q

from accounts.models import Roles

from .roles import RoleLevel, niveau_ecriture


def _est_etat_major(user):
    profil = getattr(user, "profile", None)
    return bool(profil and profil.role == Roles.ETAT_MAJOR and not getattr(user, "is_superuser", False))


def services_rattaches(user):
    """Ids des services rattachés à la fonction de commandant adjoint de `user` sur son bâtiment (vide sans fonction)."""
    from org.models import Service

    profil = user.profile
    if not profil.fonction_coma or not profil.ship_id:
        return set()
    return set(Service.objects.filter(
        ship_id=profil.ship_id, commandant_adjoint=profil.fonction_coma, archived=False,
    ).values_list("pk", flat=True))


def peut_ecrire_sur_service(user, service_id):
    """Vrai si `user` peut écrire sur les données du service `service_id` (None : objet sans service)."""
    if not _est_etat_major(user):
        return True
    return service_id is not None and service_id in services_rattaches(user)


def service_de(objet):
    """Id du service d'un objet métier, directement ou par son matériel, son installation, son plan ou sa pièce."""
    if objet is None:
        return None
    if getattr(objet, "service_id", None):
        return objet.service_id
    for chemin in (("asset",), ("installation",), ("installation_maintenance", "installation"), ("plan", "asset"),
                   ("plan", "installation_maintenance", "installation"), ("piece",), ("asset_type", "sector"), ("sector",)):
        courant = objet
        for attribut in chemin:
            courant = getattr(courant, attribut, None)
            if courant is None:
                break
        else:
            if getattr(courant, "service_id", None):
                return courant.service_id
    return None


def niveau_ecriture_sur(user, objet=None, service_id=None):
    """Niveau d'écriture applicable à un objet (ou à un service) : celui du rôle, ramené au niveau équipier pour un
    état-major hors des services de sa fonction."""
    niveau = niveau_ecriture(user)
    if not _est_etat_major(user):
        return niveau
    cible = service_id if service_id is not None else service_de(objet)
    return niveau if peut_ecrire_sur_service(user, cible) else RoleLevel.EQUIPIER


def niveau_ecriture_ui(user):
    """Niveau pour afficher les commandes d'écriture d'une page de liste : un état-major sans service rattaché n'en a pas."""
    niveau = niveau_ecriture(user)
    if not _est_etat_major(user):
        return niveau
    return niveau if services_rattaches(user) else RoleLevel.EQUIPIER


def q_ecriture(user, chemin_service):
    """Filtre des objets sur lesquels `user` peut écrire, d'après le chemin du service (ex. « service_id »)."""
    if not _est_etat_major(user):
        return Q()
    return Q(**{f"{chemin_service}__in": services_rattaches(user)})


def verifier_cible_ecriture(user, donnees, exiger_cible=False):
    """Refuse (PermissionDenied) qu'un état-major rattache un objet à un service, secteur ou section d'un autre
    commandant adjoint, d'après les champs du formulaire."""
    from django.core.exceptions import PermissionDenied
    from org.models import Section, Sector

    if not _est_etat_major(user):
        return
    rattaches = services_rattaches(user)
    cibles = []
    if donnees.get("service_id"):
        cibles.append(("service", donnees.get("service_id")))
    if donnees.get("sector_id"):
        cibles.append(("sector", donnees.get("sector_id")))
    if donnees.get("section_id"):
        cibles.append(("section", donnees.get("section_id")))
    for genre, valeur in cibles:
        try:
            pk = int(valeur)
        except (TypeError, ValueError):
            raise PermissionDenied
        if genre == "service":
            service_id = pk
        elif genre == "sector":
            service_id = Sector.objects.filter(pk=pk).values_list("service_id", flat=True).first()
        else:
            service_id = Section.objects.filter(pk=pk).values_list("sector__service_id", flat=True).first()
        if service_id not in rattaches:
            raise PermissionDenied
    if (exiger_cible and not cibles) or not rattaches:
        raise PermissionDenied
