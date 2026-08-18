from django.urls import path
from .web_views import AssetDetailView, StartVisualCheckView, AssetListView, LocationListView, InstallationListView, InstallationDetailView, ScanQRView

urlpatterns = [
    path('assets/', AssetListView.as_view(), name='asset-list'),
    path('assets/<uuid:pk>/', AssetDetailView.as_view(), name='asset-detail'),
    path('assets/<uuid:pk>/start-visual/', StartVisualCheckView.as_view(), name='asset-start-visual'),
    path('locations/', LocationListView.as_view(), name='location-list'),
    path('installations/', InstallationListView.as_view(), name='installation-list'),
    path('installations/<uuid:pk>/', InstallationDetailView.as_view(), name='installation-detail'),
    # Scan QR : point d'entrée unique pour matériel mobile ET installation fixe
    # (même UUID, ScanQRView résout le bon modèle).
    path('scan/<uuid:pk>/', ScanQRView.as_view(), name='scan-qr'),
]
