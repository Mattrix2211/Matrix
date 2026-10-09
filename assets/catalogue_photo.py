"""Contrôle des photos du catalogue (formulaires et API) : jamais de HTML ni de SVG servi en ligne."""
import os

from django.core.exceptions import ValidationError

EXTENSIONS_PHOTO = (".jpg", ".jpeg", ".png", ".webp")
TAILLE_PHOTO_MAX = 5 * 1024 * 1024


def valider_photo(fichier):
    """Refuse extension hors liste blanche, fichier trop lourd ou contenu qui n'est pas une image."""
    if not fichier or not hasattr(fichier, "size"):
        return fichier
    if os.path.splitext(fichier.name)[1].lower() not in EXTENSIONS_PHOTO:
        raise ValidationError("Format d'image refusé : utilisez JPEG, PNG ou WebP.")
    if fichier.size > TAILLE_PHOTO_MAX:
        raise ValidationError(f"Image trop lourde (maximum {TAILLE_PHOTO_MAX // (1024 * 1024)} Mo).")
    try:
        from PIL import Image
    except ImportError:
        return fichier
    try:
        Image.open(fichier).verify()
    except Exception:
        raise ValidationError("Le fichier n'est pas une image valide.")
    finally:
        fichier.seek(0)
    return fichier
