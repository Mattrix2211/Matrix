"""Contrôle des documents téléversés (plans, notices...) : liste blanche, taille et signature du contenu.
Jamais de HTML, SVG ou script accepté."""
import os

from django.conf import settings
from django.core.exceptions import ValidationError

# Signatures de début de fichier par extension ; absente = pas de contrôle (texte brut).
SIGNATURES = {
    ".pdf": (b"%PDF",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".webp": (b"RIFF",),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
}
EXTENSIONS_DOCUMENT = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".docx", ".xlsx")


def taille_document_max():
    """Taille maximale en octets (réglage DOCUMENT_TAILLE_MAX_MO, 20 Mo par défaut)."""
    return getattr(settings, "DOCUMENT_TAILLE_MAX_MO", 20) * 1024 * 1024


def valider_document(fichier):
    """Refuse une extension hors liste blanche, un fichier trop lourd ou dont le contenu ne correspond pas."""
    extension = os.path.splitext(fichier.name)[1].lower()
    if extension not in EXTENSIONS_DOCUMENT:
        raise ValidationError("Format refusé : PDF, image (PNG, JPEG, WebP), texte, Word ou Excel uniquement.")
    if fichier.size > taille_document_max():
        raise ValidationError(f"Fichier trop lourd (maximum {taille_document_max() // (1024 * 1024)} Mo).")
    signatures = SIGNATURES.get(extension)
    if signatures:
        debut = fichier.read(16)
        fichier.seek(0)
        if not debut.startswith(signatures):
            raise ValidationError("Le contenu du fichier ne correspond pas à son extension.")
    return fichier
