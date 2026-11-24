"""URLconf d'essai : le vrai site plus deux routes volontairement mal protégées, pour vérifier que le dispositif les détecte."""
from django.http import HttpResponse
from django.urls import path

from matrix.urls import urlpatterns as urlpatterns_site


def vue_ouverte(request):
    return HttpResponse("donnée sensible fictive")


urlpatterns = [*urlpatterns_site, path("piege/ouvert/", vue_ouverte), path("quarts/piege-ouvert/", vue_ouverte)]
