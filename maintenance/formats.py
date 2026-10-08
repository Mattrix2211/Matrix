"""Lecture et affichage des champs date et heure des formulaires de compte rendu."""
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def valeur_datetime(valeur):
    """Valeur d'un champ datetime-local (heure locale, sans secondes)."""
    return timezone.localtime(valeur).strftime("%Y-%m-%dT%H:%M") if valeur else ""


def lire_datetime(texte):
    """(datetime, erreur) depuis un champ datetime-local ; vide : (None, None)."""
    texte = (texte or "").strip()
    if not texte:
        return None, None
    try:
        valeur = parse_datetime(texte)
    except ValueError:
        valeur = None
    if valeur is None or not 2000 <= valeur.year <= 2100:
        return None, "Date ou heure illisible."
    return (timezone.make_aware(valeur) if timezone.is_naive(valeur) else valeur), None
