"""Partage ciblé d'une information de passation (AC-03) : création, révocation, destinataires proposés, trace et notification.

Règles : une seule ligne à la fois, lecture seule, jamais la passation entière ; l'émetteur doit couvrir la ligne par son propre
périmètre (aucun partage transitif d'une ligne reçue, aucun droit conféré par un statut d'administration) ; la ligne ne doit pas être
marquée non partageable ; le destinataire relève du bâtiment de la synthèse ; chaque partage et chaque révocation sont historisés
(auteur, destinataire, date) et jamais effacés. Le destinataire est évalué à la lecture : une mutation ou une révocation joue
immédiatement ; les données déjà consultées, imprimées ou exportées avant révocation restent entre les mains de leur lecteur.
Un partage par émetteur : si deux responsables partagent la même information avec la même cible, chacun a sa ligne d'historique, et
une autorité qui révoque retire tous les partages équivalents qu'elle a le droit de retirer.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from matrix.core.mixins import utilisateurs_visibles_par
from matrix.core.scopes import navire_q
from notifications.models import Notification
from notifications.services import creer_notifications_en_masse
from org.models import PartagePassation, Section, Sector, Service, SynthesePassation

from .passation_perimetre import ligne_de, peut_partager, peut_revoquer

TYPES = PartagePassation.Destinataire
User = get_user_model()
ERREUR_DESTINATAIRE = "Destinataire introuvable dans ce bâtiment."  # message unique : aucun indice sur les comptes d'un autre bâtiment


def destinataires_proposes(synthese, user):
    """Choix de destinataires du bâtiment de la synthèse : marins que l'annuaire de `user` lui montre (jamais plus), fonctions,
    sections, secteurs, services."""
    navire = synthese.ship
    marins = utilisateurs_visibles_par(user).filter(navire_q(navire.pk, "profile__"), is_active=True).order_by("username")
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


def _cible(synthese, user, type_destinataire, valeur):
    """(champs du modèle, libellé figé) du destinataire demandé, ou ValidationError au message unique (hors du bâtiment, inconnu,
    fonction inexistante : rien ne distingue ces cas)."""
    navire = synthese.ship
    try:
        if type_destinataire == TYPES.MARIN:
            marin = utilisateurs_visibles_par(user).select_related("profile").get(pk=int(valeur), is_active=True)
            if marin.profile.navire_id_effectif != navire.pk:
                raise ValidationError(ERREUR_DESTINATAIRE)
            return {"marin": marin}, marin.get_full_name() or marin.get_username()
        if type_destinataire == TYPES.SERVICE:
            service = Service.objects.get(pk=int(valeur), ship=navire)
            return {"service": service}, f"service {service.name}"
        if type_destinataire == TYPES.SECTEUR:
            secteur = Sector.objects.select_related("service").get(pk=int(valeur), service__ship=navire)
            return {"sector": secteur}, f"secteur {secteur}"
        if type_destinataire == TYPES.SECTION:
            section = Section.objects.select_related("sector__service").get(pk=int(valeur), sector__service__ship=navire)
            return {"section": section}, f"section {section}"
        if type_destinataire == TYPES.FONCTION:
            noms = dict(destinataires_proposes(synthese, user)["fonctions"])
            if valeur not in noms:
                raise ValidationError(ERREUR_DESTINATAIRE)
            return {"fonction": valeur}, noms[valeur]
    except (ValueError, TypeError, ObjectDoesNotExist):  # inconnu, inactif, sans profil : un seul message
        pass
    raise ValidationError(ERREUR_DESTINATAIRE)


def _membres(partage):
    """Marins actuellement désignés par un partage (pour les prévenir), requêtes sur la hiérarchie des profils."""
    if partage.type_destinataire == TYPES.MARIN:
        return [partage.marin] if partage.marin_id else []
    profils = UserProfile.objects.filter(navire_q(partage.synthese.ship_id), user__is_active=True).select_related("user")
    if partage.type_destinataire == TYPES.FONCTION:
        genre, _, nom = partage.fonction.partition(":")
        profils = profils.filter(fonction_coma=nom, role="ETAT_MAJOR") if genre == "coma" else profils.filter(fonction_service=nom)
    elif partage.type_destinataire == TYPES.SECTION:
        profils = profils.filter(section_id=partage.section_id)
    elif partage.type_destinataire == TYPES.SECTEUR:
        profils = profils.filter(Q(sector_id=partage.sector_id) | Q(section__sector_id=partage.sector_id))
    else:
        profils = profils.filter(Q(service_id=partage.service_id) | Q(sector__service_id=partage.service_id)
                                 | Q(section__sector__service_id=partage.service_id))
    return [p.user for p in profils if p.navire_id_effectif == partage.synthese.ship_id]


def partager(user, synthese, cle, type_destinataire, valeur):
    """Partage la ligne `cle` ; renvoie (partage, créé). PermissionDenied si `user` ne peut pas partager cette ligne.

    Un même émetteur ne crée pas deux partages actifs identiques (double clic, requêtes simultanées : la synthèse est verrouillée) ;
    un autre émetteur a son propre partage, donc sa propre trace."""
    ligne = ligne_de(synthese, cle)
    if not peut_partager(user, synthese, ligne):
        raise PermissionDenied
    cible, libelle_cible = _cible(synthese, user, type_destinataire, valeur)
    with transaction.atomic():
        SynthesePassation.objects.select_for_update().get(pk=synthese.pk)
        existant = PartagePassation.objects.filter(
            synthese=synthese, cle_ligne=cle, type_destinataire=type_destinataire, revoque_le__isnull=True, partage_par=user, **cible).first()
        if existant:
            return existant, False
        partage = PartagePassation.objects.create(
            synthese=synthese, cle_ligne=cle, libelle=ligne["titre"][:200], partage_par=user,
            type_destinataire=type_destinataire, destinataire_libelle=libelle_cible[:200], **cible)
        AuditLog.objects.create(
            actor=user, action="passation_partagee",
            details=f"synthese={synthese.pk}; ligne={cle}; destinataire={partage.libelle_destinataire()}; partage={partage.pk}")
        auteur = user.get_full_name() or user.get_username()
        creer_notifications_en_masse(
            Notification(user=m, target=synthese, verb=f"{auteur} a partagé avec vous une information de la synthèse de passation de "
                                                       f"{synthese.ship.name}.")
            for m in {m.pk: m for m in _membres(partage) if m.pk != user.pk}.values())
    return partage, True


def revoquer(user, partage):
    """Révoque un partage actif (auteur du partage ou autorité qui couvre la ligne) ; la trace est conservée.

    Tous les partages actifs équivalents (même information, même destinataire) que `user` a le droit de retirer le sont : une
    révocation ne laisse pas le destinataire lire encore par un doublon. Renvoie le nombre de partages révoqués."""
    if not peut_revoquer(user, partage):
        raise PermissionDenied
    equivalents = PartagePassation.objects.filter(
        synthese_id=partage.synthese_id, cle_ligne=partage.cle_ligne, type_destinataire=partage.type_destinataire,
        marin_id=partage.marin_id, fonction=partage.fonction, service_id=partage.service_id, sector_id=partage.sector_id,
        section_id=partage.section_id, revoque_le__isnull=True)
    revoques = 0
    with transaction.atomic():
        for candidat in equivalents.select_related("synthese"):
            if not peut_revoquer(user, candidat):
                continue
            if PartagePassation.objects.filter(pk=candidat.pk, revoque_le__isnull=True).update(revoque_le=timezone.now(), revoque_par=user):
                revoques += 1
                AuditLog.objects.create(
                    actor=user, action="passation_partage_revoque",
                    details=f"synthese={candidat.synthese_id}; ligne={candidat.cle_ligne}; destinataire={candidat.libelle_destinataire()}; "
                            f"partage={candidat.pk}")
    return revoques
