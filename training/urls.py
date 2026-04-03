from rest_framework.routers import DefaultRouter
from .views import TrainingCourseViewSet, TrainingRequirementViewSet, TrainingSessionViewSet, TrainingRecordViewSet

router = DefaultRouter()
router.register(r'courses', TrainingCourseViewSet)
router.register(r'requirements', TrainingRequirementViewSet)
router.register(r'sessions', TrainingSessionViewSet)
router.register(r'records', TrainingRecordViewSet)

urlpatterns = router.urls
