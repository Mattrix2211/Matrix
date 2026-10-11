from django.urls import path

from . import web_views

urlpatterns = [
    path("", web_views.ProgrammeIndexView.as_view(), name="programme-index"),
    path("nouveau/", web_views.EvenementNouveauView.as_view(), name="evenement-nouveau"),
    path("reglages/", web_views.ProgrammeReglagesView.as_view(), name="programme-reglages"),
    path("<int:pk>/", web_views.EvenementDetailView.as_view(), name="evenement-detail"),
    path("<int:pk>/action/", web_views.EvenementActionView.as_view(), name="evenement-action"),
]
