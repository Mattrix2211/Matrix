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
from org.models import Ship
from quarts.models import (
    CreneauQuart,
    CreneauServiceGarde,
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
        if (designation.ship_id, designation.service_id, designation.sector_id, designation.section_id) == cible:
            return designation
    return None


def peut_activer_liste(user, liste):
    return designation_chef_de_liste(user, liste) is not None


def conflits_activation(liste, a_partir_de=None):
    """Créneaux de la liste qui recouvrent un quart à la mer publié ou un autre service à quai
    en vigueur pour le même marin, à partir de l'instant donné (pas de rétroactivité).
    Matrix ne modifie jamais ces créneaux : le conflit est présenté aux responsables."""
    a_partir_de = a_partir_de or timezone.now()
    conflits = []
    for creneau in liste.creneaux.select_related("marin").filter(marin__isnull=False, fin__gt=a_partir_de):
        filtres = dict(marin=creneau.marin, debut__lt=creneau.fin, fin__gt=max(creneau.debut, a_partir_de))
        mer = CreneauQuart.objects.filter(quart__statut="PUBLIEE", **filtres).select_related("quart")
        quai = CreneauServiceGarde.applicables().filter(**filtres).exclude(service_garde=liste).select_related("service_garde")
        for autre in (*mer, *quai):
            genre = "quart à la mer" if isinstance(autre, CreneauQuart) else "service à quai"
            conflits.append({
                "marin": creneau.marin, "creneau": creneau, "autre": autre, "genre": genre,
                "liste_autre": autre.quart if isinstance(autre, CreneauQuart) else autre.service_garde,
            })
    return conflits


def decrire_conflit(conflit):
    marin, autre = conflit["marin"], conflit["autre"]
    return (
        f"{marin.get_full_name() or marin.username} : {conflit['genre']} « {autre.poste} » du "
        f"{timezone.localtime(autre.debut):%d/%m %H:%M} au {timezone.localtime(autre.fin):%d/%m %H:%M} "
        f"recouvre le service « {conflit['creneau'].poste} »."
    )


def _fonctions_cumulees(user, liste):
    """Fonctions de commandement du même agent, signalées dans la trace sans conférer de droit."""
    ship = Ship.objects.filter(pk=navire_id_du_perimetre(liste.ship, liste.service, liste.sector, liste.section)).first()
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
    return liste


@transaction.atomic
def activer_liste(user, liste):
    """Rend la liste applicable à partir de maintenant, sans rétroactivité."""
    liste = ServiceGarde.objects.select_for_update().get(pk=liste.pk)
    designation = designation_chef_de_liste(user, liste)
    if designation is None:
        raise ActivationImpossible("Seul le chef de liste désigné pour ce périmètre peut activer la liste.")
    if liste.statut != ServiceGarde.STATUT_PUBLIEE or liste.application != ServiceGarde.APPLICATION_PREVISIONNELLE:
        raise ActivationImpossible("Seule une liste publiée à titre prévisionnel peut être activée.")
    maintenant = timezone.now()
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
            "en qualité de chef de liste désigné."
            + (f" Fonction {', '.join(cumul)} du même agent non utilisée pour cet acte." if cumul else "")
        ),
    )
    for creneau in liste.creneaux.select_related("marin").filter(marin__isnull=False, fin__gt=maintenant):
        Notification.objects.create(
            user=creneau.marin,
            verb=f"La liste « {liste.nom or liste.perimetre} » est maintenant active : votre service du {timezone.localtime(creneau.debut):%d/%m/%Y à %H:%M} est confirmé.",
            url=reverse("quarts-index"),
        )
    return liste
