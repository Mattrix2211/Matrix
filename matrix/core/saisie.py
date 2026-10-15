"""Lecture défensive des paramètres de requête."""
from datetime import datetime

from django.core.exceptions import ValidationError
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


def verifier_longueurs(modele, **valeurs):
    """Refuse en français un texte plus long que sa colonne : PostgreSQL le rejette (erreur 500), SQLite l'accepte."""
    erreurs = {}
    for nom, valeur in valeurs.items():
        champ = modele._meta.get_field(nom)
        if isinstance(champ, models.CharField) and isinstance(valeur, str) and len(valeur) > champ.max_length:
            erreurs[nom] = [f"« {capfirst(str(champ.verbose_name))} » est limité à {champ.max_length} caractères ({len(valeur)} saisis)."]
    if erreurs:
        raise ValidationError(erreurs)
