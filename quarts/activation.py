"""Publication à titre prévisionnel et activation des listes de services à quai.

La validation (statut) et l'application (application) sont deux axes distincts : publier
ne rend jamais une liste applicable, seul le chef de liste désigné l'active."""
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.commandants_adjoints import titulaires_commandant_adjoint
from matrix.core.scopes import navire_id_du_perimetre
from notifications.models import Notification
from quarts.echanges import appliquer_echanges_prepares
from quarts.mouvements import mode_du_batiment, reevaluer_batiment
from org.models import Ship
from quarts.models import (
    CreneauQuart,
    CreneauServiceGarde,
    MouvementBatiment,
    ServiceGarde,
    equipage_de_la_liste,
    perimetre_de_mon_equipage,
)


class ActivationImpossible(Exception):
    """Refus métier, message affichable tel quel."""


def designation_chef_de_liste(user, liste):
    """Désignation de `user` pour EXACTEMENT le périmètre de la liste, ou None.
    Ni la supervision du commandement ni un rôle ne la remplacent."""
    if not user.is_active or not perimetre_de_mon_equipage(user, equipage_de_la_liste(liste)):
        return None
    cible = (liste.ship_id, liste.service_id, liste.sector_id, liste.section_id)
    for designation in user.designations_chef_de_liste.all():
        if (designation.ship_id, designation.service_id, designation.sector_id, designation.section_id) == cible and designation.couvre(liste.CODE_TYPE):
            return designation
    return None


def remplacement_actif(user, liste, instant=None):
    """Remplacement temporaire en cours de `user` pour exactement ce périmètre, cet équipage et ce type de liste."""
    instant = instant or timezone.now()
    if not user.is_active:
        return None
    ship = navire_de_la_liste(liste)
    for r in user.remplacements_chef_de_liste.filter(
        type_liste=liste.CODE_TYPE, revoque_le__isnull=True, debut__lte=instant, fin__gt=instant,
    ):
        meme_perimetre = (
            (r.perimetre_navire and liste.ship_id == r.ship_id)
            or (r.service_id and r.service_id == liste.service_id)
            or (r.sector_id and r.sector_id == liste.sector_id)
            or (r.section_id and r.section_id == liste.section_id)
        )
        if meme_perimetre and ship is not None and r.ship_id == ship.pk and r.equipage in ("", liste.equipage):
            return r
    return None


def habilitation_activation(user, liste):
    """(« chef » ou « remplaçant », objet) si `user` peut activer, reporter ou retirer cette prévision, sinon None."""
    designation = designation_chef_de_liste(user, liste)
    if designation is not None:
        return "chef", designation
    remplacement = remplacement_actif(user, liste)
    return ("remplacant", remplacement) if remplacement is not None else None


def capacite_texte(habilitation):
    genre, objet = habilitation
    if genre == "chef":
        return "en qualité de chef de liste désigné"
    return f"en qualité de remplaçant temporaire de {objet.titulaire.get_full_name() or objet.titulaire.username}, jusqu'au {timezone.localtime(objet.fin):%d/%m/%Y %H:%M}"


def peut_activer_liste(user, liste):
    return habilitation_activation(user, liste) is not None


def recouvrements_activation(liste, a_partir_de=None):
    """Recouvrements entre les créneaux de la liste et les autres affectations du même marin, à partir de
    l'instant d'activation (jamais de rétroactivité). Matrix ne modifie jamais ces créneaux.

    - BLOQUANT : deux services à quai en vigueur qui se recouvrent, ou un quart déjà en cours en même temps
      que le service (conflit actuel, le bâtiment étant à quai) ;
    - AVERTISSEMENT : un quart qui ne recouvre le service que dans le futur, tant que le régime n'est pas
      confirmé ; réévalué à chaque mouvement, modification de liste ou activation."""
    maintenant = a_partir_de or timezone.now()
    resultats = []
    for creneau in liste.creneaux.select_related("marin").filter(marin__isnull=False, fin__gt=maintenant):
        filtres = dict(marin=creneau.marin, debut__lt=creneau.fin, fin__gt=max(creneau.debut, maintenant))
        mer = CreneauQuart.objects.filter(quart__statut="PUBLIEE", **filtres).select_related("quart")
        quai = CreneauServiceGarde.applicables().filter(**filtres).exclude(service_garde=liste).select_related("service_garde")
        for autre in (*mer, *quai):
            en_mer = isinstance(autre, CreneauQuart)
            debut_commun = max(creneau.debut, autre.debut, maintenant)
            bloquant = not en_mer or debut_commun <= maintenant
            resultats.append({
                "marin": creneau.marin, "creneau": creneau, "autre": autre, "bloquant": bloquant,
                "genre": "quart à la mer" if en_mer else "service à quai",
                "liste_autre": autre.quart if en_mer else autre.service_garde,
            })
    return resultats


def conflits_activation(liste, a_partir_de=None):
    return [r for r in recouvrements_activation(liste, a_partir_de) if r["bloquant"]]


def avertissements_activation(liste, a_partir_de=None):
    return [r for r in recouvrements_activation(liste, a_partir_de) if not r["bloquant"]]


def decrire_conflit(conflit):
    marin, autre = conflit["marin"], conflit["autre"]
    return (
        f"{marin.get_full_name() or marin.username} : {conflit['genre']} « {autre.poste} » du "
        f"{timezone.localtime(autre.debut):%d/%m %H:%M} au {timezone.localtime(autre.fin):%d/%m %H:%M} "
        f"recouvre le service « {conflit['creneau'].poste} »."
    )


