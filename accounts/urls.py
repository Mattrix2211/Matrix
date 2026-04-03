from rest_framework.routers import DefaultRouter
from .views import (
	UserViewSet,
	UserProfileViewSet,
	GradeChoiceViewSet,
	SpecialityChoiceViewSet,
	RoleAvailabilityViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'profiles', UserProfileViewSet)
router.register(r'grades', GradeChoiceViewSet)
router.register(r'specialities', SpecialityChoiceViewSet)
router.register(r'role-availability', RoleAvailabilityViewSet)

urlpatterns = router.urls
