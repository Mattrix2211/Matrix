"""Workflow d'échange de tours de service de garde (Phase 2, VISION §7.4) :
A demande → B accepte/refuse → le chef de liste valide en dernier → les deux
affectations sont permutées. Chaque étape est tracée (EchangeServiceEvenement
+ AuditLog) et notifie les personnes concernées.

Le calendrier personnel n'a rien à mettre à jour lui-même : il lit directement
CreneauServiceGarde.marin (calendar_app/views.py), donc la permutation des deux
créneaux suffit à le refléter pour A comme pour B.

Périmètre : échanges entre deux créneaux d'UNE MÊME liste de gardes (même chef
de liste, mêmes habilitations) — hypothèse de cadrage, non étendue aux quarts.
Les absences ne sont pas modélisées dans Matrix à ce jour : la détection couvre
donc les conflits d'affectation (autre garde ou quart au même moment) et les
habilitations manquantes ; un modèle d'absence pourra s'y brancher plus tard
dans `analyser_echange`."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from notifications.models import Notification, NotificationLevel
from training.models import TrainingRecord

from .models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    EchangeService,
    EchangeServiceEvenement,
    perimetre_correspond,
    peut_gerer_liste,
)


class EchangeImpossible(Exception):
    """Levée quand une action est refusée ; `problemes` explique pourquoi,
    en français, à l'utilisateur."""

    def __init__(self, problemes):
        self.problemes = [problemes] if isinstance(problemes, str) else list(problemes)
        super().__init__(" ".join(self.problemes))


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def _libelle_creneau(creneau):
    return f"« {creneau.poste} » du {timezone.localtime(creneau.debut):%d/%m/%Y %H:%M}"


def _conflits_marin(marin, creneau, ignorer_ids):
    """Autres gardes ou quarts publiés de `marin` chevauchant `creneau`."""
    filtres = dict(marin=marin, debut__lt=creneau.fin, fin__gt=creneau.debut)
    gardes = CreneauServiceGarde.objects.filter(
        service_garde__statut="PUBLIEE", **filtres
    ).exclude(pk__in=ignorer_ids)
    quarts = CreneauQuart.objects.filter(quart__statut="PUBLIEE", **filtres)
    return list(gardes) + list(quarts)


def _habilitations_manquantes(marin, creneau):
    jour = timezone.localtime(creneau.debut).date()
    manquantes = []
    for formation in creneau.service_garde.formations_requises.all():
        valide = TrainingRecord.objects.filter(
            user=marin, course=formation, completed_at__lte=jour, expires_at__gte=jour
        ).exists()
        if not valide:
            manquantes.append(formation.title)
    return manquantes


def analyser_echange(echange, verifier_delai=False):
    """Liste des raisons, expliquées en français, pour lesquelles l'échange
    est impossible (liste vide = faisable)."""
    a, b = echange.creneau_demandeur, echange.creneau_cible
    if a is None or b is None:
        return ["Un des deux créneaux n'existe plus : l'échange n'a plus d'objet."]
    problemes = []
    if a.service_garde_id != b.service_garde_id:
        problemes.append("Les deux tours doivent appartenir à la même liste de services.")
    if a.service_garde.statut != "PUBLIEE":
        problemes.append("La liste n'est pas publiée : les tours ne sont pas encore définitifs.")
    if a.marin_id != echange.demandeur_id:
        problemes.append(
            f"Le tour {_libelle_creneau(a)} n'est plus affecté à {_nom(echange.demandeur)} : "
            "la situation a changé depuis la demande."
        )
    if b.marin_id != echange.cible_id:
        problemes.append(
            f"Le tour {_libelle_creneau(b)} n'est plus affecté à {_nom(echange.cible)} : "
            "la situation a changé depuis la demande."
        )
    if problemes:
        return problemes

    maintenant = timezone.now()
    for creneau in (a, b):
        if creneau.debut <= maintenant:
            problemes.append(f"Le tour {_libelle_creneau(creneau)} a déjà commencé : il ne peut plus être échangé.")
    delai = a.service_garde.delai_minimal_echange_heures
    if verifier_delai and delai:
        limite = maintenant + timezone.timedelta(hours=delai)
        for creneau in (a, b):
            if maintenant < creneau.debut < limite:
                problemes.append(
                    f"Le tour {_libelle_creneau(creneau)} est trop proche : cette liste exige "
                    f"un échange demandé au moins {delai} h à l'avance."
                )

    ignorer = [a.pk, b.pk]
    for marin, prend in ((echange.cible, a), (echange.demandeur, b)):
        for conflit in _conflits_marin(marin, prend, ignorer):
            problemes.append(
                f"Conflit d'affectation : {_nom(marin)} serait déjà affecté(e) à "
                f"{_libelle_creneau(conflit)} au moment du tour {_libelle_creneau(prend)}."
            )
        manquantes = _habilitations_manquantes(marin, prend)
        if manquantes:
            problemes.append(
                f"Habilitation manquante : {_nom(marin)} n'a pas de validation en cours pour "
                f"« {' », « '.join(manquantes)} » le jour du tour {_libelle_creneau(prend)}."
            )
    return problemes


