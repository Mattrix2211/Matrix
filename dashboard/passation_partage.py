"""Partage ciblé d'une information de passation (AC-03) : création, révocation, destinataires proposés, trace et notification.

Règles : une seule ligne à la fois, lecture seule, jamais la passation entière ; l'émetteur doit couvrir la ligne par son propre
périmètre (aucun partage transitif d'une ligne reçue, aucun droit conféré par un statut d'administration) ; la ligne ne doit pas être
marquée non partageable ; le destinataire relève du bâtiment de la synthèse ; chaque partage et chaque révocation sont historisés
(auteur, destinataire, date) et jamais effacés. Le destinataire est évalué à la lecture : une mutation ou une révocation joue
immédiatement ; les données déjà consultées, imprimées ou exportées avant révocation restent entre les mains de leur lecteur.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from annonces.services import chaine
from notifications.models import Notification
from org.models import PartagePassation, Section, Sector, Service

from .passation_perimetre import ligne_de, peut_partager, peut_revoquer

TYPES = PartagePassation.Destinataire
User = get_user_model()


def _du_batiment(marins, navire_id):
    return [m for m in marins if getattr(getattr(m, "profile", None), "navire_id_effectif", None) == navire_id]


def destinataires_proposes(synthese):
    """Choix de destinataires du bâtiment de la synthèse : marins actifs, fonctions, sections, secteurs, services."""
    navire = synthese.ship
    marins = _du_batiment(User.objects.filter(is_active=True).select_related("profile").order_by("username"), navire.pk)
    fonctions = [(f"coma:{code}", f"Commandant adjoint {label}") for code, label in
                 dict(Service._meta.get_field("commandant_adjoint").choices).items() if code]
    fonctions += [(f"service:{nom}", nom) for nom in ServiceFunctionChoice.objects.filter(active=True).order_by("name").values_list("name", flat=True)]
    return {
        "marins": [(m.pk, m.get_full_name() or m.get_username()) for m in marins],
        "fonctions": fonctions,
        "sections": [(s.pk, str(s)) for s in Section.objects.filter(sector__service__ship=navire).select_related("sector__service")],
        "secteurs": [(s.pk, str(s)) for s in Sector.objects.filter(service__ship=navire).select_related("service")],
        "services": [(s.pk, s.name) for s in Service.objects.filter(ship=navire, archived=False)],
    }


def _cible(synthese, type_destinataire, valeur):
    """(champs du modèle, libellé) du destinataire demandé, ou ValidationError (hors du bâtiment, inconnu, fonction inexistante)."""
    navire = synthese.ship
    try:
        if type_destinataire == TYPES.MARIN:
            marin = User.objects.select_related("profile").get(pk=int(valeur), is_active=True)
            if marin.profile.navire_id_effectif != navire.pk:
                raise ValidationError("Ce marin ne relève pas du bâtiment de la synthèse.")
            return {"marin": marin}
        if type_destinataire == TYPES.SERVICE:
            return {"service": Service.objects.get(pk=int(valeur), ship=navire)}
        if type_destinataire == TYPES.SECTEUR:
            return {"sector": Sector.objects.get(pk=int(valeur), service__ship=navire)}
        if type_destinataire == TYPES.SECTION:
            return {"section": Section.objects.get(pk=int(valeur), sector__service__ship=navire)}
        if type_destinataire == TYPES.FONCTION:
            if valeur not in {cle for cle, _ in destinataires_proposes(synthese)["fonctions"]}:
                raise ValidationError("Cette fonction n'existe pas.")
            return {"fonction": valeur}
    except (ValueError, TypeError, User.DoesNotExist, Service.DoesNotExist, Sector.DoesNotExist, Section.DoesNotExist):
        raise ValidationError("Destinataire introuvable dans ce bâtiment.")
    raise ValidationError("Type de destinataire inconnu.")


def _membres(partage):
    """Marins actuellement désignés par un partage (pour les prévenir)."""
    if partage.type_destinataire == TYPES.MARIN:
        return [partage.marin]
    profils = UserProfile.objects.filter(user__is_active=True).select_related("user")
    if partage.type_destinataire == TYPES.FONCTION:
        genre, _, nom = partage.fonction.partition(":")
        profils = profils.filter(fonction_coma=nom, role="ETAT_MAJOR") if genre == "coma" else profils.filter(fonction_service=nom)
        return [p.user for p in profils if p.navire_id_effectif == partage.synthese.ship_id]
    cle = {TYPES.SECTION: ("section", partage.section_id), TYPES.SECTEUR: ("secteur", partage.sector_id),
           TYPES.SERVICE: ("service", partage.service_id)}[partage.type_destinataire]
    indice = {"service": 1, "secteur": 2, "section": 3}[cle[0]]
    return [p.user for p in profils if p.navire_id_effectif == partage.synthese.ship_id and chaine(p.user)[indice] == cle[1]]


def partager(user, synthese, cle, type_destinataire, valeur):
    """Partage la ligne `cle` ; renvoie (partage, créé). PermissionDenied si `user` ne peut pas partager cette ligne."""
    ligne = ligne_de(synthese, cle)
    if not peut_partager(user, synthese, ligne):
        raise PermissionDenied
    cible = _cible(synthese, type_destinataire, valeur)
    existant = PartagePassation.objects.filter(
        synthese=synthese, cle_ligne=cle, type_destinataire=type_destinataire, revoque_le__isnull=True,
        **cible,
    ).first()
    if existant:
        return existant, False
    with transaction.atomic():
        partage = PartagePassation.objects.create(
            synthese=synthese, cle_ligne=cle, libelle=ligne["titre"][:200], partage_par=user,
            type_destinataire=type_destinataire, **cible)
        AuditLog.objects.create(
            actor=user, action="passation_partagee",
            details=f"synthese={synthese.pk}; ligne={cle}; destinataire={partage.libelle_destinataire()}; partage={partage.pk}")
    for marin in {m.pk: m for m in _membres(partage) if m.pk != user.pk}.values():
        Notification.objects.create(
            user=marin, target=synthese,
            verb=f"{user.get_full_name() or user.get_username()} a partagé avec vous une information de la synthèse de passation de {synthese.ship.name}.")
    return partage, True


def revoquer(user, partage):
    """Révoque un partage actif (auteur du partage ou autorité qui couvre la ligne) ; la trace est conservée."""
    if not peut_revoquer(user, partage):
        raise PermissionDenied
    with transaction.atomic():
        if not PartagePassation.objects.filter(pk=partage.pk, revoque_le__isnull=True).update(revoque_le=timezone.now(), revoque_par=user):
            return False
        AuditLog.objects.create(
            actor=user, action="passation_partage_revoque",
            details=f"synthese={partage.synthese_id}; ligne={partage.cle_ligne}; destinataire={partage.libelle_destinataire()}; partage={partage.pk}")
    return True
