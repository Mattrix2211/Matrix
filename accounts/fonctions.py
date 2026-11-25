"""Fonctions de commandant adjoint à confirmer après la migration L06 (AC-14).

Tant qu'une demande est en attente, la fonction ne confère aucun droit. La décision relève de l'autorité compétente pour
désigner un commandant adjoint (le commandant du bâtiment, ou l'administrateur général) ; personne ne décide pour soi-même.
Les droits techniques du compte ne sont jamais touchés.
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from matrix.core.commandants_adjoints import titulaires_commandant_adjoint
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.scopes import is_master_admin, ship_id_for_user
from org.models import CommandantAdjoint

from .models import AuditLog, FonctionAConfirmer, Roles, UserProfile

CONFIRMER, CORRIGER, REFUSER = "confirmer", "corriger", "refuser"


def peut_decider(acteur):
    """Autorité compétente pour désigner un commandant adjoint (AC-02)."""
    return is_master_admin(acteur) or user_role_level(acteur) >= RoleLevel.COMMANDANT


def demandes_visibles_par(acteur):
    if not peut_decider(acteur):
        return FonctionAConfirmer.objects.none()
    qs = FonctionAConfirmer.objects.select_related("user", "ship", "decide_par")
    return qs if is_master_admin(acteur) else qs.filter(ship_id=ship_id_for_user(acteur))


def nombre_en_attente(acteur):
    return demandes_visibles_par(acteur).filter(statut=FonctionAConfirmer.Statut.EN_ATTENTE).count()


def decider(acteur, demande_id, decision, fonction=""):
    """Confirme, corrige ou refuse une demande. Lève ValidationError (message affichable) ou PermissionDenied."""
    if not peut_decider(acteur):
        raise PermissionDenied
    with transaction.atomic():
        try:
            demande = demandes_visibles_par(acteur).select_for_update(of=("self",)).get(pk=demande_id)
        except FonctionAConfirmer.DoesNotExist:
            raise PermissionDenied
        if decision not in (CONFIRMER, CORRIGER, REFUSER):
            raise ValidationError("Décision inconnue.")
        if not is_master_admin(acteur) and ship_id_for_user(acteur) is None:
            raise PermissionDenied
        if demande.statut != FonctionAConfirmer.Statut.EN_ATTENTE:
            raise ValidationError("Cette demande a déjà été traitée.")
        if demande.user_id == acteur.pk:
            raise PermissionDenied
        profil = UserProfile.objects.select_for_update().get(user_id=demande.user_id)
        if profil.ship_id != demande.ship_id:
            raise ValidationError("Le marin a changé de bâtiment depuis la migration : la demande n'est plus applicable.")
        if decision == REFUSER:
            retenue, statut = "", FonctionAConfirmer.Statut.REFUSEE
        else:
            retenue = demande.fonction_ancienne if decision == CONFIRMER else fonction
            if retenue not in CommandantAdjoint.values:
                raise ValidationError("Choisissez une fonction de commandant adjoint valide.")
            statut = FonctionAConfirmer.Statut.CONFIRMEE if decision == CONFIRMER else FonctionAConfirmer.Statut.CORRIGEE
            if titulaires_commandant_adjoint(profil.ship, retenue, profil.equipage).exclude(pk=demande.user_id).exists():
                raise ValidationError("Cette fonction est déjà tenue sur le bâtiment : révoquez d'abord le titulaire actuel.")
            if profil.role in (Roles.COMMANDANT, Roles.COMMANDANT_EN_SECOND, Roles.MASTER_ADMIN):
                raise ValidationError("Le marin exerce déjà une autorité supérieure : la fonction ne peut pas lui être attribuée ainsi.")
            profil.role, profil.fonction_coma = Roles.ETAT_MAJOR, retenue
            profil.save(update_fields=["role", "fonction_coma"])
        demande.statut, demande.fonction_retenue = statut, retenue
        demande.decide_par, demande.decide_le = acteur, timezone.now()
        demande.save(update_fields=["statut", "fonction_retenue", "decide_par", "decide_le", "updated_at"])
        AuditLog.objects.create(
            actor=acteur, action=f"fonction_a_confirmer_{decision}", target_user=demande.user,
            details=f"ancienne={demande.fonction_ancienne}; retenue={retenue or '—'}",
        )
    return demande


def anomalies_de_coherence():
    """Écarts entre le journal de la migration, les demandes et les décisions (liste de messages ; vide si cohérent)."""
    anomalies = []
    for ligne in AuditLog.objects.filter(action="l06_migration_role", target_user__isnull=False):
        fonction = ligne.details.split("fonction_a_confirmer=")[-1]
        if fonction not in ("", "aucune") and not FonctionAConfirmer.objects.filter(user_id=ligne.target_user_id).exists():
            anomalies.append(f"Fonction {fonction} journalisée sans demande pour le compte {ligne.target_user_id}.")
    for demande in FonctionAConfirmer.objects.exclude(statut=FonctionAConfirmer.Statut.EN_ATTENTE):
        decision = {"CONFIRMEE": CONFIRMER, "CORRIGEE": CORRIGER, "REFUSEE": REFUSER}[demande.statut]
        if not AuditLog.objects.filter(action=f"fonction_a_confirmer_{decision}", target_user_id=demande.user_id).exists():
            anomalies.append(f"Décision sans trace d'audit pour le compte {demande.user_id}.")
        if demande.statut != FonctionAConfirmer.Statut.REFUSEE and not UserProfile.objects.filter(
            user_id=demande.user_id, role=Roles.ETAT_MAJOR, fonction_coma=demande.fonction_retenue
        ).exists():
            anomalies.append(f"La fonction retenue n'est plus portée par le compte {demande.user_id}.")
    return anomalies
