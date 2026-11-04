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
from org.models import Ship
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


def mode_du_batiment(ship, instant=None):
    """Mode (« MER » ou « QUAI ») du bâtiment à un instant, déduit du dernier mouvement valide survenu avant lui ;
    None si la situation n'a jamais été renseignée à cette date. Seule source du mode, jamais un champ libre."""
    instant = instant or timezone.now()
    dernier = mouvements_valides(ship).filter(survenu_le__lte=instant).last()
    return dernier.mode_apres if dernier and dernier.mode_apres else None


def intervalles_par_mode(ship, debut, fin):
    """Découpe [debut, fin) en intervalles (début, fin, mode) ; mode None quand il n'est pas connu."""
    mode = mode_du_batiment(ship, debut)
    bornes = [(debut, mode)]
    for mouvement in mouvements_valides(ship).filter(survenu_le__gt=debut, survenu_le__lt=fin):
        bornes.append((mouvement.survenu_le, mouvement.mode_apres or None))
    bornes.append((fin, None))
    return [(bornes[i][0], bornes[i + 1][0], bornes[i][1]) for i in range(len(bornes) - 1) if bornes[i][0] < bornes[i + 1][0]]


def _controler_chronologie(ship, type_, mode_apres, survenu_le, ignorer=None):
    """Deux mouvements valides consécutifs ne mènent jamais au même mode ; un mode ne s'initialise que
    avant tout autre mouvement."""
    if survenu_le > timezone.now():
        raise MouvementImpossible("La date effective ne peut pas être dans le futur.")
    lignes = [m for m in mouvements_valides(ship) if not ignorer or m.pk != ignorer.pk]
    avant = [m for m in lignes if m.survenu_le <= survenu_le]
    apres = [m for m in lignes if m.survenu_le > survenu_le]
    if type_ == MouvementBatiment.TYPE_INITIALISATION and avant:
        raise MouvementImpossible("Le mode est déjà renseigné à cette date : déclarez un accostage ou un appareillage.")
    if avant and avant[-1].mode_apres == mode_apres:
        raise MouvementImpossible(f"Incohérent : le bâtiment est déjà {dict(MouvementBatiment.MODE_CHOICES)[mode_apres].lower()} à cette date.")
    if apres and apres[0].mode_apres == mode_apres:
        raise MouvementImpossible(f"Incohérent : le mouvement suivant mène déjà au mode « {dict(MouvementBatiment.MODE_CHOICES)[mode_apres].lower()} ».")


def _recalculer_modes_avant(ship, acteur):
    """Remet « mode avant » en cohérence avec la chronologie après une correction ; les changements sont tracés."""
    precedent, modifies = "", []
    for mouvement in mouvements_valides(ship):
        if mouvement.mode_avant != precedent:
            modifies.append(f"{mouvement.get_type_display()} du {timezone.localtime(mouvement.survenu_le):%d/%m/%Y %H:%M}")
            mouvement.mode_avant = precedent
            mouvement.save(update_fields=["mode_avant", "updated_at"])
        precedent = mouvement.mode_apres
    if modifies:
        AuditLog.objects.create(
            actor=acteur, action="mouvement_batiment_chronologie_recalculee",
            details=f"Chronologie de {ship} recalculée après correction : « mode avant » mis à jour pour " + " ; ".join(modifies) + ".",
        )


def _creer(user, ship, type_, survenu_le, remplace=None, mode=None, motif=""):
    fonction = fonction_habilitee(user, ship)
    if fonction is None:
        raise MouvementImpossible("Seul le COMAEQ ou le commandant peut déclarer un mouvement du bâtiment.")
    mode_apres = mode or MouvementBatiment.MODE_PAR_TYPE.get(type_)
    if mode_apres not in dict(MouvementBatiment.MODE_CHOICES):
        raise MouvementImpossible("Le mode demandé est invalide.")
    if type_ == MouvementBatiment.TYPE_INITIALISATION and not motif.strip():
        raise MouvementImpossible("Un motif est obligatoire pour initialiser le mode.")
    _controler_chronologie(ship, type_, mode_apres, survenu_le)
    mouvement = MouvementBatiment.objects.create(
        ship=ship, type=type_, survenu_le=survenu_le, declare_par=user, fonction_declarante=fonction, remplace=remplace,
        mode_avant=mode_du_batiment(ship, survenu_le) or "", mode_apres=mode_apres, motif=motif.strip(),
    )
    AuditLog.objects.create(
        actor=user, action="mouvement_batiment_declare",
        details=(
            f"{mouvement.get_type_display()} de {ship} le {timezone.localtime(survenu_le):%d/%m/%Y à %H:%M}, "
            f"déclaré en qualité de {fonction} : mode {mouvement.mode_avant or 'non renseigné'} → {mouvement.mode_apres}."
            + (f" Motif : {mouvement.motif}." if mouvement.motif else "")
        ),
    )
    return mouvement


