"""Balises de bloc des composants (docs/UX.md §5.1, §14 et §26).

Syntaxe : ``{% surface titre="Titre" icone="maintenance" %}...{% fin_surface %}``.
Le contenu du bloc est transmis au gabarit ``components/<nom>.html`` sous le
nom ``contenu``. Les mêmes gabarits restent utilisables avec
``{% include "components/surface.html" with titre="..." contenu=... %}``.
Niveaux d'interaction : ``modale``, ``panneau_lateral``, ``menu_contextuel``,
``assistant`` et ``grille`` (saisie en série, UX-0.5). Les composants sans contenu libre (metric, badge_etat, jauge,
etat_vide, popover, menu_item) se règlent uniquement par ``{% include %}``.
"""
from django import template
from django.template.base import token_kwargs
from django.template.loader import get_template

register = template.Library()


@register.filter
def pourcentage(valeur):
    """Entier borné à 0-100 ; toute valeur non numérique donne 0."""
    try:
        return max(0, min(100, int(float(valeur))))
    except (TypeError, ValueError, OverflowError):
        return 0


@register.filter
def valeur_cellule(ligne, nom):
    """Valeur saisie d'une cellule de grille (chaîne vide si absente)."""
    valeur = (ligne.get("valeurs") or {}).get(nom, "")
    return "" if valeur is None else valeur


@register.filter
def initiale_liste(valeur, choix):
    """Valeur réellement affichée par une liste : vide si elle n'est pas parmi les choix."""
    return valeur if any(c.get("valeur") == valeur for c in choix) else ""


@register.filter
def erreur_cellule(ligne, nom):
    """Message d'erreur d'une cellule de grille (chaîne vide si aucune)."""
    return (ligne.get("erreurs") or {}).get(nom, "")


# Choix par défaut d'une colonne de conformité de la grille.
CHOIX_CONFORMITE = [
    {"valeur": "conforme", "libelle": "Conforme"},
    {"valeur": "non_conforme", "libelle": "Non conforme"},
]


class _NoeudComposant(template.Node):
    def __init__(self, gabarit, parametres, corps, defauts=None):
        self.gabarit = gabarit
        self.parametres = parametres
        self.corps = corps
        self.defauts = defauts or {}

    def render(self, context):
        valeurs = dict(self.defauts)
        valeurs.update({cle: expr.resolve(context) for cle, expr in self.parametres.items()})
        valeurs["contenu"] = self.corps.render(context)
        return get_template(self.gabarit).render(valeurs)


def _declarer(nom):
    @register.tag(nom)
    def compiler(parser, token):
        elements = token.split_contents()[1:]
        parametres = token_kwargs(elements, parser)
        if elements:
            raise template.TemplateSyntaxError(
                f"« {nom} » n'accepte que des paramètres nommés (cle=valeur)."
            )
        corps = parser.parse((f"fin_{nom}",))
        parser.delete_first_token()
        defauts = {"choix_conformite": CHOIX_CONFORMITE} if nom == "grille" else None
        return _NoeudComposant(f"components/{nom}.html", parametres, corps, defauts)

    return compiler


for _nom in ("surface", "carte_interactive", "carte_action", "attention", "modale", "panneau_lateral", "menu_contextuel", "assistant", "grille"):
    _declarer(_nom)
