"""Contrôle des photos du catalogue (formulaires et API) : politique commune de matrix/core/validators.py."""
from matrix.core.validators import valider_photo_catalogue


def valider_photo(fichier):
    """Lève ValidationError si la photo est refusée ; renvoie le fichier (ou None s'il n'y en a pas)."""
    if not fichier or not hasattr(fichier, "size"):
        return fichier
    valider_photo_catalogue(fichier)
    return fichier
