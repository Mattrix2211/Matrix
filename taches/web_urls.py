from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.TachesIndexView.as_view(), name="taches-index"),
    path("<int:pk>/", web_views.TacheDetailView.as_view(), name="tache-detail"),
    path("<int:pk>/action/", web_views.TacheActionView.as_view(), name="tache-action"),
    path("commentaire/<int:pk>/", web_views.TacheCommentaireView.as_view(), name="tache-commentaire"),
]
