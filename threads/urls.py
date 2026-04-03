from rest_framework.routers import DefaultRouter
from .views import ThreadViewSet, MessageViewSet, AttachmentViewSet

router = DefaultRouter()
router.register(r'threads', ThreadViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'attachments', AttachmentViewSet)

urlpatterns = router.urls
