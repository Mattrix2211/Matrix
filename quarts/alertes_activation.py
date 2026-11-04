"""Rappels, alertes et escalade d'une liste à quai publiée à titre prévisionnel et non encore activée,
ainsi que report et retrait de la prévision (motif obligatoire, version de prévision incrémentée)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.commandants_adjoints import titulaires_commandant_adjoint
from matrix.core.scopes import navire_id_du_perimetre
from notifications.models import Notification, NotificationLevel
from org.models import Ship
from quarts.activation import ActivationImpossible, designation_chef_de_liste, navire_de_la_liste
from quarts.mouvements import reevaluer_batiment
from quarts.models import (
    AlerteActivation,
    ChefDeListe,
    ConfigurationActivation,
    ServiceGarde,
    commandants_en_second,
)

ECHEANCES_PAR_DEFAUT = {"rappel_minutes": 30, "alerte_minutes": 0, "escalade_minutes": 15}


def _navire(liste):
    return Ship.objects.filter(pk=navire_id_du_perimetre(liste.ship, liste.service, liste.sector, liste.section)).first()


def delais(ship):
    reglage = ConfigurationActivation.objects.filter(ship=ship).first() if ship else None
    return {cle: getattr(reglage, cle) if reglage else defaut for cle, defaut in ECHEANCES_PAR_DEFAUT.items()}


def echeances(liste):
    """Instants des trois étapes, calculés depuis la prise d'effet prévue et les délais du bâtiment."""
    d = delais(_navire(liste))
    prevue = liste.prise_effet_prevue
    alerte = prevue + timedelta(minutes=d["alerte_minutes"])
    return {
        AlerteActivation.ETAPE_RAPPEL: prevue - timedelta(minutes=d["rappel_minutes"]),
        AlerteActivation.ETAPE_ALERTE: alerte,
        AlerteActivation.ETAPE_ESCALADE: alerte + timedelta(minutes=d["escalade_minutes"]),
    }


def chefs_de_liste_habilites(liste):
    cible = dict(ship_id=liste.ship_id, service_id=liste.service_id, sector_id=liste.sector_id, section_id=liste.section_id)
    ids = ChefDeListe.objects.filter(**cible).values_list("user_id", flat=True)
    return [u for u in User.objects.filter(pk__in=ids, is_active=True) if designation_chef_de_liste(u, liste)]


def destinataires_escalade(liste):
    """COMAEQ du bâtiment (et de l'équipage) ; à défaut le commandant en second, en supervision seulement."""
    ship = _navire(liste)
    if ship is None:
        return []
    comaeq = list(titulaires_commandant_adjoint(ship, "COMAEQ", liste.equipage))
    if comaeq:
        return comaeq
    return list(commandants_en_second(ship, liste.equipage))


def _textes(liste, etape):
    nom = liste.nom or liste.perimetre
    prevue = f"{timezone.localtime(liste.prise_effet_prevue):%d/%m/%Y à %H:%M}"
    return {
        AlerteActivation.ETAPE_RAPPEL: (f"Rappel : la liste « {nom} » doit prendre effet le {prevue}. Pensez à l'activer.", NotificationLevel.INFO),
        AlerteActivation.ETAPE_ALERTE: (f"La liste « {nom} » devait prendre effet le {prevue} et n'est pas activée : activez-la ou reportez-la.", NotificationLevel.WARNING),
        AlerteActivation.ETAPE_ESCALADE: (f"La liste « {nom} » n'est toujours pas activée (prise d'effet prévue le {prevue}). Suivi demandé auprès du chef de liste.", NotificationLevel.WARNING),
    }[etape]


def _creer_alerte(liste, etape):
    """Crée l'alerte et notifie une seule fois ; une personne cumulant plusieurs fonctions reçoit un seul message."""
    try:
        with transaction.atomic():
            alerte = AlerteActivation.objects.create(liste=liste, etape=etape, version_prevision=liste.version_prevision)
    except IntegrityError:
        return None
    destinataires = destinataires_escalade(liste) if etape == AlerteActivation.ETAPE_ESCALADE else chefs_de_liste_habilites(liste)
    texte, niveau = _textes(liste, etape)
    for user in {u.pk: u for u in destinataires}.values():
        Notification.objects.create(user=user, verb=texte, level=niveau, url=reverse("garde-detail", args=[liste.pk]))
    return alerte


