"""Réinitialisation du mot de passe d'un marin par l'administrateur du bâtiment (sans messagerie à bord)."""
import secrets
import string

from django.core.exceptions import PermissionDenied

from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import user_role_level

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
    return user_role_level(acteur) >= niveau_requis_pour(acteur, "mot_de_passe_reinitialisation")


def reinitialiser_mot_de_passe(acteur, cible):
    """Définit un mot de passe provisoire que le marin devra changer ; le renvoie une seule fois.

    L'appelant a déjà borné `cible` au périmètre navire de l'acteur. Le mot de passe n'est ni
    enregistré en clair ni écrit dans le journal d'audit."""
    if not peut_reinitialiser(acteur) or acteur.pk == cible.pk:
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