@transaction.atomic
def declarer_mouvement(user, ship, type_, survenu_le):
    if type_ not in MouvementBatiment.MODE_PAR_TYPE:
        raise MouvementImpossible("Type de mouvement inconnu.")
    mouvement = _creer(user, ship, type_, survenu_le)
    _recalculer_modes_avant(ship, user)
    reevaluer_batiment(ship)
    return mouvement


@transaction.atomic
def initialiser_mode(user, ship, mode, survenu_le, motif):
    """Déclare explicitement le mode de départ d'un bâtiment (jamais déduit d'une liste publiée)."""
    mouvement = _creer(user, ship, MouvementBatiment.TYPE_INITIALISATION, survenu_le, mode=mode, motif=motif)
    _recalculer_modes_avant(ship, user)
    return mouvement


@transaction.atomic
def annuler_mouvement(user, mouvement, motif, nouveau_survenu_le=None):
    """Annule une déclaration (motif obligatoire) et, pour la corriger, la remplace par une nouvelle date.
    La chronologie et les alertes sont recalculées ; aucune affectation passée n'est modifiée."""
    mouvement = MouvementBatiment.objects.select_for_update().get(pk=mouvement.pk)
    if fonction_habilitee(user, mouvement.ship) is None:
        raise MouvementImpossible("Seul le COMAEQ ou le commandant peut annuler ou corriger un mouvement du bâtiment.")
    if mouvement.statut != MouvementBatiment.STATUT_VALIDE:
        raise MouvementImpossible("Cette déclaration est déjà annulée.")
    if not motif.strip():
        raise MouvementImpossible("Un motif est obligatoire pour annuler ou corriger une déclaration.")
    if nouveau_survenu_le is not None:
        _controler_chronologie(mouvement.ship, mouvement.type, mouvement.mode_apres, nouveau_survenu_le, ignorer=mouvement)
    else:
        autres = [m for m in mouvements_valides(mouvement.ship) if m.pk != mouvement.pk]
        precedents = [m for m in autres if m.survenu_le <= mouvement.survenu_le]
        suivants = [m for m in autres if m.survenu_le > mouvement.survenu_le]
        if precedents and suivants and precedents[-1].mode_apres == suivants[0].mode_apres:
            raise MouvementImpossible("Annulation incohérente : elle laisserait deux mouvements menant au même mode.")
    mouvement.statut = MouvementBatiment.STATUT_ANNULE
    mouvement.annule_par, mouvement.annule_le, mouvement.motif_annulation = user, timezone.now(), motif.strip()
    mouvement.save(update_fields=["statut", "annule_par", "annule_le", "motif_annulation", "updated_at"])
    mouvement.alertes.filter(fermee_le__isnull=True).update(fermee_le=timezone.now(), motif_fermeture="déclaration annulée ou corrigée")
    AuditLog.objects.create(
        actor=user, action="mouvement_batiment_annule",
        details=f"{mouvement.get_type_display()} de {mouvement.ship} du {timezone.localtime(mouvement.survenu_le):%d/%m/%Y %H:%M} annulé(e). Motif : {motif.strip()}.",
    )
    nouveau = (
        _creer(user, mouvement.ship, mouvement.type, nouveau_survenu_le, remplace=mouvement, mode=mouvement.mode_apres, motif=mouvement.motif)
        if nouveau_survenu_le else None
    )
    _recalculer_modes_avant(mouvement.ship, user)
    reevaluer_batiment(mouvement.ship)
    return nouveau


# Valeurs fictives du jeu de démonstration uniquement : aucune affirmation sur la situation réelle de ces bâtiments.
MODES_DE_DEMONSTRATION = {"Bretagne": "QUAI", "Jacques Chevallier": "MER", "Auguste Bénébig": "QUAI"}


def initialiser_modes_de_demonstration(instant):
    """Initialise, de façon explicite et tracée, le mode des bâtiments de démonstration présents en base
    (déclaré par leur commandant) ; ceux déjà renseignés ou sans commandant habilité sont laissés tels quels."""
    comptes_rendus = []
    for nom, mode in MODES_DE_DEMONSTRATION.items():
        ship = Ship.objects.filter(name=nom).first()
        if ship is None:
            comptes_rendus.append(f"{nom} : absent de la base, ignoré.")
        elif mode_du_batiment(ship) is not None:
            comptes_rendus.append(f"{nom} : mode déjà renseigné, inchangé.")
        else:
            auteur = next((u for u in User.objects.filter(profile__ship=ship, is_active=True) if fonction_habilitee(u, ship)), None)
            if auteur is None:
                comptes_rendus.append(f"{nom} : aucun commandant ou COMAEQ habilité, mode non initialisé.")
                continue
            initialiser_mode(auteur, ship, mode, instant, "Situation fictive de démonstration validée par le PO")
            comptes_rendus.append(f"{nom} : mode {mode} initialisé (démonstration).")
    return comptes_rendus


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
