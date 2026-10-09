"""Balise de gabarit ``{% icone "concept" %}`` (table : matrix/core/icones.py)."""
from django import template
from django.utils.html import format_html

from matrix.core.icones import classe_icone

register = template.Library()


@register.simple_tag
def icone(concept, classes_supplementaires=""):
    """Rend l'icône du concept (décorative : le texte voisin porte le sens).

    Une icône seule doit recevoir par ailleurs un ``title`` et un ``aria-label``
    sur son élément parent (docs/UX.md §16).
    """
    classes = f"bi {classe_icone(concept)} {classes_supplementaires}".strip()
    return format_html('<i class="{}" aria-hidden="true"></i>', classes)
