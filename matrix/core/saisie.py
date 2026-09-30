"""Lecture sûre des valeurs saisies (paramètres d'adresse, champs de formulaire)."""


def entier_ou_none(valeur):
    """Entier décimal ASCII contenu dans `valeur`, sinon None.

    `str.isdigit()` accepte des chiffres Unicode comme « ² » : la conversion en
    entier échoue alors et provoque une erreur 500. Ici, seuls les chiffres
    0 à 9 sont acceptés."""
    texte = str(valeur if valeur is not None else "").strip()
    return int(texte) if texte.isascii() and texte.isdecimal() else None
