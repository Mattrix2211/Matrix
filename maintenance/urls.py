from rest_framework.routers import DefaultRouter
from .views import MaintenancePlanViewSet, MaintenanceOccurrenceViewSet, MaintenanceExecutionViewSet

router = DefaultRouter()
router.register(r'plans', MaintenancePlanViewSet)
router.register(r'occurrences', MaintenanceOccurrenceViewSet)
router.register(r'executions', MaintenanceExecutionViewSet)

urlpatterns = router.urls
