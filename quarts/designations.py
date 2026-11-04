"""Désignations historiques de chef de liste (sans type) : repérage des cas ambigus à faire préciser."""
from quarts.models import ChefDeListe, Quart, ServiceGarde


def usage_du_perimetre(cdl):
    """Nombre de listes de quarts et de services à quai posées sur le périmètre exact de la désignation."""
    cible = dict(ship_id=cdl.ship_id, service_id=cdl.service_id, sector_id=cdl.sector_id, section_id=cdl.section_id)
    return Quart.objects.filter(**cible).count(), ServiceGarde.objects.filter(**cible).count()


def situation(cdl):
    """AMBIGUE si le périmètre porte les deux familles de listes ; sinon indication d'usage (jamais d'attribution automatique)."""
    quarts, gardes = usage_du_perimetre(cdl)
    if quarts and gardes:
        return "AMBIGUE"
    if quarts:
        return "QUARTS_SEULEMENT"
    if gardes:
        return "QUAI_SEULEMENT"
    return "SANS_LISTE"


LIBELLES = {
    "AMBIGUE": "Ambiguë : le niveau porte des quarts et des services à quai",
    "QUARTS_SEULEMENT": "Usage constaté : quarts à la mer seulement",
    "QUAI_SEULEMENT": "Usage constaté : services à quai seulement",
    "SANS_LISTE": "Aucune liste sur ce niveau",
}


def designations_historiques():
    return ChefDeListe.objects.filter(type_liste="").select_related("user", "ship", "service", "sector", "section")
