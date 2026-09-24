from django.urls import path

from .web_views import (
    ChefDeListeReglagesView,
    EchangeActionView,
    EchangesIndexView,
    FeuilleServiceDetailView,
    FeuilleServiceIndexView,
    FeuilleServiceReglagesView,
    ListeIndexView,
    ProposerEchangeView,
    QuartDetailView,
    ServiceGardeDetailView,
)

urlpatterns = [
    path("", ListeIndexView.as_view(), name="quarts-index"),
    path("reglages/", ChefDeListeReglagesView.as_view(), name="quarts-reglages"),
    path("quart/<int:pk>/", QuartDetailView.as_view(), name="quart-detail"),
    path("garde/<int:pk>/", ServiceGardeDetailView.as_view(), name="garde-detail"),
    path("garde/<int:pk>/echanges/proposer/", ProposerEchangeView.as_view(), name="echange-proposer"),
    path("echanges/", EchangesIndexView.as_view(), name="echanges-index"),
    path("echanges/<int:pk>/<str:action>/", EchangeActionView.as_view(), name="echange-action"),
    path("feuille-service/", FeuilleServiceIndexView.as_view(), name="feuille-service-index"),
    path("feuille-service/reglages/", FeuilleServiceReglagesView.as_view(), name="feuille-service-reglages"),
    path(
        "feuille-service/<int:ship_id>/<str:date_str>/",
        FeuilleServiceDetailView.as_view(),
        name="feuille-service-detail",
    ),
]
