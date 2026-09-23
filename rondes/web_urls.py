from django.urls import path

from .web_views import (
    LancerRondeView, ModeleFormView, ModeleListView, PointActionView, ResultatView,
    RondeDetailView, RondesIndexView, TerminerRondeView,
)

urlpatterns = [
    path("", RondesIndexView.as_view(), name="rondes-index"),
    path("modeles/", ModeleListView.as_view(), name="ronde-modeles"),
    path("modeles/nouveau/", ModeleFormView.as_view(), name="ronde-modele-nouveau"),
    path("modeles/<int:pk>/", ModeleFormView.as_view(), name="ronde-modele"),
    path("modeles/<int:pk>/lancer/", LancerRondeView.as_view(), name="ronde-lancer"),
    path("modeles/<int:pk>/points/<str:action>/", PointActionView.as_view(), name="ronde-point-ajouter"),
    path("modeles/<int:pk>/points/<int:point_pk>/<str:action>/", PointActionView.as_view(), name="ronde-point"),
    path("<int:pk>/", RondeDetailView.as_view(), name="ronde-detail"),
    path("<int:pk>/points/<int:resultat_pk>/", ResultatView.as_view(), name="ronde-resultat"),
    path("<int:pk>/terminer/", TerminerRondeView.as_view(), name="ronde-terminer"),
]
