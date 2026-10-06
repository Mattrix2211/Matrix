from django.urls import path

from . import web_views

urlpatterns = [
    path("panneau/", web_views.panneau, name="notifications-panneau"),
    path("compteur/", web_views.compteur, name="notifications-compteur"),
    path("tout-lu/", web_views.tout_marquer_lu, name="notifications-tout-lu"),
    path("<int:pk>/lue/", web_views.marquer_lue, name="notifications-lue"),
]
