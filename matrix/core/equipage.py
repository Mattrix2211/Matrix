"""Double équipage : l'équipage à terre consulte le bâtiment en lecture seule."""
from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import AuditLog, Roles
from matrix.core.scopes import is_master_admin
from notifications.models import Notification

ACTIONS_RELEVE = ("proposer_releve", "decider_releve", "annuler_releve", "valider_releve_secours")
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
    return profil.equipage != navire.equipage_a_bord


def suivi_a_terre_sans_validation(user):
    """Responsable de classe ou de spécialité à terre : il consulte et commente, il ne valide pas."""
    from training.models import navire_de

    return not is_master_admin(user) and navire_de(user) is None


def equipage_modifiable_par(acteur, cible):
    """Nul ne change son propre équipage (sauf l'administrateur général) : cela contournerait la lecture seule."""
    return is_master_admin(acteur) or acteur.pk != cible.pk


def commandants_equipage(navire, equipage):
    """Commandants et commandants en second d'un équipage de l'unité."""
    return get_user_model().objects.filter(
        profile__ship=navire, profile__role__in=ROLES_COMMANDEMENT, profile__equipage=equipage
    )


def releve_en_attente(navire):
    from org.models import ReleveEquipage

    return ReleveEquipage.objects.filter(ship=navire, statut=ReleveEquipage.Statut.EN_ATTENTE).first()


def _equipage_commandant(user, navire):
    """Équipage dont l'utilisateur est commandant (ou en second) sur cette unité, sinon chaîne vide (pas de contournement MASTER_ADMIN)."""
    profil = getattr(user, "profile", None)
    if profil and profil.role in ROLES_COMMANDEMENT and profil.ship_id == navire.pk:
        return profil.equipage
    return ""


def proposer_releve(auteur, navire, equipage):
    """Un commandant ou son second propose la relève ; renvoie (proposition, message d'erreur)."""
    from org.models import ReleveEquipage

    mon_equipage = _equipage_commandant(auteur, navire)
    a_bord = navire.equipage_a_bord
    if not mon_equipage:
        return None, "Seul un commandant ou un commandant en second de l'unité peut proposer la relève."
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
    proposition = ReleveEquipage.objects.create(ship=navire, equipage_propose=equipage, propose_par=auteur)
    AuditLog.objects.create(
        actor=auteur, action="releve_proposee", details=f"navire={navire.name}; equipage_propose={equipage}"
    )
    for cdt in commandants_equipage(navire, autre):
        Notification.objects.create(
            user=cdt,
            verb=f"Relève proposée sur {navire.name} : l'équipage {equipage} à bord. Votre validation est attendue.",
        )
    return proposition, ""


def decider_releve(auteur, proposition, accepter):
    """Le commandant (ou en second) de l'autre équipage valide ou refuse ; la validation applique la relève. Renvoie un message d'erreur ou ''."""
    navire = proposition.ship
    if proposition.statut != proposition.Statut.EN_ATTENTE:
        return "Cette relève n'est plus en attente."
    mon_equipage = _equipage_commandant(auteur, navire)
    if not mon_equipage:
        return "Seul un commandant ou un commandant en second de l'unité peut valider la relève."
    if auteur == proposition.propose_par:
        return "Vous ne pouvez pas valider votre propre proposition."
    proposeur = _equipage_commandant(proposition.propose_par, navire)
    if mon_equipage == proposeur or mon_equipage not in (navire.equipage_a_bord, proposition.equipage_propose):
        return "Seul le commandant (ou en second) de l'autre équipage peut valider cette relève."
    return _appliquer_decision(auteur, proposition, accepter, "releve_validee", f"decide_par={auteur}")


def _equipage_valideur(proposition):
    """Équipage chargé de valider : l'autre que celui du proposant ; chaîne vide si le proposant n'est plus commandant."""
    navire = proposition.ship
    proposeur = _equipage_commandant(proposition.propose_par, navire)
    if not proposeur:
        return ""
    return proposition.equipage_propose if proposeur == navire.equipage_a_bord else navire.equipage_a_bord


def erreur_secours_releve(auteur, proposition):
    """Message d'erreur si la validation de secours n'est pas permise, sinon ''.

    Réservée à l'administrateur général, et seulement quand l'équipage valideur n'a ni commandant ni second.
    """
    if not is_master_admin(auteur):
        return "Seul l'administrateur général peut valider une relève en secours."
    if proposition.statut != proposition.Statut.EN_ATTENTE:
        return "Cette relève n'est plus en attente."
    valideur = _equipage_valideur(proposition)
    if not valideur:
        return "La proposition ne vient plus d'un commandant de l'unité : la validation de secours est impossible."
    if commandants_equipage(proposition.ship, valideur).exists():
        return f"L'équipage {valideur} a un commandant ou un commandant en second : lui seul peut valider."
    return ""


def valider_releve_secours(auteur, proposition, motif):
    """L'administrateur général valide à la place d'un équipage sans commandant ni second ; motif obligatoire. Renvoie un message d'erreur ou ''."""
    erreur = erreur_secours_releve(auteur, proposition)
    if erreur:
        return erreur
    motif = (motif or "").strip()
    if not motif:
        return "Le motif de la validation de secours est obligatoire."
    navire = proposition.ship
    equipages = {proposition.equipage_propose, navire.equipage_a_bord}
    _appliquer_decision(
        auteur, proposition, True, "releve_validee_secours",
        f"decide_par={auteur}; equipage_valideur={_equipage_valideur(proposition)}; motif={motif}",
        notifier_proposant=False,
    )
    destinataires = get_user_model().objects.filter(profile__ship=navire, profile__equipage__in=equipages)
    for marin in destinataires:
        Notification.objects.create(
            user=marin,
            verb=f"Relève sur {navire.name} validée en secours par l'administrateur général (aucun commandant disponible).",
        )
    return ""


def _appliquer_decision(auteur, proposition, accepter, action_validation, complement, notifier_proposant=True):
    """Enregistre la décision, applique la relève si validée, trace et notifie le proposant (sauf si la validation de secours s'en charge)."""
    navire = proposition.ship
    proposition.decide_par = auteur
    proposition.decide_le = timezone.now()
    details = (
        f"navire={navire.name}; equipage_propose={proposition.equipage_propose}; "
        f"propose_par={proposition.propose_par}; {complement}"
    )
    if accepter:
        avant = (navire.double_equipage, navire.equipage_a_bord)
        proposition.statut = proposition.Statut.VALIDEE
        navire.equipage_a_bord = proposition.equipage_propose
        navire.save(update_fields=["equipage_a_bord", "updated_at"])
        AuditLog.objects.create(actor=auteur, action=action_validation, details=details)
        tracer_changement_equipage(auteur, navire, avant)
    else:
        proposition.statut = proposition.Statut.REFUSEE
        AuditLog.objects.create(actor=auteur, action="releve_refusee", details=details)
    proposition.save()
    if notifier_proposant and proposition.propose_par:
        Notification.objects.create(
            user=proposition.propose_par,
            verb=f"Relève sur {navire.name} {'validée' if accepter else 'refusée'} par {auteur.get_full_name() or auteur.username}.",
        )
    return ""


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
