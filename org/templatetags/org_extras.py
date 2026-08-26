"""Filtres et tags de gabarit pour l'app org (unités et hiérarchie).

Tâche Notion « [FEAT] Modéliser un organisme de formation comme une unité
dédiée » : un organisme de formation (école, centre de formation) est une
Ship/« Unité » comme une autre (type_unite=ECOLE ou CENTRE_FORMATION). Ces
outils permettent de repérer visuellement le type d'une unité dans les
listes/sélecteurs (principe « priorité au visuel », CLAUDE.md) sans jamais
exclure une unité d'un sélecteur : un marin peut légitimement être rattaché
à une école, un centre de formation ou un bureau à terre, exactement comme
à un navire (voir raisonnement détaillé dans le commentaire Notion de la
tâche)."""
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

from org.models import Ship

register = template.Library()

# Icône Bootstrap Icons + couleur de badge Bootstrap par type d'unité.
_ICONES_TYPE_UNITE = {
    Ship.TypeUnite.NAVIRE: ("bi-water", "bg-primary"),
    Ship.TypeUnite.ECOLE: ("bi-mortarboard-fill", "bg-warning text-dark"),
    Ship.TypeUnite.CENTRE_FORMATION: ("bi-easel", "bg-info text-dark"),
    Ship.TypeUnite.BUREAU: ("bi-building", "bg-secondary"),
}


@register.filter
def badge_type_unite(unite):
    """Badge Bootstrap (icône + libellé) selon le type de l'unité fournie."""
    if not unite:
        return ""
    icone, couleur = _ICONES_TYPE_UNITE.get(unite.type_unite, ("bi-question-circle", "bg-secondary"))
    libelle = escape(unite.get_type_unite_display())
    return mark_safe(
        f'<span class="badge {couleur}"><span class="bi {icone} me-1" aria-hidden="true"></span>{libelle}</span>'
    )


@register.simple_tag
def unites_groupees_par_type(unites):
    """Regroupe une liste/queryset d'unités par type_unite, dans l'ordre
    Navire / École / Centre de formation / Bureau, pour construire des
    <optgroup> lisibles dans les sélecteurs. Ne filtre ni n'exclut aucune
    unité : toutes restent sélectionnables, seul l'affichage est groupé."""
    ordre = [code for code, _ in Ship.TypeUnite.choices]
    libelles = dict(Ship.TypeUnite.choices)
    groupes = {code: [] for code in ordre}
    for unite in unites:
        groupes.setdefault(unite.type_unite, []).append(unite)
    return [(libelles[code], groupes[code]) for code in ordre if groupes.get(code)]
