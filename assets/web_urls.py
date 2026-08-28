from django.urls import path
from .web_views import (
    AssetDetailView, StartVisualCheckView, AssetListView, InstallationListView,
    InstallationDetailView, ScanQRView, AssetImportView, AssetImportModeleView,
    PlanNavireListView, PlanNavireDeckView, PlanNavireVueView, PlanNavireVueDeckView,
)

urlpatterns = [
    path('assets/', AssetListView.as_view(), name='asset-list'),
    path('assets/importer/', AssetImportView.as_view(), name='asset-import'),
    path('assets/importer/modele/', AssetImportModeleView.as_view(), name='asset-import-modele'),
    path('assets/<uuid:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('assets/<uuid:pk>/start-visual/', StartVisualCheckView.as_view(), name='asset-start-visual'),
    path('installations/', InstallationListView.as_view(), name='installation-list'),
    path('installations/<uuid:pk>/', InstallationDetailView.as_view(), name='installation-detail'),
    # Scan QR : point d'entrée unique pour matériel mobile ET installation fixe
    # (même UUID, ScanQRView résout le bon modèle).
    path('scan/<uuid:pk>/', ScanQRView.as_view(), name='scan-qr'),
    # Plan visuel du navire : configuration des ponts et de leurs zones cliquables
    # (réservée CHEF_SERVICE+, cf. PlanNavireListView/PlanNavireDeckView).
    path('assets/plan/', PlanNavireListView.as_view(), name='plan-navire-list'),
    path('assets/plan/<int:pk>/', PlanNavireDeckView.as_view(), name='plan-navire-deck'),
    # Plan visuel du navire : consultation en lecture seule, ouverte à tous les
    # rôles (cf. PlanNavireVueView/PlanNavireVueDeckView) — sous-tâche 3/3.
    path('assets/plan-navire/', PlanNavireVueView.as_view(), name='plan-navire-vue'),
    path('assets/plan-navire/<int:pk>/', PlanNavireVueDeckView.as_view(), name='plan-navire-vue-deck'),
]
