"""Workflow des tâches : droits, transitions, notifications et traçabilité.

Un chef (CHEF_SECTION+) attribue une tâche à un marin de son périmètre et de son équipage.
Le fil de discussion est ouvert à l'assigné, au créateur, aux chefs du périmètre et aux
interlocuteurs que le chef ajoute (marins du même navire, y compris l'équipage à terre).
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from absences.services import marin_dans_perimetre
from accounts.models import AuditLog
from matrix.core.mixins import build_scope_q
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import equipage_marin_q
from notifications.models import Notification, NotificationLevel
from threads.models import Message, Thread
from threads.utils import ajouter_commentaire

from .models import Tache

User = get_user_model()

NIVEAU_REQUIS_GESTION_TACHE = RoleLevel.CHEF_SECTION
JOURS_TERMINEES_AFFICHEES = 30


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def est_chef_de(user, marin):
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_TACHE and marin_dans_perimetre(user, marin)


def peut_gerer(user, tache):
    return user.pk != tache.assigne_id and est_chef_de(user, tache.assigne)


def peut_consulter(user, tache):
    if user.pk in (tache.assigne_id, tache.created_by_id) or tache.participants.filter(pk=user.pk).exists():
        return True
    return peut_gerer(user, tache)


def taches_visibles(user):
    base = Q(assigne=user) | Q(created_by=user) | Q(participants=user)
    if user_role_level(user) >= NIVEAU_REQUIS_GESTION_TACHE:
        base |= build_scope_q(user, "assigne__profile__") & equipage_marin_q(user, "assigne__profile__")
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
    if user_role_level(user) < NIVEAU_REQUIS_GESTION_TACHE:
        return Tache.objects.none()
    return Tache.objects.filter(
        build_scope_q(user, "assigne__profile__"), equipage_marin_q(user, "assigne__profile__"),
    ).exclude(assigne=user)


def avancement_equipe(user, aujourdhui=None):
    """Synthèse pour le chef : tâches par statut, retards et blocages en attente de levée.

    Les tâches terminées ne comptent que sur les JOURS_TERMINEES_AFFICHEES derniers jours.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    depuis = timezone.now() - timedelta(days=JOURS_TERMINEES_AFFICHEES)
    taches = taches_supervisees(user).select_related("assigne")
    ouvertes = [t for t in taches if t.ouverte]
    comptes = {statut: 0 for statut, _ in Tache.STATUT_CHOICES}
    for t in ouvertes:
        comptes[t.statut] += 1
    comptes[Tache.STATUT_TERMINEE] = taches.filter(statut=Tache.STATUT_TERMINEE, terminee_le__gte=depuis).count()
    return {
        "comptes": comptes,
        "total": sum(comptes.values()),
        "retards": [t for t in ouvertes if t.echeance < aujourdhui],
        "blocages": [t for t in ouvertes if t.statut == Tache.STATUT_BLOQUEE],
    }


def marins_assignables(user):
    """Marins à qui `user` peut attribuer une tâche (lui-même exclu)."""
    if user_role_level(user) < NIVEAU_REQUIS_GESTION_TACHE:
        return User.objects.none()
    return User.objects.filter(build_scope_q(user, "profile__"), equipage_marin_q(user)).exclude(pk=user.pk).order_by("username")


def interlocuteurs_possibles(tache):
    """Marins du même navire que l'assigné (équipage à terre compris), hors assigné et participants."""
    navire = getattr(tache.assigne.profile, "ship_id", None)
    if navire is None:
        return User.objects.none()
    return User.objects.filter(profile__ship_id=navire).exclude(
        pk__in=[tache.assigne_id, *tache.participants.values_list("pk", flat=True)]
    ).order_by("username")


def _tracer(tache, acteur, action):
    AuditLog.objects.create(
        actor=acteur, action=f"tache_{action}", target_user=tache.assigne,
        details=f"tache={tache.pk}; statut={tache.statut}; echeance={tache.echeance.isoformat()}",
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
    return User.objects.filter(pk__in=ids)


def _notifier(tache, destinataires, verb, niveau=NotificationLevel.INFO):
    for user in destinataires:
        Notification.objects.create(user=user, verb=verb, level=niveau, target=tache)


def creer_tache(chef, assigne, titre, echeance, description=""):
    if not est_chef_de(chef, assigne):
        raise PermissionError("Vous ne pouvez pas attribuer de tâche à ce marin.")
    tache = Tache(
        titre=titre.strip(), description=description.strip(), echeance=echeance,
        assigne=assigne, created_by=chef, updated_by=chef,
    )
    tache.full_clean(exclude=["assigne"])
    tache.save()
    _tracer(tache, chef, "creation")
    _notifier(tache, [assigne], f"{_nom(chef)} vous a attribué la tâche « {tache.titre} » (échéance {echeance:%d/%m/%Y}).")
    return tache


def _enregistrer(tache, acteur, action, champs):
    tache.updated_by = acteur
    tache.save(update_fields=[*champs, "updated_by", "updated_at"])
    _tracer(tache, acteur, action)


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


def _destinataires_relance(tache):
    """Tâche bloquée : les chefs qui peuvent lever le blocage ; sinon l'assigné et le chef qui l'a attribuée."""
    if tache.statut == Tache.STATUT_BLOQUEE:
        candidats = User.objects.filter(is_active=True, profile__ship_id=getattr(tache.assigne.profile, "ship_id", None))
        return [u for u in candidats if u.pk != tache.assigne_id and est_chef_de(u, tache.assigne)]
    ids = {tache.assigne_id, tache.created_by_id} - {None}
    return list(User.objects.filter(pk__in=ids, is_active=True))


def relancer_echeances_depassees(aujourdhui=None):
    """Relance une fois par jour, tant que la tâche n'est pas traitée, les acteurs d'une tâche en retard.

    Le dédoublonnage ignore l'état de lecture : une relance lue n'est pas une tâche faite.
    Les relances encore non lues d'une tâche terminée sont soldées.
    """
    aujourdhui = aujourdhui or timezone.localdate()
    debut_jour = timezone.make_aware(timezone.datetime.combine(aujourdhui, timezone.datetime.min.time()))
    creees = 0
    for tache in Tache.objects.filter(statut__in=Tache.STATUTS_OUVERTS, echeance__lt=aujourdhui, assigne__is_active=True).select_related("assigne"):
        jours = (aujourdhui - tache.echeance).days
        etat = " (bloquée)" if tache.statut == Tache.STATUT_BLOQUEE else ""
        for user in _destinataires_relance(tache):
            if _relances(tache).filter(user=user, created_at__gte=debut_jour).exists():
                continue
            qui = f" de {_nom(tache.assigne)}" if user.pk != tache.assigne_id else ""
            _notifier(
                tache, [user],
                f"{PREFIXE_RELANCE}{etat} : « {tache.titre} »{qui}, échéance dépassée de {jours} j.", NotificationLevel.WARNING,
            )
            creees += 1
    for tache in Tache.objects.filter(statut=Tache.STATUT_TERMINEE):
        _relances(tache).filter(is_read=False).update(is_read=True)
    return creees
