from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.DemandesIndexView.as_view(), name="demandes-index"),
    path("nouvelle/", web_views.DemandeNouvelleView.as_view(), name="demande-nouvelle"),
    path("<int:pk>/", web_views.DemandeDetailView.as_view(), name="demande-detail"),
    path("<int:pk>/action/", web_views.DemandeActionView.as_view(), name="demande-action"),
    path("<int:pk>/commentaire/", web_views.DemandeCommentaireView.as_view(), name="demande-commentaire"),
]
