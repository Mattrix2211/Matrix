"""Accostage et appareillage du bâtiment : déclaration, correction motivée et alerte « accostage sans liste applicable »."""
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.commandants_adjoints import titulaires_commandant_adjoint
from matrix.core.equipage import equipage_a_bord
from notifications.models import Notification, NotificationLevel
from quarts.models import (
    AlerteAccostage,
    ChefDeListe,
    MouvementBatiment,
    ServiceGarde,
    _commandant_de_l_equipage,
    commandants_en_second,
)


class MouvementImpossible(Exception):
    """Refus métier, message affichable tel quel."""


def fonction_habilitee(user, ship):
    """« COMAEQ » ou « COMMANDANT » si l'agent peut déclarer un mouvement du bâtiment, sinon None."""
    equipage = equipage_a_bord(ship)
    if titulaires_commandant_adjoint(ship, "COMAEQ", equipage).filter(pk=user.pk).exists():
        return "COMAEQ"
    if _commandant_de_l_equipage(user, ship, equipage):
        return "COMMANDANT"
    return None


def mouvements_valides(ship):
    return MouvementBatiment.objects.filter(ship=ship, statut=MouvementBatiment.STATUT_VALIDE).order_by("survenu_le", "pk")


def regime_du_batiment(ship):
    """« QUAI » après un accostage, « MER » après un appareillage, None si aucun mouvement."""
    dernier = mouvements_valides(ship).last()
    if dernier is None:
        return None
    return "QUAI" if dernier.type == MouvementBatiment.TYPE_ACCOSTAGE else "MER"


def _controler_chronologie(ship, type_, survenu_le, ignorer=None):
    """Les mouvements valides alternent : jamais deux accostages (ou appareillages) consécutifs."""
    if survenu_le > timezone.now():
        raise MouvementImpossible("La date effective ne peut pas être dans le futur.")
    lignes = [m for m in mouvements_valides(ship) if not ignorer or m.pk != ignorer.pk]
    avant = [m for m in lignes if m.survenu_le <= survenu_le]
    apres = [m for m in lignes if m.survenu_le > survenu_le]
    if avant and avant[-1].type == type_:
        raise MouvementImpossible(f"Incohérent : le dernier mouvement avant cette date est déjà un(e) {avant[-1].get_type_display().lower()}.")
    if apres and apres[0].type == type_:
        raise MouvementImpossible(f"Incohérent : le mouvement suivant est déjà un(e) {apres[0].get_type_display().lower()}.")


def _creer(user, ship, type_, survenu_le, remplace=None):
    fonction = fonction_habilitee(user, ship)
    if fonction is None:
        raise MouvementImpossible("Seul le COMAEQ ou le commandant peut déclarer un mouvement du bâtiment.")
    _controler_chronologie(ship, type_, survenu_le)
    mouvement = MouvementBatiment.objects.create(
        ship=ship, type=type_, survenu_le=survenu_le, declare_par=user, fonction_declarante=fonction, remplace=remplace,
    )
    AuditLog.objects.create(
        actor=user, action="mouvement_batiment_declare",
        details=f"{mouvement.get_type_display()} de {ship} le {timezone.localtime(survenu_le):%d/%m/%Y à %H:%M}, déclaré en qualité de {fonction}.",
    )
    return mouvement


@transaction.atomic
def declarer_mouvement(user, ship, type_, survenu_le):
    mouvement = _creer(user, ship, type_, survenu_le)
    reevaluer_batiment(ship)
    return mouvement


