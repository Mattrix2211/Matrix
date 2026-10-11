from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.AnnoncesIndexView.as_view(), name="annonces-index"),
    path("nouvelle/", web_views.AnnonceNouvelleView.as_view(), name="annonce-nouvelle"),
    path("<int:pk>/", web_views.AnnonceDetailView.as_view(), name="annonce-detail"),
    path("<int:pk>/action/", web_views.AnnonceActionView.as_view(), name="annonce-action"),
]
