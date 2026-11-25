"""Réinitialisation du mot de passe d'un marin par l'administrateur du bâtiment (sans messagerie à bord)."""
import secrets
import string

from django.core.exceptions import PermissionDenied

from matrix.core.role_thresholds import niveau_pour_action, niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
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


def peut_reinitialiser_cible(acteur, cible):
    return peut_reinitialiser(acteur) and acteur.pk != cible.pk and _reinitialisable_par_technique(acteur, cible)


def _reinitialisable_par_technique(acteur, cible):
    """Un administrateur technique sans autorité métier ne reprend pas le compte d'une autorité : au-delà de chef de section,
    ou d'un autre administrateur technique, la réinitialisation revient à l'administrateur général."""
    if is_master_admin(acteur) or user_role_level(acteur) >= RoleLevel.COMMANDANT:
        return True
    profil = getattr(cible, "profile", None)
    return (
        not cible.is_superuser and user_role_level(cible) <= RoleLevel.CHEF_SECTION
        and not cible.is_staff and not cible.groups.exists() and not cible.user_permissions.exists()
        and not (profil and (profil.administrateur_technique or profil.fonction_coma)) and not porte_une_designation(cible)
    )


# Désignations indépendantes du rôle : qui les porte exerce une autorité que le rôle ne montre pas.
DESIGNATIONS = (
    "designations_chef_de_liste", "redactions_feuille_service", "delegations_programme", "formations_referentes",
    "specialites_dont_il_est_responsable", "classes_navire_dont_il_est_responsable", "navires_brh",
    "navires_dont_il_est_referent_formation", "remplacements_chef_de_liste", "responsables_specialite_diriges",
)


def porte_une_designation(utilisateur):
    return any(getattr(utilisateur, relation).exists() for relation in DESIGNATIONS)


def reinitialiser_mot_de_passe(acteur, cible):
    """Définit un mot de passe provisoire que le marin devra changer ; le renvoie une seule fois.

    L'appelant a déjà borné `cible` au périmètre navire de l'acteur. Le mot de passe n'est ni
    enregistré en clair ni écrit dans le journal d'audit."""
    if not peut_reinitialiser_cible(acteur, cible):
        raise PermissionDenied
    mot_de_passe = generer_mot_de_passe()
    cible.set_password(mot_de_passe)
    cible.save(update_fields=["password"])
    profil, _ = UserProfile.objects.get_or_create(user=cible)
    profil.mot_de_passe_provisoire = True
    profil.save(update_fields=["mot_de_passe_provisoire"])
    AuditLog.objects.create(
        actor=acteur, action="reinitialisation_mot_de_passe", target_user=cible,
        details="mot de passe provisoire généré",
    )
    return mot_de_passe
