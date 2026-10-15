"""Lecture défensive des paramètres de requête."""
from datetime import datetime

from uuid import UUID

from django.core.exceptions import BadRequest, ValidationError
from django.db import models
from django.utils.text import capfirst

ENTIER_MAX = 2**63 - 1  # borne des clés primaires entières


def entier_ou_none(valeur):
    """Entier positif lu depuis du texte, ou None (chiffres exposants et valeurs trop grandes refusés)."""
    texte = str(valeur or "").strip()
    if not (texte.isascii() and texte.isdigit()):
        return None
    nombre = int(texte)
    return nombre if nombre <= ENTIER_MAX else None


def uuid_ou_none(valeur):
    """UUID lu depuis du texte, ou None."""
    try:
        return UUID(str(valeur or "").strip())
    except ValueError:
        return None


def entiers_valides(valeurs):
    """Les seuls identifiants entiers valides d'une liste de textes postés."""
    return [n for n in map(entier_ou_none, valeurs) if n is not None]


def uuids_valides(valeurs):
    """Les seuls UUID valides d'une liste de textes postés."""
    return [u for u in map(uuid_ou_none, valeurs) if u]


def identifiant_d_url(valeur):
    """Identifiant d'un filtre d'URL : None s'il est vide, requête refusée (400) s'il n'est pas un entier."""
    if not valeur:
        return None
    nombre = entier_ou_none(valeur)
    if nombre is None:
        raise BadRequest("Identifiant invalide.")
    return nombre


def date_fr_ou_none(valeur):
    """Date saisie au format jj/mm/aaaa ; None si vide, ValueError si mal formée."""
    texte = str(valeur or "").strip()
    return datetime.strptime(texte, "%d/%m/%Y").date() if texte else None


def formater_date_fr(date):
    """jj/mm/aaaa, ou texte vide si la date est absente."""
    return date.strftime("%d/%m/%Y") if date else ""


def sans_nul(texte):
    """Texte débarrassé des caractères NUL, que PostgreSQL refuse (erreur serveur sinon)."""
    return str(texte or "").replace("\x00", "")


def _depassements(modele, valeurs):
    erreurs = {}
    for nom, valeur in valeurs.items():
        champ = modele._meta.get_field(nom)
        if isinstance(champ, models.CharField) and isinstance(valeur, str) and len(valeur) > champ.max_length:
            erreurs[nom] = f"« {capfirst(str(champ.verbose_name))} » est limité à {champ.max_length} caractères ({len(valeur)} saisis)."
    return erreurs


def verifier_longueurs(modele, **valeurs):
    """Refuse en français un texte plus long que sa colonne : PostgreSQL le rejette (erreur 500), SQLite l'accepte."""
    erreurs = _depassements(modele, valeurs)
    if erreurs:
        raise ValidationError({nom: [message] for nom, message in erreurs.items()})


def message_longueurs(modele, **valeurs):
    """Comme verifier_longueurs, pour une vue qui affiche un message : texte vide si tout est dans la limite."""
    return " ".join(_depassements(modele, valeurs).values())
