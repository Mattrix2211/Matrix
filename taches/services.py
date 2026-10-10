"""Workflow des tâches : droits, transitions, notifications et traçabilité.

Un chef (CHEF_SECTION+) attribue une tâche à un marin de son périmètre et de son équipage.
Le fil de discussion est ouvert à l'assigné, au créateur, aux chefs du périmètre et aux
interlocuteurs que le chef ajoute (marins du même navire, y compris l'équipage à terre).
"""
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from absences.models import Absence
from absences.services import marin_dans_perimetre
from accounts.models import AuditLog
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import seuil_role
from matrix.core.roles import user_role_level
from matrix.core.scopes import equipage_marin_q
from notifications.models import Notification, NotificationLevel
from threads.models import Message, Thread
from threads.utils import ajouter_commentaire

from .models import ParametresTaches, Tache

User = get_user_model()


def peut_attribuer(user):
    """Niveau minimal configurable (Réglages > Seuils de rôle, action « tache_attribution »)."""
    return user_role_level(user) >= seuil_role("tache_attribution")


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def est_chef_de(user, marin):
    return peut_attribuer(user) and marin_dans_perimetre(user, marin)


def peut_gerer(user, tache):
    return tache.partagee and user.pk != tache.assigne_id and est_chef_de(user, tache.assigne)


def peut_consulter(user, tache):
    if user.pk in (tache.assigne_id, tache.created_by_id) or tache.participants.filter(pk=user.pk).exists():
        return True
    return peut_gerer(user, tache)


def taches_visibles(user):
    base = Q(assigne=user) | Q(created_by=user) | Q(participants=user)
    if peut_attribuer(user):
        base |= build_scope_q(user, "assigne__profile__") & equipage_marin_q(user, "assigne__profile__") & Q(partagee=True)
    return Tache.objects.filter(base).distinct()


def taches_a_suivre(user):
    """Tâches ouvertes dont `user` doit s'occuper : les siennes, et celles qu'il supervise lorsqu'elles sont bloquées."""
    ouvertes = taches_visibles(user).filter(statut__in=Tache.STATUTS_OUVERTS).select_related("assigne")
    return [
        t for t in ouvertes
        if t.assigne_id == user.pk or (t.statut == Tache.STATUT_BLOQUEE and peut_gerer(user, t))
    ]


def taches_supervisees(user):
    """Tâches des marins du périmètre et de l'équipage d'un chef, hors les siennes."""
    if not peut_attribuer(user):
        return Tache.objects.none()
    return Tache.objects.filter(
        build_scope_q(user, "assigne__profile__"), equipage_marin_q(user, "assigne__profile__"), partagee=True,
    ).exclude(assigne=user)


def avancement_equipe(user, aujourdhui=None):
    """Synthèse pour le chef : tâches par statut, charge par marin, retards, blocages et conflits d'absence.

    Les tâches terminées ne comptent que sur la durée réglée (jours_terminees_affichees).
    Un conflit est une tâche ouverte dont l'échéance tombe pendant une absence déclarée ou validée de son marin.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    depuis = timezone.now() - timedelta(days=ParametresTaches.courants().jours_terminees_affichees)
    taches = taches_supervisees(user).select_related("assigne")
    ouvertes = [t for t in taches if t.ouverte]
    comptes = {statut: 0 for statut, _ in Tache.STATUT_CHOICES}
    for t in ouvertes:
        comptes[t.statut] += 1
    comptes[Tache.STATUT_TERMINEE] = taches.filter(statut=Tache.STATUT_TERMINEE, terminee_le__gte=depuis).count()

    marins = list(marins_assignables(user))
    absences = list(Absence.objects.filter(
        marin__in=marins, date_fin__gte=aujourdhui).select_related("type_absence").order_by("date_debut"))
    charges = []
    for marin in marins:
        siennes = [t for t in ouvertes if t.assigne_id == marin.pk]
        absent = next((a for a in absences if a.marin_id == marin.pk and a.date_debut <= aujourdhui), None)
        charges.append({
            "marin": marin, "ouvertes": len(siennes), "retards": sum(t.en_retard_au(aujourdhui) for t in siennes),
            "bloquees": sum(t.statut == Tache.STATUT_BLOQUEE for t in siennes), "absent_jusqu_au": absent and absent.date_fin,
        })
    charges.sort(key=lambda c: (-c["ouvertes"], c["marin"].username))
    conflits = [
        {"tache": t, "absence": a}
        for t in ouvertes for a in absences
        if t.echeance and a.marin_id == t.assigne_id and a.date_debut <= t.echeance <= a.date_fin
    ]
    return {
        "comptes": comptes,
        "total": sum(comptes.values()),
        "retards": [t for t in ouvertes if t.en_retard_au(aujourdhui)],
        "blocages": [t for t in ouvertes if t.statut == Tache.STATUT_BLOQUEE],
        "charges": charges,
        "charge_max": max((c["ouvertes"] for c in charges), default=0),
        "conflits": conflits,
    }


def marins_assignables(user):
    """Marins à qui `user` peut attribuer une tâche (lui-même exclu)."""
    if not peut_attribuer(user):
        return User.objects.none()
    return User.objects.filter(build_scope_q(user, "profile__"), equipage_marin_q(user)).exclude(pk=user.pk).order_by("username")


def interlocuteurs_possibles(tache):
    """Marins du même navire que l'assigné (équipage à terre compris), hors assigné et participants."""
    navire = getattr(tache.assigne.profile, "ship_id", None)
    if navire is None:
        return User.objects.none()
    return User.objects.filter(profile__ship_id=navire, is_active=True).exclude(
        pk__in=[tache.assigne_id, *tache.participants.values_list("pk", flat=True)]
    ).order_by("username")


