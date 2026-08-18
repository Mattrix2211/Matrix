from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    LocationViewSet, AssetTypeViewSet, ChecklistTemplateViewSet, ChecklistItemTemplateViewSet,
    AssetViewSet, AssetDocumentViewSet, AssetChecklistOverrideViewSet,
    installation_qr_code, installation_qr_png,
)

router = DefaultRouter()
router.register(r'locations', LocationViewSet)
router.register(r'types', AssetTypeViewSet)
router.register(r'checklist-templates', ChecklistTemplateViewSet)
router.register(r'checklist-items', ChecklistItemTemplateViewSet)
router.register(r'assets', AssetViewSet)
router.register(r'asset-docs', AssetDocumentViewSet)
router.register(r'asset-checklist-overrides', AssetChecklistOverrideViewSet)

urlpatterns = router.urls + [
    # Génération QR pour les installations fixes : pas de ViewSet dédié pour
    # l'instant, deux vues simples suffisent (même principe que AssetViewSet.qr_code/qr_png).
    path('installations/<uuid:pk>/qr/', installation_qr_code, name='installation-qr'),
    path('installations/<uuid:pk>/qr_png/', installation_qr_png, name='installation-qr-png'),
]
