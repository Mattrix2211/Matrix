from rest_framework.routers import DefaultRouter
from .views import (
    LocationViewSet, AssetTypeViewSet, ChecklistTemplateViewSet, ChecklistItemTemplateViewSet,
    AssetViewSet, AssetDocumentViewSet, AssetChecklistOverrideViewSet
)

router = DefaultRouter()
router.register(r'locations', LocationViewSet)
router.register(r'types', AssetTypeViewSet)
router.register(r'checklist-templates', ChecklistTemplateViewSet)
router.register(r'checklist-items', ChecklistItemTemplateViewSet)
router.register(r'assets', AssetViewSet)
router.register(r'asset-docs', AssetDocumentViewSet)
router.register(r'asset-checklist-overrides', AssetChecklistOverrideViewSet)

urlpatterns = router.urls