def _tracer(tache, acteur, action, extra=""):
    AuditLog.objects.create(
        actor=acteur, action=f"tache_{action}", target_user=tache.assigne,
        details=f"tache={tache.pk}; statut={tache.statut}; echeance={tache.echeance.isoformat() if tache.echeance else 'aucune'}{extra}",
    )


def _message_systeme(tache, corps):
    thread, _ = Thread.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(tache), object_id=str(tache.pk),
    )
    Message.objects.create(thread=thread, author=None, body=corps, is_system=True)


def _destinataires(tache, sauf):
    """Acteurs du dossier à prévenir : assigné, créateur, interlocuteurs du fil."""
    ids = {tache.assigne_id, tache.created_by_id, *tache.participants.values_list("pk", flat=True)}
    ids.discard(sauf.pk)
    ids.discard(None)
    return User.objects.filter(pk__in=ids, is_active=True)


def _notifier(tache, destinataires, verb, niveau=NotificationLevel.INFO):
    for user in destinataires:
        Notification.objects.create(user=user, verb=verb, level=niveau, target=tache)


def creer_tache(chef, assigne, titre, echeance=None, description="", priorite=Tache.PRIORITE_NORMALE, partagee=True):
    """Un chef attribue une tâche ; un marin peut aussi se créer la sienne (privée sauf partage de sa part)."""
    personnelle = chef.pk == assigne.pk
    if not personnelle and not est_chef_de(chef, assigne):
        raise PermissionError("Vous ne pouvez pas attribuer de tâche à ce marin.")
    tache = Tache(
        titre=titre.strip(), description=description.strip(), echeance=echeance, priorite=priorite,
        partagee=partagee if personnelle else True, assigne=assigne, created_by=chef, updated_by=chef,
    )
    tache.full_clean(exclude=["assigne"])
    tache.save()
    _tracer(tache, chef, "creation")
    if not personnelle:
        delai = f" (échéance {echeance:%d/%m/%Y})" if echeance else ""
        _notifier(tache, [assigne], f"{_nom(chef)} vous a attribué la tâche « {tache.titre} »{delai}.")
    return tache


def _enregistrer(tache, acteur, action, champs, extra=""):
    tache.updated_by = acteur
    tache.save(update_fields=[*champs, "updated_by", "updated_at"])
    _tracer(tache, acteur, action, extra)


def _date(valeur):
    return f"{valeur:%d/%m/%Y}" if valeur else "aucune"


def peut_modifier(user, tache):
    """Un chef du périmètre modifie une tâche attribuée et ouverte ; jamais la tâche personnelle d'un marin."""
    return tache.ouverte and not tache.personnelle and peut_gerer(user, tache)


def partager(tache, user, partagee):
    """Le marin partage sa tâche personnelle avec ses chefs, ou la reprend en privé (les interlocuteurs sont retirés)."""
    if not tache.personnelle or user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin peut modifier le partage de sa tâche personnelle.")
    if tache.partagee == partagee:
        raise ValidationError("Le partage est déjà dans cet état.")
    tache.partagee = partagee
    if not partagee:
        tache.participants.clear()
    _enregistrer(tache, user, "partage" if partagee else "retrait_partage", ["partagee"])


