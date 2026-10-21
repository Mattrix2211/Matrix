"""Double équipage : l'équipage à terre consulte le bâtiment en lecture seule.

Ce module est le seul à lire ou écrire `Ship.equipage_a_bord` : tout le reste passe par `equipage_a_bord(navire)`,
qui applique d'abord les relèves planifiées dont la date d'effet est atteinte.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from accounts.models import AuditLog, Roles
from matrix.core.fuseau import fuseau_valide, formater, libelle_fuseau, minute_courante, nom_fuseau, MESSAGE_FUSEAU_INVALIDE
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level
from matrix.core.scopes import is_master_admin
from notifications.models import Notification

logger = logging.getLogger(__name__)

ACTIONS_RELEVE = (
    "proposer_releve", "decider_releve", "annuler_releve", "annuler_releve_planifiee", "valider_releve_secours",
    "generer_passation",
)
# Le commandant en second supplée le commandant de son équipage.
ROLES_COMMANDEMENT = (Roles.COMMANDANT, Roles.COMMANDANT_EN_SECOND)
MESSAGE_EQUIPAGE_OBLIGATOIRE = "L'équipage est obligatoire sur un bâtiment à double équipage."


def equipage_a_terre_lecture_seule(user):
    """Vrai si le marin appartient à l'équipage qui n'est pas à bord de son bâtiment à double équipage.

    Sans équipage renseigné, ou pour un bâtiment à équipage unique, aucune restriction.
    """
    profil = getattr(user, "profile", None)
    if profil is None or user.is_superuser:
        return False
    navire = profil.ship
    if navire is None or not navire.double_equipage or not profil.equipage:
        return False
    return profil.equipage != equipage_a_bord(navire)


def equipage_a_bord(navire):
    """Accesseur unique de l'équipage à bord : relit la base et applique d'abord les relèves planifiées échues.

    L'instance reçue est mise à jour ; une requête suffit quand rien n'est à appliquer.
    """
    from org.models import ReleveEquipage, Ship

    if navire is None or navire.pk is None:
        return navire.equipage_a_bord if navire is not None else ""
    echue = ReleveEquipage.objects.filter(
        ship=OuterRef("pk"), statut=ReleveEquipage.Statut.PLANIFIEE, date_effet__lte=timezone.now()
    )
    ligne = Ship.objects.filter(pk=navire.pk).annotate(echue=Exists(echue)).values_list("equipage_a_bord", "echue").first()
    if ligne is None:
        return navire.equipage_a_bord
    navire.equipage_a_bord = ligne[0]
    if ligne[1]:
        appliquer_releves_echues(navire)
    return navire.equipage_a_bord


def appliquer_releves_echues(navire=None):
    """Applique les relèves planifiées dont la date d'effet est atteinte (tous les bâtiments, ou celui donné).

    Idempotente et sûre en concurrence : le bâtiment est verrouillé, puis la relève relue sous verrou.
    Renvoie les relèves appliquées ; l'instance `navire` reçue est mise à jour.
    """
    from org.models import ReleveEquipage, Ship

    echues = ReleveEquipage.objects.filter(statut=ReleveEquipage.Statut.PLANIFIEE, date_effet__lte=timezone.now())
    if navire is not None:
        echues = echues.filter(ship_id=navire.pk)
    appliquees = []
    for ship_id in list(echues.values_list("ship_id", flat=True).order_by().distinct()):
        with transaction.atomic():
            verrouille = Ship.objects.select_for_update().get(pk=ship_id)
            releve = (
                ReleveEquipage.objects.select_for_update(of=("self",)).select_related("propose_par", "decide_par")
                .filter(ship=verrouille, statut=ReleveEquipage.Statut.PLANIFIEE, date_effet__lte=timezone.now())
                .first()
            )
            if releve is not None:
                sortant = verrouille.equipage_a_bord
                _appliquer(releve, verrouille, None)
                _notifier_application(releve, verrouille, sortant)
                appliquees.append(releve)
            if navire is not None and navire.pk == ship_id:
                navire.equipage_a_bord = verrouille.equipage_a_bord
    return appliquees


def equipage_a_bord_le(navire, instant):
    """Équipage à bord à l'instant donné, ou None s'il est inconnu (le passé n'est jamais reconstitué).

    Instant présent ou futur : équipage actuel, ou celui de la relève planifiée si sa date d'effet est atteinte.
    Instant passé : période enregistrée qui le couvre.
    """
    from org.models import PeriodeEquipage

    actuel = equipage_a_bord(navire)
    if instant >= minute_courante(timezone.now()):
        planifiee = releve_planifiee(navire)
        if planifiee and planifiee.date_effet <= instant:
            return planifiee.equipage_propose
        return actuel or None
    periode = PeriodeEquipage.objects.filter(ship=navire, debut__lte=instant).filter(
        Q(fin__isnull=True) | Q(fin__gt=instant)
    ).first()
    return periode.equipage if periode else None


def equipage_modifiable_par(acteur, cible):
    """Nul ne change son propre équipage (sauf l'administrateur général) : cela contournerait la lecture seule."""
    return is_master_admin(acteur) or acteur.pk != cible.pk


def commandants_equipage(navire, equipage):
    """Commandants et commandants en second actifs d'un équipage de l'unité."""
    return get_user_model().objects.filter(
        is_active=True, profile__ship=navire, profile__role__in=ROLES_COMMANDEMENT, profile__equipage=equipage
    )


def releve_en_attente(navire):
    from org.models import ReleveEquipage

    return ReleveEquipage.objects.filter(ship=navire, statut=ReleveEquipage.Statut.EN_ATTENTE).first()


def releve_planifiee(navire):
    from org.models import ReleveEquipage

    return ReleveEquipage.objects.filter(ship=navire, statut=ReleveEquipage.Statut.PLANIFIEE).first()


def _equipage_commandant(user, navire):
    """Équipage dont l'utilisateur est commandant (ou en second) sur cette unité, sinon chaîne vide (pas de contournement MASTER_ADMIN)."""
    profil = getattr(user, "profile", None)
    if profil and profil.role in ROLES_COMMANDEMENT and profil.ship_id == navire.pk:
        return profil.equipage
    return ""


def _horodatage(navire, instant):
    """Instant lisible dans le fuseau du bâtiment, avec son équivalent UTC pour le journal."""
    return f"{formater(navire, instant)} [{instant:%Y-%m-%dT%H:%MZ}]" if instant else "—"


def _verrouiller_navire(navire_id):
    """Verrou de ligne du bâtiment : toute modification d'équipage à bord le prend d'abord (puis la relève)."""
    from org.models import Ship

    return Ship.objects.select_for_update().get(pk=navire_id)


def proposer_releve(auteur, navire, equipage, date_effet):
    """Un commandant ou son second propose la relève avec sa date d'effet (UTC, pas dans le passé) ; renvoie (proposition, message d'erreur)."""
    from org.models import ReleveEquipage

    mon_equipage = _equipage_commandant(auteur, navire)
    if not mon_equipage:
        return None, "Seul un commandant ou un commandant en second de l'unité peut proposer la relève."
    if date_effet is None:
        return None, "Indiquez la date et l'heure d'effet de la relève."
    if date_effet < minute_courante(timezone.now()):
        return None, "La date d'effet d'une relève ne peut pas être dans le passé."
    try:
        with transaction.atomic():
            navire = _verrouiller_navire(navire.pk)
            a_bord = equipage_a_bord(navire)
            if not navire.double_equipage or not a_bord:
                return None, "Cette unité n'a pas de double équipage ou d'équipage à bord renseigné."
            if equipage == a_bord:
                return None, f"L'équipage {equipage} est déjà à bord."
            if mon_equipage not in (a_bord, equipage):
                return None, "Vous devez être commandant (ou en second) de l'équipage à bord ou de celui à embarquer."
            autre = equipage if mon_equipage == a_bord else a_bord
            if not commandants_equipage(navire, autre).exists():
                return None, f"Aucun commandant ni commandant en second n'est désigné pour l'équipage {autre} : la relève est impossible."
            if releve_en_attente(navire):
                return None, "Une relève est déjà en attente de validation."
            if releve_planifiee(navire):
                return None, "Une relève est déjà planifiée : annulez-la avant d'en proposer une autre."
            proposition = ReleveEquipage.objects.create(
                ship=navire, equipage_propose=equipage, propose_par=auteur, date_effet=date_effet
            )
            AuditLog.objects.create(
                actor=auteur, action="releve_proposee",
                details=f"navire={navire.name}; equipage_propose={equipage}; date_effet={_horodatage(navire, date_effet)}",
            )
            for cdt in commandants_equipage(navire, autre):
                Notification.objects.create(
                    user=cdt,
                    verb=(
                        f"Relève proposée sur {navire.name} : l'équipage {equipage} à bord à compter du "
                        f"{formater(navire, date_effet)}. Votre validation est attendue."
                    ),
                    url="/parametre/?tab=equipage",
                )
    except IntegrityError:
        return None, "Une relève est déjà ouverte sur cette unité."
    return proposition, ""


def decider_releve(auteur, proposition, accepter):
    """Le commandant (ou en second) de l'autre équipage valide ou refuse ; la validation applique la relève ou la planifie. Renvoie un message d'erreur ou ''."""
    navire = proposition.ship
    if proposition.statut != proposition.Statut.EN_ATTENTE:
        return "Cette relève n'est plus en attente."
    mon_equipage = _equipage_commandant(auteur, navire)
    if not mon_equipage:
        return "Seul un commandant ou un commandant en second de l'unité peut valider la relève."
    if auteur == proposition.propose_par:
        return "Vous ne pouvez pas valider votre propre proposition."
    proposeur = _equipage_commandant(proposition.propose_par, navire)
    if mon_equipage == proposeur or mon_equipage not in (equipage_a_bord(navire), proposition.equipage_propose):
        return "Seul le commandant (ou en second) de l'autre équipage peut valider cette relève."
    with transaction.atomic():
        proposition = _recharger_en_attente(proposition)
        if proposition is None:
            return "Cette relève n'est plus en attente."
        return _appliquer_decision(auteur, proposition, accepter, "releve_validee", f"decide_par={auteur}")


def _equipage_valideur(proposition):
    """Équipage chargé de valider : l'autre que celui du proposant ; chaîne vide si le proposant n'est plus commandant d'un des deux équipages."""
    navire = proposition.ship
    a_bord = equipage_a_bord(navire)
    proposeur = _equipage_commandant(proposition.propose_par, navire)
    if proposeur not in (a_bord, proposition.equipage_propose):
        return ""
    return proposition.equipage_propose if proposeur == a_bord else a_bord


def erreur_secours_releve(auteur, proposition):
    """Message d'erreur si la validation de secours n'est pas permise, sinon ''.

    Réservée à l'administrateur général, et seulement quand l'équipage valideur n'a ni commandant ni second.
    """
    if not is_master_admin(auteur):
        return "Seul l'administrateur général peut valider une relève en secours."
    if proposition.statut != proposition.Statut.EN_ATTENTE:
        return "Cette relève n'est plus en attente."
    if auteur == proposition.propose_par:
        return "Vous ne pouvez pas valider votre propre proposition."
    valideur = _equipage_valideur(proposition)
    if not valideur:
        return "La proposition ne vient plus d'un commandant de l'unité : la validation de secours est impossible."
    if commandants_equipage(proposition.ship, valideur).exists():
        return f"L'équipage {valideur} a un commandant ou un commandant en second : lui seul peut valider."
    return ""


def _recharger_en_attente(proposition):
    """Verrouille le bâtiment puis recharge la proposition ; None si elle n'est plus en attente (double validation)."""
    _verrouiller_navire(proposition.ship_id)
    verrouillee = type(proposition).objects.select_for_update(of=("self",)).select_related("ship", "propose_par").get(pk=proposition.pk)
    return verrouillee if verrouillee.statut == verrouillee.Statut.EN_ATTENTE else None


def valider_releve_secours(auteur, proposition, motif):
    """L'administrateur général valide à la place d'un équipage sans commandant ni second ; motif obligatoire. Renvoie un message d'erreur ou ''."""
    erreur = erreur_secours_releve(auteur, proposition)
    if erreur:
        return erreur
    motif = (motif or "").strip()
    if not motif:
        return "Le motif de la validation de secours est obligatoire."
    with transaction.atomic():
        proposition = _recharger_en_attente(proposition)
        if proposition is None:
            return "Cette relève n'est plus en attente."
        erreur = erreur_secours_releve(auteur, proposition)
        if erreur:
            return erreur
        navire = proposition.ship
        equipages = {proposition.equipage_propose, equipage_a_bord(navire)}
        _appliquer_decision(
            auteur, proposition, True, "releve_validee_secours",
            f"decide_par={auteur}; equipage_valideur={_equipage_valideur(proposition)}; motif={motif}",
            notifier_proposant=False,
        )
        # Les deux équipages sont prévenus, commandants et seconds compris.
        destinataires = get_user_model().objects.filter(
            is_active=True, profile__ship=navire, profile__equipage__in=equipages
        )
        if proposition.statut == proposition.Statut.PLANIFIEE:
            etat = f"l'équipage {proposition.equipage_propose} sera à bord à compter du {formater(navire, proposition.date_effet)}."
        else:
            etat = f"l'équipage {proposition.equipage_propose} est à bord."
        for marin in destinataires:
            Notification.objects.create(
                user=marin,
                verb=(
                    f"Relève sur {navire.name} : {etat} "
                    "Validation de secours par l'administrateur général (aucun commandant ni second disponible "
                    "pour valider), tracée dans le journal d'audit."
                ),
                url="/parametre/?tab=equipage",
            )
    return ""


def _appliquer_decision(auteur, proposition, accepter, action_validation, complement, notifier_proposant=True):
    """Enregistre la décision (bâtiment verrouillé) : refus, application immédiate si la date d'effet est atteinte, sinon planification."""
    navire = proposition.ship
    maintenant = timezone.now()
    proposition.decide_par = auteur
    proposition.decide_le = maintenant
    details = (
        f"navire={navire.name}; equipage_propose={proposition.equipage_propose}; "
        f"propose_par={proposition.propose_par}; date_effet={_horodatage(navire, proposition.date_effet)}; {complement}"
    )
    planifiee = bool(accepter and proposition.date_effet and proposition.date_effet > maintenant)
    if not accepter:
        proposition.statut = proposition.Statut.REFUSEE
        proposition.save()
        AuditLog.objects.create(actor=auteur, action="releve_refusee", details=details)
    elif planifiee:
        proposition.statut = proposition.Statut.PLANIFIEE
        proposition.save()
        AuditLog.objects.create(actor=auteur, action=action_validation, details=details)
    else:
        AuditLog.objects.create(actor=auteur, action=action_validation, details=details)
        _appliquer(proposition, navire, auteur)
    if notifier_proposant and proposition.propose_par:
        nom = auteur.get_full_name() or auteur.username
        if planifiee:
            verb = (
                f"Relève sur {navire.name} validée par {nom} : l'équipage {proposition.equipage_propose} sera à bord "
                f"à compter du {formater(navire, proposition.date_effet)}. Elle reste annulable jusqu'à cette date."
            )
        else:
            verb = f"Relève sur {navire.name} {'validée' if accepter else 'refusée'} par {nom}."
        Notification.objects.create(user=proposition.propose_par, verb=verb, url="/parametre/?tab=equipage")
    return ""


def _appliquer(releve, navire, auteur):
    """Change l'équipage à bord (bâtiment verrouillé par l'appelant) : période, trace et synthèse de passation.

    `auteur` est None quand la tâche planifiée applique la relève. Les horodatages réels sont ceux de l'application.
    """
    maintenant = timezone.now()
    sortant = navire.equipage_a_bord
    avant = (navire.double_equipage, sortant)
    effet = releve.date_effet or maintenant
    releve.date_effet = effet
    releve.statut = releve.Statut.VALIDEE
    releve.appliquee_le = maintenant
    releve.save()
    navire.equipage_a_bord = releve.equipage_propose
    navire.save(update_fields=["equipage_a_bord", "updated_at"])
    _enregistrer_periode(navire, releve, effet)
    AuditLog.objects.create(
        actor=auteur, action="releve_appliquee",
        details=(
            f"navire={navire.name}; equipage={releve.equipage_propose}; "
            f"date_effet_prevue={_horodatage(navire, effet)}; appliquee_le={_horodatage(navire, maintenant)}"
        ),
    )
    tracer_changement_equipage(auteur, navire, avant)
    from dashboard.passation import generer_passation

    redacteur = auteur or releve.decide_par or releve.propose_par
    # La relève reste appliquée même si la synthèse échoue ; le bouton manuel permet de la regénérer.
    try:
        with transaction.atomic():
            generer_passation(redacteur, navire, releve, sortant)
    except Exception:
        logger.exception("Synthèse de passation non générée (relève %s)", releve.pk)
        AuditLog.objects.create(
            actor=redacteur, action="passation_echec", details=f"navire={navire.name}; releve={releve.pk}"
        )


def _enregistrer_periode(navire, releve, debut):
    """Ferme la période ouverte à la date d'effet et ouvre celle du nouvel équipage (aucune reconstitution du passé)."""
    from org.models import PeriodeEquipage

    PeriodeEquipage.objects.filter(ship=navire, fin__isnull=True).update(fin=debut)
    PeriodeEquipage.objects.create(
        ship=navire, equipage=releve.equipage_propose, debut=debut, source=PeriodeEquipage.Source.RELEVE, releve=releve
    )


def _notifier_application(releve, navire, sortant):
    """Prévient les commandements des deux équipages à l'application réelle d'une relève planifiée."""
    destinataires = {
        u.pk: u
        for u in (
            *commandants_equipage(navire, sortant), *commandants_equipage(navire, releve.equipage_propose),
            releve.propose_par, releve.decide_par,
        )
        if u is not None
    }
    for utilisateur in destinataires.values():
        Notification.objects.create(
            user=utilisateur,
            verb=(
                f"Relève appliquée sur {navire.name} : l'équipage {releve.equipage_propose} est à bord "
                f"(prévue le {formater(navire, releve.date_effet)})."
            ),
            url="/parametre/?tab=equipage",
        )


def annuler_releve(auteur, proposition):
    """Seul l'auteur annule sa proposition en attente. Renvoie un message d'erreur ou ''."""
    if proposition.statut != proposition.Statut.EN_ATTENTE or auteur != proposition.propose_par:
        return "Seul l'auteur peut annuler sa proposition en attente."
    proposition.statut = proposition.Statut.ANNULEE
    proposition.save(update_fields=["statut", "updated_at"])
    AuditLog.objects.create(
        actor=auteur, action="releve_annulee", details=f"navire={proposition.ship.name}; equipage_propose={proposition.equipage_propose}"
    )
    return ""


def peut_annuler_releve_planifiee(user, releve):
    """Commandant (ou second) de l'un des deux équipages de la relève, sur son bâtiment."""
    mon_equipage = _equipage_commandant(user, releve.ship)
    return bool(mon_equipage) and mon_equipage in {releve.equipage_propose, equipage_a_bord(releve.ship)}


def annuler_releve_planifiee(auteur, releve, motif):
    """Un commandant (ou second) de l'un des deux équipages annule une relève planifiée ; justification obligatoire.

    Prévient immédiatement le commandement de l'autre équipage. Une relève déjà appliquée ne s'annule pas.
    Renvoie un message d'erreur ou ''.
    """
    navire = releve.ship
    mon_equipage = _equipage_commandant(auteur, navire)
    if not mon_equipage:
        return "Seul un commandant ou un commandant en second de l'unité peut annuler une relève planifiée."
    motif = (motif or "").strip()
    if not motif:
        return "La justification de l'annulation est obligatoire."
    appliquer_releves_echues(navire)
    with transaction.atomic():
        _verrouiller_navire(navire.pk)
        verrouillee = type(releve).objects.select_for_update(of=("self",)).select_related("ship").get(pk=releve.pk)
        if verrouillee.statut == verrouillee.Statut.VALIDEE:
            return "Cette relève est déjà appliquée : elle ne peut plus être annulée."
        if verrouillee.statut != verrouillee.Statut.PLANIFIEE:
            return "Cette relève n'est pas planifiée."
        navire = verrouillee.ship
        if not peut_annuler_releve_planifiee(auteur, verrouillee):
            return "Seul le commandant (ou en second) de l'un des deux équipages concernés peut annuler cette relève."
        verrouillee.statut = verrouillee.Statut.ANNULEE
        verrouillee.annulee_par = auteur
        verrouillee.annulee_le = timezone.now()
        verrouillee.motif_annulation = motif
        verrouillee.save()
        AuditLog.objects.create(
            actor=auteur, action="releve_planifiee_annulee",
            details=(
                f"navire={navire.name}; equipage_propose={verrouillee.equipage_propose}; "
                f"date_effet={_horodatage(navire, verrouillee.date_effet)}; motif={motif}"
            ),
        )
        autre = ({verrouillee.equipage_propose, navire.equipage_a_bord} - {mon_equipage}).pop()
        for cdt in commandants_equipage(navire, autre):
            Notification.objects.create(
                user=cdt,
                verb=(
                    f"Relève planifiée annulée sur {navire.name} par {auteur.get_full_name() or auteur.username} "
                    f"(équipage {mon_equipage}) : l'équipage {verrouillee.equipage_propose} ne sera pas à bord le "
                    f"{formater(navire, verrouillee.date_effet)}. Motif : {motif}"
                ),
                url="/parametre/?tab=equipage",
            )
    return ""


def peut_changer_fuseau(user, navire):
    """Même habilitation que l'administration de l'unité (seuil `unite_administration`), sur son propre bâtiment."""
    if is_master_admin(user):
        return True
    profil = getattr(user, "profile", None)
    if profil is None or profil.ship_id != navire.pk:
        return False
    return user_role_level(user) >= niveau_requis_pour(user, "unite_administration")


def changer_fuseau(auteur, navire, nom):
    """Fixe le fuseau de référence du bâtiment, tracé ; les instants enregistrés (UTC) ne sont jamais touchés. Renvoie un message d'erreur ou ''."""
    if not peut_changer_fuseau(auteur, navire):
        return "Changer le fuseau horaire du bâtiment est réservé à l'administration de l'unité."
    nom = (nom or "").strip()
    if not fuseau_valide(nom):
        return MESSAGE_FUSEAU_INVALIDE
    if nom == navire.fuseau_horaire:
        return ""
    avant = libelle_fuseau(navire)
    navire.fuseau_horaire = nom
    navire.save(update_fields=["fuseau_horaire", "updated_at"])
    AuditLog.objects.create(
        actor=auteur, action="fuseau_horaire_modifie",
        details=f"navire={navire.name}; avant={avant}; apres={nom_fuseau(navire)}; instants deja enregistres inchanges",
    )
    return ""


def tracer_changement_equipage(auteur, navire, avant):
    """Inscrit au journal toute modification du double équipage ; `avant` = (double_equipage, equipage_a_bord)."""
    apres = (navire.double_equipage, navire.equipage_a_bord)
    if avant != apres:
        AuditLog.objects.create(
            actor=auteur, action="changement_equipage",
            details=(
                f"navire={navire.name}; double_equipage={avant[0]} -> {apres[0]}; "
                f"equipage_a_bord={avant[1] or '—'} -> {apres[1] or '—'}"
            ),
        )


def equipage_manquant(navire, equipage):
    """Vrai si le bâtiment est à double équipage et que l'équipage du marin n'est pas renseigné."""
    return bool(navire and navire.double_equipage and not equipage)


def marins_sans_equipage(navire):
    """Marins d'un bâtiment à double équipage dont l'équipage n'est pas renseigné."""
    if not navire.double_equipage:
        return get_user_model().objects.none()
    return get_user_model().objects.filter(profile__ship=navire, profile__equipage="").order_by("last_name", "username")
