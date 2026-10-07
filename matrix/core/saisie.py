"""Lecture défensive des paramètres de requête."""
from datetime import datetime

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
