"""Changement d'équipage d'un service (double équipage) : la branche
Service -> Secteurs -> Sections change ENSEMBLE ou pas du tout, après contrôle
des postes et des affectations existants. En cas de conflit, le changement est
bloqué et chaque poste ou affectation à corriger est nommé (décision du
30/09/2026).

Appelé par Service.clean() (administration, formulaires), Service.save()
(garantie au niveau modèle) et ServiceSerializer (API). Aucun import de modèle
au chargement : ce module est utilisé depuis org/models.py."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


def _nom_equipage(equipage):
    return f"l'équipage {equipage.nom}" if equipage is not None else "aucun équipage"


def _nom_marin(user):
    return user.get_full_name() or user.username


def conflits_changement(service, nouvel_equipage):
    """Liste de messages français décrivant ce qui empêche `service` de passer
    à `nouvel_equipage` (None = équipage unique). Liste vide : changement possible.

    Contrôlés : poste de commandant adjoint du service, service homonyme dans
    l'équipage d'arrivée, marins d'un AUTRE équipage affectés au service, à un
    de ses secteurs ou à une de ses sections (chefs compris). Les marins sans
    équipage ne bloquent pas : ils suivront leur rattachement à la page « Équipages »."""
    from accounts.models import UserProfile
    from django.db.models import Q

    from .models import Service

    if not service.pk:
        return []
    conflits = []
    poste = service.commandant_adjoint
    if poste is not None and poste.equipage_id != (nouvel_equipage.pk if nouvel_equipage else None):
        conflits.append(
            f"Le service « {service.name} » dépend du poste {poste.sigle} de "
            f"{_nom_equipage(poste.equipage)} : détachez-le de ce poste (Réglages > Commandants adjoints) "
            f"ou rattachez-le à un poste de {_nom_equipage(nouvel_equipage)}."
        )
    if Service.objects.filter(
        ship_id=service.ship_id, equipage=nouvel_equipage, name=service.name
    ).exclude(pk=service.pk).exists():
        conflits.append(
            f"Un service « {service.name} » existe déjà pour {_nom_equipage(nouvel_equipage)} : renommez l'un des deux."
        )
    if nouvel_equipage is not None:
        profils = UserProfile.objects.filter(
            Q(service=service) | Q(sector__service=service) | Q(section__sector__service=service),
            equipage__isnull=False,
        ).exclude(equipage=nouvel_equipage).select_related("user", "equipage", "service", "sector", "section")
        for profil in profils:
            lieu = (
                f"la section « {profil.section.name} »" if profil.section_id
                else f"le secteur « {profil.sector.name} »" if profil.sector_id
                else f"le service « {profil.service.name} »"
            )
            conflits.append(
                f"{_nom_marin(profil.user)} (équipage {profil.equipage.nom}, rôle {profil.role}) est affecté à {lieu} : "
                f"rattachez-le à {_nom_equipage(nouvel_equipage)} ou changez son affectation."
            )
    return conflits


def verifier_changement(service, nouvel_equipage):
    """Lève une ValidationError listant tous les conflits, sinon ne fait rien."""
    conflits = conflits_changement(service, nouvel_equipage)
    if conflits:
        raise ValidationError({"equipage": conflits})


def propager_aux_secteurs_et_sections(service):
    """Aligne l'équipage des secteurs et sections du service sur le sien."""
    from .models import Section, Sector

    maintenant = timezone.now()
    Sector.objects.filter(service=service).update(equipage=service.equipage, updated_at=maintenant)
    Section.objects.filter(sector__service=service).update(equipage=service.equipage, updated_at=maintenant)


def equipage_a_change(service):
    """Vrai si un service déjà enregistré change d'équipage (comparaison avec la base)."""
    from .models import Service

    if not service.pk:
        return False
    en_base = Service.objects.filter(pk=service.pk).values_list("equipage_id", flat=True).first()
    return en_base != service.equipage_id


def enregistrer_service(service, enregistrer):
    """Exécute `enregistrer()` (la sauvegarde du service). Si l'équipage du
    service change, contrôle d'abord les conflits puis enregistre le service et
    propage aux secteurs et sections dans UNE transaction : tout ou rien."""
    if not equipage_a_change(service):
        enregistrer()
        return
    with transaction.atomic():
        verifier_changement(service, service.equipage)
        enregistrer()
        propager_aux_secteurs_et_sections(service)
