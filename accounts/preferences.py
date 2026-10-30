"""Préférences d'interface par marin (groupes du menu, aides vues), stockées sur le profil.

Liste blanche stricte : ce ne sont que des préférences d'affichage, jamais un contrôle d'accès.
"""
import hashlib
import json
import re

from django.db import transaction

from matrix.core.navigation import GROUPES

from .models import UserProfile

MENU_GROUPES, AIDES_VUES = "menu_groupes", "aides_vues"
AIDES_CONNUES = ("acces",)
TAILLE_MAX = 2048
_SIGNATURE = re.compile(r"[0-9a-f]{12}")


def signature_droits(user, a_terre, soutien):
    """Empreinte du contexte d'autorisation : change avec le rôle, l'équipage ou le passage à terre."""
    profil = getattr(user, "profile", None)
    elements = (
        profil.role if profil else "",
        profil.equipage if profil else "",
        profil.ship_id if profil else None,
        bool(user.is_superuser),
        bool(a_terre),
        bool(soutien),
    )
    return hashlib.sha256(json.dumps(elements).encode()).hexdigest()[:12]


def lire(user):
    profil = getattr(user, "profile", None)
    brut = profil.preferences_interface if profil else {}
    return brut if isinstance(brut, dict) else {}


def aide_vue(user, aide, signature):
    """Vrai si l'aide a été refermée pour le contexte d'autorisation actuel."""
    return lire(user).get(AIDES_VUES, {}).get(aide) == signature


def groupe_ouvert(user, titre, defaut):
    return lire(user).get(MENU_GROUPES, {}).get(titre, defaut)


def _valider(cle, sous_cle, valeur):
    """(sous-clé, valeur à stocker ou None pour supprimer) ; ValueError si hors liste blanche."""
    if cle == MENU_GROUPES:
        if sous_cle not in {titre for titre, _ in GROUPES} or valeur not in ("0", "1"):
            raise ValueError("groupe ou valeur inconnus")
        return sous_cle, valeur == "1"
    if cle == AIDES_VUES:
        if sous_cle not in AIDES_CONNUES:
            raise ValueError("aide inconnue")
        if valeur == "":
            return sous_cle, None
        if not _SIGNATURE.fullmatch(valeur):
            raise ValueError("signature invalide")
        return sous_cle, valeur
    raise ValueError("préférence inconnue")


def enregistrer(user, cle, sous_cle, valeur):
    """Fusionne une seule valeur sous verrou de ligne : un poste n'efface pas les réglages d'un autre."""
    sous_cle, stockee = _valider(cle, sous_cle, valeur)
    with transaction.atomic():
        profil, _ = UserProfile.objects.select_for_update().get_or_create(user=user)
        prefs = profil.preferences_interface if isinstance(profil.preferences_interface, dict) else {}
        section = dict(prefs.get(cle, {}))
        if stockee is None:
            section.pop(sous_cle, None)
        else:
            section[sous_cle] = stockee
        prefs = {**prefs, cle: section}
        if len(json.dumps(prefs)) > TAILLE_MAX:
            raise ValueError("préférences trop volumineuses")
        profil.preferences_interface = prefs
        profil.save(update_fields=["preferences_interface", "updated_at"])
