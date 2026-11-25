"""Réinitialisation du mot de passe d'un marin par l'administrateur du bâtiment (sans messagerie à bord)."""
import secrets
import string

from django.core.exceptions import PermissionDenied

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from matrix.core.role_thresholds import niveau_pour_action, niveau_requis_pour
from matrix.core.roles import ROLE_TO_LEVEL, RoleLevel, est_administrateur_technique
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


# Niveaux de protection d'un compte face à la réinitialisation de son mot de passe (AC-12). Le plus élevé l'emporte.
PROTECTION_TECHNIQUE = 1  # administrateur technique du bâtiment : équipier à chef de service sans autre autorité
PROTECTION_GENERALE = 2  # administrateur général : autorités du bâtiment, administrateurs techniques, désignations
PROTECTION_RECUPERATION = 3  # administrateur général Matrix, superutilisateur : procédure de récupération


def niveaux_de_protection(comptes):
    """{identifiant: niveau de protection} pour une liste de comptes, d'après le rôle ET les habilitations et désignations
    effectives (quelques requêtes quel que soit le nombre de comptes). Le niveau le plus élevé l'emporte."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    ids = [c.pk for c in comptes]
    profils = {p["user_id"]: p for p in UserProfile.objects.filter(user_id__in=ids).values(
        "user_id", "role", "administrateur_technique", "fonction_coma")}
    drapeaux = {u["pk"]: u for u in User.objects.filter(pk__in=ids).values("pk", "is_superuser", "is_staff")}
    avec_droits = set(User.objects.filter(pk__in=ids, groups__isnull=False).values_list("pk", flat=True))
    avec_droits |= set(User.objects.filter(pk__in=ids, user_permissions__isnull=False).values_list("pk", flat=True))
    designes = set()
    for relation in DESIGNATIONS:
        designes |= set(User.objects.filter(pk__in=ids, **{f"{relation}__isnull": False}).values_list("pk", flat=True))
    resultat = {}
    for pk in ids:
        profil, compte = profils.get(pk, {}), drapeaux.get(pk, {})
        role = profil.get("role", "")
        if compte.get("is_superuser") or role == "MASTER_ADMIN":
            resultat[pk] = PROTECTION_RECUPERATION
        elif (
            ROLE_TO_LEVEL.get(role, RoleLevel.EQUIPIER) >= RoleLevel.ETAT_MAJOR or profil.get("administrateur_technique")
            or profil.get("fonction_coma") or compte.get("is_staff") or pk in avec_droits or pk in designes
        ):
            resultat[pk] = PROTECTION_GENERALE
        else:
            resultat[pk] = PROTECTION_TECHNIQUE
    return resultat


def niveau_de_protection(cible):
    return niveaux_de_protection([cible])[cible.pk]


def niveau_de_competence(acteur):
    """Plus haut niveau de protection qu'un acteur peut réinitialiser."""
    if not peut_reinitialiser(acteur):
        return 0
    if is_master_admin(acteur):
        return PROTECTION_GENERALE
    return PROTECTION_TECHNIQUE if est_administrateur_technique(acteur) else 0


def peut_reinitialiser_cible(acteur, cible):
    return acteur.pk != cible.pk and niveau_de_protection(cible) <= niveau_de_competence(acteur)


def reinitialiser_mot_de_passe(acteur, cible, verifie=False):
    """Définit un mot de passe provisoire que le marin devra changer ; le renvoie une seule fois.

    L'appelant a déjà borné `cible` au périmètre navire de l'acteur (et, avec `verifie`, au niveau de protection). Le mot de passe n'est ni enregistré en clair ni écrit
    dans le journal d'audit ; il expire (`DUREE_MOT_DE_PASSE_PROVISOIRE_HEURES`), les sessions ouvertes du compte sont
    invalidées par le changement de mot de passe et le titulaire est notifié."""
    if not verifie and not peut_reinitialiser_cible(acteur, cible):
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