def modifier_tache(chef, tache, assigne, echeance, priorite):
    """Réaffecte, replanifie ou change la priorité ; chaque changement est tracé dans le fil et l'audit.

    La tâche réaffectée repart « À faire » chez son nouveau titulaire, sans motif de blocage.
    """
    if not peut_modifier(chef, tache):
        raise PermissionError("Vous ne pouvez pas modifier cette tâche.")
    changements, champs, ancien = [], ["echeance", "priorite"], tache.assigne
    if assigne.pk != tache.assigne_id:
        if assigne.pk == chef.pk or not est_chef_de(chef, assigne):
            raise PermissionError("Vous ne pouvez pas confier la tâche à ce marin.")
        tache.assigne = assigne
        tache.statut, tache.motif_blocage = Tache.STATUT_A_FAIRE, ""
        champs += ["assigne", "statut", "motif_blocage"]
        changements.append(f"réaffectée de {_nom(ancien)} à {_nom(assigne)}")
    if echeance != tache.echeance:
        changements.append(f"échéance du {_date(tache.echeance)} au {_date(echeance)}")
    if priorite != tache.priorite:
        changements.append(f"priorité {tache.get_priorite_display().lower()} → {dict(Tache.PRIORITE_CHOICES).get(priorite, priorite).lower()}")
    if not changements:
        raise ValidationError("Aucune modification à enregistrer.")
    tache.echeance, tache.priorite = echeance, priorite
    tache.full_clean(exclude=["assigne"])
    resume = "; ".join(changements)
    _enregistrer(tache, chef, "modification", champs, extra=f"; modifications={resume}")
    _message_systeme(tache, f"{_nom(chef)} a modifié la tâche : {resume}.")
    if tache.assigne_id != ancien.pk:
        _relances(tache).filter(user=ancien, is_read=False).update(is_read=True)
        _notifier(tache, [tache.assigne], f"{_nom(chef)} vous a confié la tâche « {tache.titre} » ({resume}).")
        _notifier(tache, [ancien], f"La tâche « {tache.titre} » ne vous est plus attribuée : {resume}.")
    else:
        _notifier(tache, [tache.assigne], f"{_nom(chef)} a modifié « {tache.titre} » : {resume}.")


def demarrer(tache, user):
    if user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin assigné peut démarrer la tâche.")
    if tache.statut != Tache.STATUT_A_FAIRE:
        raise ValidationError("La tâche est déjà démarrée.")
    tache.statut = Tache.STATUT_EN_COURS
    _enregistrer(tache, user, "demarrage", ["statut"])


def signaler_blocage(tache, user, motif):
    if user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin assigné peut signaler un blocage.")
    motif = motif.strip()
    if not motif or not tache.ouverte:
        raise ValidationError("Indiquez le motif du blocage d'une tâche ouverte.")
    tache.statut = Tache.STATUT_BLOQUEE
    tache.motif_blocage = motif
    _enregistrer(tache, user, "blocage", ["statut", "motif_blocage"])
    _message_systeme(tache, f"{_nom(user)} signale un blocage : {motif}")
    _notifier(
        tache, _destinataires(tache, user),
        f"{_nom(user)} est bloqué sur « {tache.titre} » : {motif}", NotificationLevel.WARNING,
    )


def repondre(tache, user, corps):
    if not peut_consulter(user, tache):
        raise PermissionError("Vous n'avez pas accès au fil de cette tâche.")
    corps = corps.strip()
    if not corps:
        raise ValidationError("Le message ne peut pas être vide.")
    ajouter_commentaire(tache, user, corps)
    _notifier(tache, _destinataires(tache, user), f"{_nom(user)} a répondu sur « {tache.titre} ».")


def ajouter_participant(tache, chef, user):
    if not peut_gerer(chef, tache):
        raise PermissionError("Seul un chef du périmètre peut ajouter un interlocuteur.")
    if not interlocuteurs_possibles(tache).filter(pk=user.pk).exists():
        raise ValidationError("Cet interlocuteur n'appartient pas au navire de la tâche.")
    tache.participants.add(user)
    _tracer(tache, chef, "interlocuteur")
    _message_systeme(tache, f"{_nom(chef)} a ajouté {_nom(user)} au fil.")
    _notifier(tache, [user], f"{_nom(chef)} vous a ajouté au fil de la tâche « {tache.titre} ».")


