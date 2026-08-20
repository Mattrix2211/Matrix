from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, PushPublicKeyView, PushSubscribeView, PushUnsubscribeView

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet)

urlpatterns = router.urls + [
    path('push/public-key/', PushPublicKeyView.as_view(), name='push-public-key'),
    path('push/subscribe/', PushSubscribeView.as_view(), name='push-subscribe'),
    path('push/unsubscribe/', PushUnsubscribeView.as_view(), name='push-unsubscribe'),
]
