from rest_framework.routers import DefaultRouter
from .views import CorrectiveTicketViewSet, PartRequestViewSet, PartLineItemViewSet

router = DefaultRouter()
router.register(r'tickets', CorrectiveTicketViewSet)
router.register(r'part-requests', PartRequestViewSet)
router.register(r'part-lines', PartLineItemViewSet)

urlpatterns = router.urls
