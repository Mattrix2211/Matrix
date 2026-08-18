"""Filtres de template pour l'arbre de compétences : repère visuel quand un
prérequis appartient à une catégorie (domaine métier) différente de la
formation affichée, la vue le regroupant par catégorie (cf. training/services.py)."""
from django import template

from training.services import CATEGORIE_NON_RENSEIGNEE

register = template.Library()


@register.filter
def autre_categorie(prerequis, formation):
    """Vrai si `prerequis` appartient à une catégorie différente de celle de
    `formation` — sert à afficher un badge/lien vers la catégorie du
    prérequis dans l'arbre de compétences, pour ne pas perdre le fil quand la
    chaîne de prérequis traverse plusieurs domaines métier."""
    return (prerequis.category or "").strip() != (formation.category or "").strip()


@register.filter
def categorie_affichee(categorie):
    """Libellé affiché pour une catégorie de formation : le texte saisi, ou
    "Non catégorisées" si aucune catégorie n'a été renseignée."""
    categorie = (categorie or "").strip()
    return categorie or CATEGORIE_NON_RENSEIGNEE