def reprendre(tache, chef):
    """Le chef lève le blocage une fois la solution donnée dans le fil."""
    if not peut_gerer(chef, tache):
        raise PermissionError("Seul un chef du périmètre peut lever un blocage.")
    if tache.statut != Tache.STATUT_BLOQUEE:
        raise ValidationError("La tâche n'est pas bloquée.")
    tache.statut = Tache.STATUT_EN_COURS
    _enregistrer(tache, chef, "reprise", ["statut"])
    _message_systeme(tache, f"{_nom(chef)} lève le blocage : la tâche reprend.")
    _notifier(tache, [tache.assigne], f"Blocage levé sur « {tache.titre} » : vous pouvez reprendre.")


def rendre_compte(tache, user, compte_rendu):
    if user.pk != tache.assigne_id:
        raise PermissionError("Seul le marin assigné peut rendre compte.")
    compte_rendu = compte_rendu.strip()
    if not compte_rendu or not tache.ouverte:
        raise ValidationError("Rédigez le compte rendu d'une tâche ouverte.")
    tache.statut = Tache.STATUT_TERMINEE
    tache.compte_rendu = compte_rendu
    tache.terminee_le = timezone.now()
    _enregistrer(tache, user, "compte_rendu", ["statut", "compte_rendu", "terminee_le"])
    _message_systeme(tache, f"{_nom(user)} a rendu compte : {compte_rendu}")
    _notifier(tache, _destinataires(tache, user), f"{_nom(user)} a terminé « {tache.titre} » et rendu compte.")


PREFIXE_RELANCE = "Tâche en retard"


def _relances(tache):
    return Notification.objects.filter(
        content_type=ContentType.objects.get_for_model(tache), object_id=str(tache.pk), verb__startswith=PREFIXE_RELANCE,
    )


def _destinataires_relance(tache, parametres):
    """Tâche bloquée : les chefs qui peuvent lever le blocage ; sinon l'assigné et le chef qui l'a attribuée."""
    if tache.statut == Tache.STATUT_BLOQUEE:
        if not parametres.relancer_chefs_si_blocage or not tache.partagee:
            return []
        candidats = User.objects.filter(is_active=True, profile__ship_id=getattr(tache.assigne.profile, "ship_id", None))
        return [u for u in candidats if u.pk != tache.assigne_id and est_chef_de(u, tache.assigne)]
    ids = set()
    if parametres.relancer_assigne:
        ids.add(tache.assigne_id)
    if parametres.relancer_chef_attributeur and tache.created_by_id:
        ids.add(tache.created_by_id)
    return list(User.objects.filter(pk__in=ids, is_active=True))


def relancer_echeances_depassees(aujourdhui=None):
    """Relance les acteurs d'une tâche en retard, tous les `jours_entre_relances` jours tant qu'elle n'est pas traitée.

    Le dédoublonnage ignore l'état de lecture : une relance lue n'est pas une tâche faite.
    Les relances encore non lues d'une tâche terminée sont soldées.
    """
    parametres = ParametresTaches.courants()
    aujourdhui = aujourdhui or timezone.localdate()
    creees = 0
    if parametres.jours_entre_relances:
        depuis = aujourdhui - timedelta(days=parametres.jours_entre_relances - 1)
        debut = timezone.make_aware(datetime.combine(depuis, time.min))
        for tache in Tache.objects.filter(
            statut__in=Tache.STATUTS_OUVERTS, echeance__lt=aujourdhui, assigne__is_active=True,
        ).select_related("assigne"):
            jours = (aujourdhui - tache.echeance).days
            etat = " (bloquée)" if tache.statut == Tache.STATUT_BLOQUEE else ""
            for user in _destinataires_relance(tache, parametres):
                if _relances(tache).filter(user=user, created_at__gte=debut).exists():
                    continue
                qui = f" de {_nom(tache.assigne)}" if user.pk != tache.assigne_id else ""
                _notifier(
                    tache, [user],
                    f"{PREFIXE_RELANCE}{etat} : « {tache.titre} »{qui}, échéance dépassée de {jours} j.",
                    NotificationLevel.WARNING,
                )
                creees += 1
    Notification.objects.filter(
        content_type=ContentType.objects.get_for_model(Tache), verb__startswith=PREFIXE_RELANCE, is_read=False,
        object_id__in=[str(pk) for pk in Tache.objects.filter(statut=Tache.STATUT_TERMINEE).values_list("pk", flat=True)],
    ).update(is_read=True)
    return creees
