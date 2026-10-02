"""Balises de bloc des composants « cards » (docs/UX.md §14 et §26).

Syntaxe : ``{% surface titre="Titre" icone="maintenance" %}...{% fin_surface %}``.
Le contenu du bloc est transmis au gabarit ``components/<nom>.html`` sous le
nom ``contenu``. Les mêmes gabarits restent utilisables avec
``{% include "components/surface.html" with titre="..." contenu=... %}``.
Les composants sans contenu libre (metric, badge_etat, jauge, etat_vide) se
règlent uniquement par ``{% include %}``.
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


class _NoeudComposant(template.Node):
    def __init__(self, gabarit, parametres, corps):
        self.gabarit = gabarit
        self.parametres = parametres
        self.corps = corps

    def render(self, context):
        valeurs = {cle: expr.resolve(context) for cle, expr in self.parametres.items()}
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
        return _NoeudComposant(f"components/{nom}.html", parametres, corps)

    return compiler


for _nom in ("surface", "carte_interactive", "carte_action", "attention"):
    _declarer(_nom)
