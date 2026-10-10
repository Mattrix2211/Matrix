"""Commandants adjoints (COMAEQ, COMOPS, COMANAV, COMAVIA) : routage des visas par service.

Objet -> service responsable -> commandant adjoint du service -> titulaire actif
du bâtiment (et de l'équipage en double équipage).
"""
from django.contrib.auth import get_user_model

from accounts.models import Roles


def service_de(user):
    """Service du marin, quel que soit son niveau de rattachement (service, secteur ou section)."""
    profil = getattr(user, "profile", None)
    if profil is None:
        return None
    if profil.service_id:
        return profil.service
    if profil.sector_id:
        return profil.sector.service
    if profil.section_id:
        return profil.section.sector.service
    return None


def commandant_adjoint_du_service(service):
    """Code du commandant adjoint dont dépend le service ; chaîne vide si non configuré."""
    return service.commandant_adjoint if service else ""


def titulaires_commandant_adjoint(navire, code, equipage=""):
    """Titulaires actifs d'une fonction de commandant adjoint sur un bâtiment.

    En double équipage, ils appartiennent à l'équipage concerné (à défaut, celui à bord).
    """
    if navire is None or not code:
        return get_user_model().objects.none()
    qs = get_user_model().objects.filter(
        is_active=True, profile__ship=navire, profile__role=Roles.ETAT_MAJOR, profile__fonction_coma=code
    )
    equipage = equipage or navire.equipage_a_bord
    if navire.double_equipage and equipage:
        qs = qs.filter(profile__equipage=equipage)
    return qs


def titulaires_du_service(service, equipage=""):
    """Titulaires du commandant adjoint dont dépend le service (vide si non configuré)."""
    if service is None:
        return get_user_model().objects.none()
    return titulaires_commandant_adjoint(service.ship, commandant_adjoint_du_service(service), equipage)


def est_commandant_adjoint_du_service(user, service, equipage=""):
    """Vrai si `user` est titulaire du commandant adjoint dont dépend `service`."""
    return titulaires_du_service(service, equipage).filter(pk=user.pk).exists()
