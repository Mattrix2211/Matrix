from django.urls import path

from .web_views import (
    HistoriqueAppareillageView,
    ItemAppareillageCocherView,
    PretAppareillageView,
    SessionAppareillageDetailView,
    SessionAppareillageOuvrirView,
    SessionAppareillageSignerView,
    VueFlotteView,
)

urlpatterns = [
    path("flotte/", VueFlotteView.as_view(), name="vue-flotte"),
    path("pret-appareillage/", PretAppareillageView.as_view(), name="pret-appareillage"),
    path("pret-appareillage/ouvrir/", SessionAppareillageOuvrirView.as_view(), name="session-appareillage-ouvrir"),
    path(
        "pret-appareillage/session/<int:pk>/signer/",
        SessionAppareillageSignerView.as_view(),
        name="session-appareillage-signer",
    ),
    path(
        "pret-appareillage/session/<int:pk>/",
        SessionAppareillageDetailView.as_view(),
        name="session-appareillage-detail",
    ),
    path(
        "pret-appareillage/item/<int:pk>/cocher/",
        ItemAppareillageCocherView.as_view(),
        name="item-appareillage-cocher",
    ),
    path("pret-appareillage/historique/", HistoriqueAppareillageView.as_view(), name="historique-appareillage"),
]