@transaction.atomic
def annuler_mouvement(user, mouvement, motif, nouveau_survenu_le=None):
    """Annule une déclaration (motif obligatoire) et, pour la corriger, la remplace par une nouvelle date."""
    mouvement = MouvementBatiment.objects.select_for_update().get(pk=mouvement.pk)
    if fonction_habilitee(user, mouvement.ship) is None:
        raise MouvementImpossible("Seul le COMAEQ ou le commandant peut annuler ou corriger un mouvement du bâtiment.")
    if mouvement.statut != MouvementBatiment.STATUT_VALIDE:
        raise MouvementImpossible("Cette déclaration est déjà annulée.")
    if not motif.strip():
        raise MouvementImpossible("Un motif est obligatoire pour annuler ou corriger une déclaration.")
    if nouveau_survenu_le is not None:
        _controler_chronologie(mouvement.ship, mouvement.type, nouveau_survenu_le, ignorer=mouvement)
    else:
        suivants = [m for m in mouvements_valides(mouvement.ship) if m.survenu_le > mouvement.survenu_le]
        precedents = [m for m in mouvements_valides(mouvement.ship) if m.survenu_le < mouvement.survenu_le]
        if precedents and suivants and precedents[-1].type == suivants[0].type:
            raise MouvementImpossible("Annulation incohérente : elle laisserait deux mouvements identiques consécutifs.")
    mouvement.statut = MouvementBatiment.STATUT_ANNULE
    mouvement.annule_par, mouvement.annule_le, mouvement.motif_annulation = user, timezone.now(), motif.strip()
    mouvement.save(update_fields=["statut", "annule_par", "annule_le", "motif_annulation", "updated_at"])
    mouvement.alertes.filter(fermee_le__isnull=True).update(fermee_le=timezone.now(), motif_fermeture="déclaration annulée ou corrigée")
    AuditLog.objects.create(
        actor=user, action="mouvement_batiment_annule",
        details=f"{mouvement.get_type_display()} de {mouvement.ship} du {timezone.localtime(mouvement.survenu_le):%d/%m/%Y %H:%M} annulé(e). Motif : {motif.strip()}.",
    )
    nouveau = _creer(user, mouvement.ship, mouvement.type, nouveau_survenu_le, remplace=mouvement) if nouveau_survenu_le else None
    reevaluer_batiment(mouvement.ship)
    return nouveau


def _listes_du_batiment(ship):
    q = Q(ship=ship) | Q(service__ship=ship) | Q(sector__service__ship=ship) | Q(section__sector__service__ship=ship)
    jour = timezone.localdate()
    qs = ServiceGarde.objects.filter(q, statut=ServiceGarde.STATUT_PUBLIEE, date_debut__lte=jour, date_fin__gte=jour)
    equipage = equipage_a_bord(ship) if ship.double_equipage else ""
    return qs.filter(Q(equipage=equipage) | Q(equipage="")) if equipage else qs


def _destinataires(ship, listes):
    equipage = equipage_a_bord(ship)
    par_id = {u.pk: u for u in titulaires_commandant_adjoint(ship, "COMAEQ", equipage)}
    if not par_id:  # COMAEQ vacant : le commandant en second reçoit l'alerte pour supervision
        par_id = {u.pk: u for u in commandants_en_second(ship, equipage)}
    from quarts.alertes_activation import chefs_de_liste_habilites

    for liste in listes:
        par_id.update({u.pk: u for u in chefs_de_liste_habilites(liste)})
    if not listes:
        cibles = ChefDeListe.objects.filter(
            Q(ship=ship) | Q(service__ship=ship) | Q(sector__service__ship=ship) | Q(section__sector__service__ship=ship),
            type_liste__in=("", ChefDeListe.TYPE_QUAI),
        ).values_list("user_id", flat=True)
        par_id.update({u.pk: u for u in User.objects.filter(pk__in=cibles, is_active=True)})
    return list(par_id.values())


def reevaluer_batiment(ship):
    """Si le bâtiment est à quai, vérifie qu'une liste est en vigueur ; sinon ouvre (ou met à jour) l'alerte
    adaptée. Idempotent : à rappeler après toute activation, publication, retrait ou correction de mouvement."""
    dernier = mouvements_valides(ship).last()
    if dernier is None or dernier.type != MouvementBatiment.TYPE_ACCOSTAGE:
        return None
    listes = list(_listes_du_batiment(ship))
    if any(l.application == ServiceGarde.APPLICATION_ACTIVE for l in listes):
        dernier.alertes.filter(fermee_le__isnull=True).update(fermee_le=timezone.now(), motif_fermeture="liste en vigueur")
        return None
    previsionnelles = [l for l in listes if l.application == ServiceGarde.APPLICATION_PREVISIONNELLE]
    genre = AlerteAccostage.GENRE_PREVISIONNELLE if previsionnelles else AlerteAccostage.GENRE_AUCUNE
    with transaction.atomic():
        dernier = MouvementBatiment.objects.select_for_update().get(pk=dernier.pk)
        dernier.alertes.filter(fermee_le__isnull=True).exclude(genre=genre).update(
            fermee_le=timezone.now(), motif_fermeture="situation modifiée"
        )
        if dernier.alertes.filter(fermee_le__isnull=True, genre=genre).exists():
            return None
        alerte = AlerteAccostage.objects.create(mouvement=dernier, genre=genre)
    texte = (
        f"Accostage de {ship} confirmé : la liste prévisionnelle n'est pas encore activée. Le chef de liste doit l'activer."
        if previsionnelles else f"Accostage de {ship} confirmé : aucune liste de service à quai n'est préparée."
    )
    for user in _destinataires(ship, previsionnelles or listes):
        Notification.objects.create(user=user, verb=texte, level=NotificationLevel.WARNING, url=reverse("quarts-index"))
    return alerte
