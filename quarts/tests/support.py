"""Aides de test : désignations de chef de liste explicitement qualifiées."""
from quarts.models import ChefDeListe


def designer_chef(user, **perimetre):
    """Chef de liste des deux types (quarts à la mer et services à quai) pour un périmètre : cas général des tests.
    Renvoie la désignation des quarts. Une désignation sans type ne donne plus aucun droit."""
    quarts = ChefDeListe.objects.create(user=user, type_liste=ChefDeListe.TYPE_QUARTS, **perimetre)
    ChefDeListe.objects.create(user=user, type_liste=ChefDeListe.TYPE_QUAI, **perimetre)
    return quarts