def chefs_de_liste_a_notifier(liste):
    """Chefs de liste désignés pour le périmètre exact de la liste ; à défaut,
    le créateur de la liste (pour que la demande ne reste jamais sans validateur)."""
    chefs = [
        cdl.user for cdl in ChefDeListe.objects.filter(user__is_active=True).select_related("user")
        if perimetre_correspond(cdl, liste)
    ]
    if not chefs and liste.created_by_id:
        chefs = [liste.created_by]
    return chefs


def _tracer(echange, acteur, action, detail=""):
    EchangeServiceEvenement.objects.create(echange=echange, acteur=acteur, action=action, detail=detail)
    AuditLog.objects.create(
        actor=acteur, action=f"echange_service_{action}", target_user=echange.cible,
        details=f"echange={echange.pk}; {detail}",
    )


def _notifier(users, verb, echange, level=NotificationLevel.INFO):
    for user in {u.pk: u for u in users if u}.values():
        Notification.objects.create(user=user, verb=verb, level=level, target=echange)


def _resume(echange):
    return f"{echange.libelle_creneau_demandeur} contre {echange.libelle_creneau_cible}"


def peut_valider_echange(user, echange):
    return echange.liste is not None and peut_gerer_liste(user, echange.liste)


def _echanges_en_cours_des_creneaux(*creneaux):
    return EchangeService.objects.filter(statut__in=EchangeService.STATUTS_EN_COURS).filter(
        Q(creneau_demandeur__in=creneaux) | Q(creneau_cible__in=creneaux)
    )


@transaction.atomic
def proposer_echange(demandeur, creneau_demandeur, creneau_cible, motif=""):
    if creneau_demandeur.marin_id != demandeur.pk:
        raise EchangeImpossible("Vous ne pouvez proposer que l'échange d'un tour qui vous est affecté.")
    if creneau_cible.marin_id is None or creneau_cible.marin_id == demandeur.pk:
        raise EchangeImpossible("Choisissez le tour d'un autre marin.")
    if _echanges_en_cours_des_creneaux(creneau_demandeur, creneau_cible).exists():
        raise EchangeImpossible("Un de ces deux tours fait déjà l'objet d'une demande d'échange en cours.")
    echange = EchangeService(
        creneau_demandeur=creneau_demandeur, creneau_cible=creneau_cible,
        libelle_creneau_demandeur=_libelle_creneau(creneau_demandeur),
        libelle_creneau_cible=_libelle_creneau(creneau_cible),
        demandeur=demandeur, cible=creneau_cible.marin, motif=motif.strip(),
    )
    problemes = analyser_echange(echange, verifier_delai=True)
    if problemes:
        raise EchangeImpossible(problemes)
    echange.save()
    _tracer(echange, demandeur, "demande", _resume(echange))
    _notifier(
        [echange.cible],
        f"{_nom(demandeur)} vous propose un échange de service : {_resume(echange)}. "
        "Répondez depuis « Mes échanges ».",
        echange, NotificationLevel.WARNING,
    )
    return echange


def _echange_en_attente(echange, statut):
    echange.refresh_from_db()
    if echange.statut != statut:
        raise EchangeImpossible("Cette demande a déjà été traitée ou annulée.")


@transaction.atomic
def accepter_echange(echange, user):
    _echange_en_attente(echange, EchangeService.STATUT_DEMANDE)
    if user.pk != echange.cible_id:
        raise EchangeImpossible("Seul le marin sollicité peut répondre à cette demande.")
    problemes = analyser_echange(echange)
    if problemes:
        raise EchangeImpossible(problemes)
    echange.statut = EchangeService.STATUT_ACCEPTE
    echange.accepte_le = timezone.now()
    echange.save(update_fields=["statut", "accepte_le", "updated_at"])
    _tracer(echange, user, "acceptation")
    _notifier(
        [echange.demandeur],
        f"{_nom(user)} a accepté l'échange ({_resume(echange)}) : en attente du chef de liste.",
        echange,
    )
    _notifier(
        chefs_de_liste_a_notifier(echange.liste),
        f"Échange à valider : {_nom(echange.demandeur)} et {_nom(echange.cible)} — {_resume(echange)}.",
        echange, NotificationLevel.WARNING,
    )