def terminer_listes_echues(maintenant):
    """Passe en « terminée » les listes ACTIVES dont la période est échue. Jamais une prévisionnelle,
    et jamais d'activation d'une autre liste en conséquence."""
    echues = ServiceGarde.objects.filter(
        statut=ServiceGarde.STATUT_PUBLIEE, application=ServiceGarde.APPLICATION_ACTIVE,
        date_fin__lt=timezone.localtime(maintenant).date(),
    )
    terminees = 0
    for liste in echues:
        terminees += 1
        liste.application = ServiceGarde.APPLICATION_TERMINEE
        liste.terminee_le = maintenant
        liste.save(update_fields=["application", "terminee_le", "updated_at"])
        AuditLog.objects.create(
            action="liste_service_terminee",
            details=f"Service à quai #{liste.pk} ({liste.perimetre}) terminé : sa période de validité est échue.",
        )
        if ship := _navire(liste):
            reevaluer_batiment(ship)
    return terminees


def traiter_echeances(maintenant=None):
    """Crée les alertes échues et termine les listes échues. Idempotent et sûr en exécution concurrente."""
    maintenant = maintenant or timezone.now()
    terminer_listes_echues(maintenant)
    creees = 0
    listes = ServiceGarde.objects.filter(
        statut=ServiceGarde.STATUT_PUBLIEE, application=ServiceGarde.APPLICATION_PREVISIONNELLE, prise_effet_prevue__isnull=False,
    )
    for liste in listes:
        for etape, instant in echeances(liste).items():
            if maintenant >= instant and _creer_alerte(liste, etape):
                creees += 1
    return creees


def fermer_alertes(liste, motif):
    return liste.alertes_activation.filter(fermee_le__isnull=True).update(fermee_le=timezone.now(), motif_fermeture=motif)


@transaction.atomic
def reporter_prise_effet(user, liste, nouvelle_prevue, motif):
    """Reporte la prise d'effet prévue : motif obligatoire, nouvelle version de prévision, rappels recalculés."""
    liste = ServiceGarde.objects.select_for_update().get(pk=liste.pk)
    if designation_chef_de_liste(user, liste) is None:
        raise ActivationImpossible("Seul le chef de liste désigné pour ce périmètre peut reporter la prise d'effet.")
    if liste.statut != ServiceGarde.STATUT_PUBLIEE or liste.application != ServiceGarde.APPLICATION_PREVISIONNELLE:
        raise ActivationImpossible("Seule une liste publiée à titre prévisionnel peut être reportée.")
    if not motif.strip():
        raise ActivationImpossible("Un motif est obligatoire pour reporter la prise d'effet.")
    if nouvelle_prevue is None or nouvelle_prevue <= timezone.now():
        raise ActivationImpossible("La nouvelle prise d'effet prévue doit être dans le futur.")
    ancienne = liste.prise_effet_prevue
    liste.prise_effet_prevue = nouvelle_prevue
    liste.version_prevision += 1
    liste.save(update_fields=["prise_effet_prevue", "version_prevision", "updated_at"])
    fermer_alertes(liste, "report de la prise d'effet")
    AuditLog.objects.create(
        actor=user, action="liste_service_reportee",
        details=(
            f"Service à quai #{liste.pk} ({liste.perimetre}) : prise d'effet prévue reportée du "
            f"{timezone.localtime(ancienne):%d/%m/%Y %H:%M} au {timezone.localtime(nouvelle_prevue):%d/%m/%Y %H:%M} "
            f"(version de prévision {liste.version_prevision}). Motif : {motif.strip()}."
        ),
    )
    return liste


@transaction.atomic
def retirer_previsionnelle(user, liste, motif):
    """Retire la prévision : la liste redevient un brouillon (versions conservées), alertes fermées."""
    liste = ServiceGarde.objects.select_for_update().get(pk=liste.pk)
    if designation_chef_de_liste(user, liste) is None:
        raise ActivationImpossible("Seul le chef de liste désigné pour ce périmètre peut retirer la prévision.")
    if liste.statut != ServiceGarde.STATUT_PUBLIEE or liste.application != ServiceGarde.APPLICATION_PREVISIONNELLE:
        raise ActivationImpossible("Seule une liste publiée à titre prévisionnel peut être retirée.")
    if not motif.strip():
        raise ActivationImpossible("Un motif est obligatoire pour retirer la prévision.")
    liste.statut = ServiceGarde.STATUT_BROUILLON
    liste.prise_effet_prevue = None
    liste.version_prevision += 1
    liste.save(update_fields=["statut", "prise_effet_prevue", "version_prevision", "updated_at"])
    fermer_alertes(liste, "prévision retirée")
    AuditLog.objects.create(
        actor=user, action="liste_service_previsionnelle_retiree",
        details=f"Service à quai #{liste.pk} ({liste.perimetre}) : prévision retirée, la liste redevient un brouillon. Motif : {motif.strip()}.",
    )
    if ship := navire_de_la_liste(liste):
        reevaluer_batiment(ship)
    return liste
