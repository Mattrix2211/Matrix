"""Réinitialisation du mot de passe d'un marin par l'administrateur du bâtiment (sans messagerie à bord)."""
import secrets
import string

from django.core.exceptions import PermissionDenied

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from matrix.core.role_thresholds import niveau_pour_action, niveau_requis_pour
from matrix.core.roles import RoleLevel, est_administrateur_technique, user_role_level
from matrix.core.scopes import is_master_admin

from .models import AuditLog, UserProfile

ALPHABET = string.ascii_letters + string.digits + "!@$%*#?"
LONGUEUR = 14


def generer_mot_de_passe(longueur=LONGUEUR):
    """Mot de passe aléatoire contenant minuscule, majuscule, chiffre et symbole."""
    while True:
        mot_de_passe = "".join(secrets.choice(ALPHABET) for _ in range(longueur))
        if (any(c.islower() for c in mot_de_passe) and any(c.isupper() for c in mot_de_passe)
                and any(c.isdigit() for c in mot_de_passe) and any(c in "!@$%*#?" for c in mot_de_passe)):
            return mot_de_passe


def peut_reinitialiser(acteur):
    """Niveau minimal configurable (Réglages > Seuils de rôle) : administrateur du bâtiment par défaut."""
    return niveau_pour_action(acteur, "mot_de_passe_reinitialisation") >= niveau_requis_pour(acteur, "mot_de_passe_reinitialisation")


# Désignations indépendantes du rôle : qui les porte exerce une autorité que le rôle ne montre pas.
DESIGNATIONS = (
    "designations_chef_de_liste", "redactions_feuille_service", "delegations_programme", "formations_referentes",
    "specialites_dont_il_est_responsable", "classes_navire_dont_il_est_responsable", "navires_brh",
    "navires_dont_il_est_referent_formation", "remplacements_chef_de_liste", "responsables_specialite_diriges",
)


def porte_une_designation(utilisateur):
    return any(getattr(utilisateur, relation).exists() for relation in DESIGNATIONS)


# Niveaux de protection d'un compte face à la réinitialisation de son mot de passe (AC-12). Le plus élevé l'emporte.
PROTECTION_TECHNIQUE = 1  # administrateur technique du bâtiment : équipier à chef de service sans autre autorité
PROTECTION_GENERALE = 2  # administrateur général : autorités du bâtiment, administrateurs techniques, désignations
PROTECTION_RECUPERATION = 3  # administrateur général Matrix, superutilisateur : procédure de récupération


def niveau_de_protection(cible):
    """Niveau de protection d'un compte, d'après son rôle ET ses habilitations et désignations effectives."""
    profil = getattr(cible, "profile", None)
    role = profil.role if profil else ""
    if cible.is_superuser or role == "MASTER_ADMIN":
        return PROTECTION_RECUPERATION
    if (
        user_role_level(cible) >= RoleLevel.ETAT_MAJOR or (profil and (profil.administrateur_technique or profil.fonction_coma))
        or cible.is_staff or cible.groups.exists() or cible.user_permissions.exists() or porte_une_designation(cible)
    ):
        return PROTECTION_GENERALE
    return PROTECTION_TECHNIQUE


def niveau_de_competence(acteur):
    """Plus haut niveau de protection qu'un acteur peut réinitialiser."""
    if not peut_reinitialiser(acteur):
        return 0
    if is_master_admin(acteur):
        return PROTECTION_GENERALE
    return PROTECTION_TECHNIQUE if est_administrateur_technique(acteur) else 0


def peut_reinitialiser_cible(acteur, cible):
    return acteur.pk != cible.pk and niveau_de_protection(cible) <= niveau_de_competence(acteur)


def reinitialiser_mot_de_passe(acteur, cible):
    """Définit un mot de passe provisoire que le marin devra changer ; le renvoie une seule fois.

    L'appelant a déjà borné `cible` au périmètre navire de l'acteur. Le mot de passe n'est ni enregistré en clair ni écrit
    dans le journal d'audit ; il expire (`DUREE_MOT_DE_PASSE_PROVISOIRE_HEURES`), les sessions ouvertes du compte sont
    invalidées par le changement de mot de passe et le titulaire est notifié."""
    if not peut_reinitialiser_cible(acteur, cible):
        raise PermissionDenied
    mot_de_passe = generer_mot_de_passe()
    cible.set_password(mot_de_passe)
    cible.save(update_fields=["password"])
    profil, _ = UserProfile.objects.get_or_create(user=cible)
    profil.mot_de_passe_provisoire = True
    profil.mot_de_passe_provisoire_expire_le = timezone.now() + timedelta(hours=settings.DUREE_MOT_DE_PASSE_PROVISOIRE_HEURES)
    profil.save(update_fields=["mot_de_passe_provisoire", "mot_de_passe_provisoire_expire_le"])
    AuditLog.objects.create(
        actor=acteur, action="reinitialisation_mot_de_passe", target_user=cible,
        details=f"mot de passe provisoire généré, valide jusqu'au {profil.mot_de_passe_provisoire_expire_le:%d/%m/%Y %H:%M}",
    )
    from notifications.models import Notification, NotificationLevel
    Notification.objects.create(
        user=cible, verb="Votre mot de passe a été réinitialisé : choisissez-en un nouveau à la prochaine connexion.",
        level=NotificationLevel.WARNING, categorie="securite",
    )
    return mot_de_passe
