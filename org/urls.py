from rest_framework.routers import DefaultRouter
from .views import ShipViewSet, ServiceViewSet, SectorViewSet, SectionViewSet, SectorConfigViewSet

router = DefaultRouter()
router.register(r'ships', ShipViewSet)
router.register(r'services', ServiceViewSet)
router.register(r'sectors', SectorViewSet)
router.register(r'sections', SectionViewSet)
router.register(r'sector-configs', SectorConfigViewSet)

urlpatterns = router.urls
