"""Workflow autour des absences : qui peut déclarer/valider pour quel marin,
notifications et journal d'audit — même mécanique que quarts/echanges.py
(AuditLog + Notification pour la traçabilité), pour rester cohérent avec le
reste du projet plutôt que d'inventer un nouveau style.

Règle de gestion (HYPOTHÈSE DE CADRAGE, à confirmer par le métier — cf.
commentaire Notion de la tâche) : un marin déclare toujours SA PROPRE absence
(statut « Déclarée », à valider ensuite) ; un chef CHEF_SECTION et au-dessus,
pour un marin de son périmètre organisationnel, peut soit déclarer une
absence pour lui (immédiatement « Validée », puisque le chef fait foi), soit
valider une absence déjà déclarée par le marin lui-même. Même seuil
(CHEF_SECTION) que la gestion d'équipe déjà appliquée ailleurs dans le projet
(ex. calendar_app::_peut_agir_occurrence/_peut_agir_ticket)."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from accounts.models import AuditLog
from matrix.core.mixins import build_scope_q
from matrix.core.roles import RoleLevel, user_role_level
from notifications.models import Notification

from .models import Absence

User = get_user_model()

# Seuil à partir duquel un utilisateur peut gérer (déclarer/valider) une
# absence d'UN AUTRE marin de son périmètre — même seuil que les autres
# actions de gestion d'équipe du calendrier central (RoleLevel.CHEF_SECTION).
NIVEAU_REQUIS_GESTION_ABSENCE = RoleLevel.CHEF_SECTION


def _nom(user):
    return (user.get_full_name() or user.username) if user else "un marin supprimé"


def marin_dans_perimetre(user, marin):
    """Vrai si `marin` appartient au périmètre organisationnel direct de
    `user` (même niveau exact, via le profil — cf. matrix/core/scopes.py) —
    réutilise build_scope_q déjà existant plutôt que d'inventer un nouveau
    mécanisme de périmètre. Pas de cascade hiérarchique (ex. un CHEF_SECTEUR
    ne voit pas automatiquement les sections de son secteur ici) : cadrage
    volontairement simple, aligné sur la majorité des usages de build_scope_q
    dans le projet — à revoir si un besoin de cascade est confirmé côté
    métier (cf. commentaire Notion de la tâche)."""
    return User.objects.filter(build_scope_q(user, "profile__"), pk=marin.pk).exists()


def peut_gerer_absence_de(user, marin):
    """Vrai si `user` peut déclarer/modifier une absence pour `marin` : le
    marin lui-même, ou un chef (CHEF_SECTION+) dont le périmètre couvre ce
    marin."""
    if user.pk == marin.pk:
        return True
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_ABSENCE and marin_dans_perimetre(user, marin)


def peut_valider_absence(user, absence):
    """Vrai si `user` peut valider CETTE absence précise : seul un chef
    (CHEF_SECTION+) de périmètre, jamais le marin concerné lui-même (une
    absence validée par soi-même n'aurait aucune valeur de contrôle)."""
    if user.pk == absence.marin_id:
        return False
    return user_role_level(user) >= NIVEAU_REQUIS_GESTION_ABSENCE and marin_dans_perimetre(user, absence.marin)


def marins_de_mon_perimetre(user):
    """Marins du périmètre organisationnel direct de `user` (hors lui-même) —
    utilisé pour peupler le sélecteur « déclarer pour un marin » d'un chef.
    Même logique que marin_dans_perimetre, en sens inverse (queryset plutôt
    que test unitaire)."""
    return User.objects.filter(build_scope_q(user, "profile__")).exclude(pk=user.pk).order_by("username")


def absences_visibles(user):
    """Absences visibles par `user` : les siennes toujours, plus celles de
    son périmètre organisationnel s'il est CHEF_SECTION et au-dessus (même
    principe de visibilité par périmètre que le reste du projet)."""
    if user_role_level(user) >= NIVEAU_REQUIS_GESTION_ABSENCE:
        return Absence.objects.filter(Q(marin=user) | build_scope_q(user, "marin__profile__")).distinct()
    return Absence.objects.filter(marin=user)


def _tracer(absence, acteur, action):
    AuditLog.objects.create(
        actor=acteur, action=f"absence_{action}", target_user=absence.marin,
        details=(
            f"absence={absence.pk}; type={absence.type_absence_id}; "
            f"{absence.date_debut.isoformat()} -> {absence.date_fin.isoformat()}"
        ),
    )


def declarer_absence(auteur, marin, type_absence, date_debut, date_fin, motif=""):
    """Crée une absence pour `marin`, saisie par `auteur` (le marin
    lui-même, ou un chef de son périmètre). Statut initial : « Déclarée » si
    le marin se déclare lui-même (reste à valider par un chef), « Validée »
    d'emblée si c'est un chef qui la saisit pour son équipe (le chef fait
    foi — cf. docstring de module)."""
    if not peut_gerer_absence_de(auteur, marin):
        raise PermissionError("Vous ne pouvez pas déclarer d'absence pour ce marin.")
    absence = Absence(
        marin=marin, type_absence=type_absence, date_debut=date_debut, date_fin=date_fin,
        motif=motif.strip(), created_by=auteur, updated_by=auteur,
    )
    absence.full_clean()
    absence.save()
    if auteur.pk != marin.pk:
        absence.statut = Absence.STATUT_VALIDEE
        absence.validee_le = timezone.now()
        absence.validee_par = auteur
        absence.save(update_fields=["statut", "validee_le", "validee_par", "updated_at"])
    _tracer(absence, auteur, "declaration")

    if auteur.pk == marin.pk:
        # Le marin s'est déclaré lui-même : les chefs de son périmètre direct
        # (même niveau que marin_dans_perimetre) sont prévenus pour validation.
        chefs = [
            c for c in User.objects.filter(build_scope_q(marin, "profile__")).exclude(pk=marin.pk)
            if user_role_level(c) >= NIVEAU_REQUIS_GESTION_ABSENCE
        ]
        for chef in chefs:
            Notification.objects.create(
                user=chef,
                verb=(
                    f"{_nom(marin)} a déclaré une absence ({type_absence}) du "
                    f"{date_debut:%d/%m/%Y} au {date_fin:%d/%m/%Y}, à valider."
                ),
                target=absence,
            )
    else:
        Notification.objects.create(
            user=marin,
            verb=(
                f"{_nom(auteur)} a enregistré votre absence ({type_absence}) du "
                f"{date_debut:%d/%m/%Y} au {date_fin:%d/%m/%Y}."
            ),
            target=absence,
        )
    return absence


def valider_absence(absence, user):
    if not peut_valider_absence(user, absence):
        raise PermissionError("Vous ne pouvez pas valider cette absence.")
    absence.statut = Absence.STATUT_VALIDEE
    absence.validee_le = timezone.now()
    absence.validee_par = user
    absence.save(update_fields=["statut", "validee_le", "validee_par", "updated_at"])
    _tracer(absence, user, "validation")
    Notification.objects.create(
        user=absence.marin,
        verb=f"{_nom(user)} a validé votre absence du {absence.date_debut:%d/%m/%Y} au {absence.date_fin:%d/%m/%Y}.",
        target=absence,
    )
    return absence