def _cloturer(echange, user, statut, action, motif, notifies, message):
    echange.statut = statut
    echange.decide_le = timezone.now()
    echange.decide_par = user
    echange.motif_decision = motif.strip()
    echange.save(update_fields=["statut", "decide_le", "decide_par", "motif_decision", "updated_at"])
    _tracer(echange, user, action, echange.motif_decision)
    suffixe = f" Motif : {echange.motif_decision}" if echange.motif_decision else ""
    _notifier(notifies, message + suffixe, echange)


@transaction.atomic
def refuser_echange(echange, user, motif=""):
    _echange_en_attente(echange, EchangeService.STATUT_DEMANDE)
    if user.pk != echange.cible_id:
        raise EchangeImpossible("Seul le marin sollicité peut répondre à cette demande.")
    _cloturer(
        echange, user, EchangeService.STATUT_REFUSE, "refus_marin", motif, [echange.demandeur],
        f"{_nom(user)} a refusé l'échange ({_resume(echange)}).",
    )


@transaction.atomic
def annuler_echange(echange, user, motif=""):
    echange.refresh_from_db()
    if not echange.en_cours:
        raise EchangeImpossible("Cette demande a déjà été traitée ou annulée.")
    if user.pk != echange.demandeur_id:
        raise EchangeImpossible("Seul le marin à l'origine de la demande peut l'annuler.")
    notifies = [echange.cible]
    if echange.statut == EchangeService.STATUT_ACCEPTE:
        notifies += chefs_de_liste_a_notifier(echange.liste)
    _cloturer(
        echange, user, EchangeService.STATUT_ANNULE, "annulation", motif, notifies,
        f"{_nom(user)} a annulé la demande d'échange ({_resume(echange)}).",
    )


@transaction.atomic
def rejeter_echange(echange, user, motif=""):
    _echange_en_attente(echange, EchangeService.STATUT_ACCEPTE)
    if not peut_valider_echange(user, echange):
        raise EchangeImpossible("Seul le chef de la liste concernée peut trancher cet échange.")
    _cloturer(
        echange, user, EchangeService.STATUT_REJETE, "refus_chef", motif,
        [echange.demandeur, echange.cible],
        f"Le chef de liste a refusé l'échange ({_resume(echange)}) : les tours restent inchangés.",
    )


@transaction.atomic
def valider_echange(echange, user):
    """Dernière étape : les conditions sont revérifiées (la situation a pu
    changer depuis l'accord), puis les deux marins sont permutés."""
    _echange_en_attente(echange, EchangeService.STATUT_ACCEPTE)
    if not peut_valider_echange(user, echange):
        raise EchangeImpossible("Seul le chef de la liste concernée peut valider cet échange.")
    problemes = analyser_echange(echange)
    if problemes:
        raise EchangeImpossible(problemes)
    a = CreneauServiceGarde.objects.select_for_update().get(pk=echange.creneau_demandeur_id)
    b = CreneauServiceGarde.objects.select_for_update().get(pk=echange.creneau_cible_id)
    a.marin, b.marin = echange.cible, echange.demandeur
    a.save(update_fields=["marin", "updated_at"])
    b.save(update_fields=["marin", "updated_at"])
    echange.statut = EchangeService.STATUT_VALIDE
    echange.decide_le = timezone.now()
    echange.decide_par = user
    echange.save(update_fields=["statut", "decide_le", "decide_par", "updated_at"])
    _tracer(
        echange, user, "validation",
        f"{echange.libelle_creneau_demandeur} : {_nom(echange.demandeur)} -> {_nom(echange.cible)} ; "
        f"{echange.libelle_creneau_cible} : {_nom(echange.cible)} -> {_nom(echange.demandeur)}",
    )
    _notifier(
        [echange.demandeur, echange.cible] + chefs_de_liste_a_notifier(echange.liste),
        f"Échange validé : {_nom(echange.demandeur)} et {_nom(echange.cible)} ont permuté leurs tours "
        f"({_resume(echange)}). Les calendriers sont à jour.",
        echange,
    )


def annuler_echanges_du_creneau(creneau, acteur):
    """À appeler avant la suppression d'un créneau : les demandes en cours qui
    le concernent sont annulées avec explication, jamais laissées orphelines."""
    for echange in _echanges_en_cours_des_creneaux(creneau):
        _cloturer(
            echange, acteur, EchangeService.STATUT_ANNULE, "annulation_creneau_supprime",
            "Le créneau a été supprimé de la liste.", [echange.demandeur, echange.cible],
            f"L'échange ({_resume(echange)}) est annulé.",
        )
