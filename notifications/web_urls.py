from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.centre, name="notifications-centre"),
    path("centre/tout-lu/", web_views.tout_lu_centre, name="notifications-centre-tout-lu"),
    path("centre/<int:pk>/lue/", web_views.lue_centre, name="notifications-centre-lue"),
    path("panneau/", web_views.panneau, name="notifications-panneau"),
    path("compteur/", web_views.compteur, name="notifications-compteur"),
    path("tout-lu/", web_views.tout_marquer_lu, name="notifications-tout-lu"),
    path("<int:pk>/lue/", web_views.marquer_lue, name="notifications-lue"),
]