def navire_de_la_liste(liste):
    return Ship.objects.filter(pk=navire_id_du_perimetre(liste.ship, liste.service, liste.sector, liste.section)).first()


def _fonctions_cumulees(user, liste):
    """Fonctions de commandement du même agent, signalées dans la trace sans conférer de droit."""
    ship = navire_de_la_liste(liste)
    if ship is None:
        return []
    return [sigle for sigle in ("COMAEQ",) if titulaires_commandant_adjoint(ship, sigle, liste.equipage).filter(pk=user.pk).exists()]


@transaction.atomic
def publier_a_titre_previsionnel(user, liste, prise_effet_prevue):
    """PROPOSEE -> PUBLIEE sans effet : la liste reste prévisionnelle jusqu'à son activation."""
    liste = ServiceGarde.objects.select_for_update().get(pk=liste.pk)
    if liste.statut != ServiceGarde.STATUT_PROPOSEE:
        raise ActivationImpossible("Seule une liste proposée peut être publiée à titre prévisionnel.")
    if prise_effet_prevue is None:
        raise ActivationImpossible("La prise d'effet prévue est obligatoire pour publier à titre prévisionnel.")
    liste.publier(user)
    liste.application = ServiceGarde.APPLICATION_PREVISIONNELLE
    liste.prise_effet_prevue = prise_effet_prevue
    liste.prise_effet = None
    liste.save(update_fields=["application", "prise_effet_prevue", "prise_effet", "updated_at"])
    AuditLog.objects.create(
        actor=user, action="liste_service_previsionnelle",
        details=f"Service à quai #{liste.pk} ({liste.perimetre}) publié à titre prévisionnel ; prise d'effet prévue le {timezone.localtime(prise_effet_prevue):%d/%m/%Y à %H:%M}.",
    )
    if ship := navire_de_la_liste(liste):
        reevaluer_batiment(ship)
    return liste


@transaction.atomic
def activer_liste(user, liste):
    """Rend la liste applicable à partir de maintenant, sans rétroactivité."""
    liste = ServiceGarde.objects.select_for_update().get(pk=liste.pk)
    habilitation = habilitation_activation(user, liste)
    if habilitation is None:
        raise ActivationImpossible("Seul le chef de liste désigné pour ce périmètre, ou son remplaçant temporaire, peut activer la liste.")
    if liste.statut != ServiceGarde.STATUT_PUBLIEE or liste.application != ServiceGarde.APPLICATION_PREVISIONNELLE:
        raise ActivationImpossible("Seule une liste publiée à titre prévisionnel peut être activée.")
    maintenant = timezone.now()
    ship = navire_de_la_liste(liste)
    mode = mode_du_batiment(ship, maintenant) if ship else None
    if mode is None:
        raise ActivationImpossible(
            "Le mode du bâtiment n'est pas renseigné : une personne habilitée (COMAEQ ou commandant) doit d'abord "
            "l'initialiser, puis la liste pourra être activée."
        )
    if mode != MouvementBatiment.MODE_QUAI:
        raise ActivationImpossible(
            "Le bâtiment est à la mer : la liste ne peut être activée qu'après l'accostage confirmé par le COMAEQ ou le commandant. "
            "Elle reste publiée à titre prévisionnel."
        )
    conflits = conflits_activation(liste, maintenant)
    if conflits:
        raise ActivationImpossible(
            "Activation bloquée : des créneaux se recouvrent. Ils doivent être résolus par les responsables concernés "
            "(Matrix ne raccourcit aucun quart). " + " ".join(decrire_conflit(c) for c in conflits[:5])
            + (f" (+ {len(conflits) - 5} autre(s))" if len(conflits) > 5 else "")
        )
    liste.application = ServiceGarde.APPLICATION_ACTIVE
    liste.prise_effet = maintenant
    liste.active_le = maintenant
    liste.active_par = user
    liste.save(update_fields=["application", "prise_effet", "active_le", "active_par", "updated_at"])
    liste.alertes_activation.filter(fermee_le__isnull=True).update(fermee_le=maintenant, motif_fermeture="liste activée")
    cumul = _fonctions_cumulees(user, liste)
    prevue = f" (prise d'effet prévue le {timezone.localtime(liste.prise_effet_prevue):%d/%m/%Y à %H:%M})" if liste.prise_effet_prevue else ""
    AuditLog.objects.create(
        actor=user, action="liste_service_activee",
        details=(
            f"Service à quai #{liste.pk} ({liste.perimetre}) activé le {timezone.localtime(maintenant):%d/%m/%Y à %H:%M}{prevue} "
            f"{capacite_texte(habilitation)}."
            + (f" Fonction {', '.join(cumul)} du même agent non utilisée pour cet acte." if cumul else "")
        ),
    )
    appliquer_echanges_prepares(liste, user)
    for creneau in liste.creneaux.select_related("marin").filter(marin__isnull=False, fin__gt=maintenant):
        Notification.objects.create(
            user=creneau.marin,
            verb=f"La liste « {liste.nom or liste.perimetre} » est maintenant active : votre service du {timezone.localtime(creneau.debut):%d/%m/%Y à %H:%M} est confirmé.",
            url=reverse("quarts-index"),
        )
    if ship := navire_de_la_liste(liste):
        reevaluer_batiment(ship)
    return liste
