from rest_framework import viewsets, permissions, decorators, response
from .models import Notification
from .serializers import NotificationSerializer

class DefaultPermission(permissions.IsAuthenticated):
    pass

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related("user").all()
    serializer_class = NotificationSerializer
    permission_classes = [DefaultPermission]

    def get_queryset(self):
        # Limit notifications to the current user for privacy
        qs = super().get_queryset()
        if self.request and self.request.user and self.request.user.is_authenticated:
            return qs.filter(user=self.request.user)
        return qs.none()

    @decorators.action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return response.Response({"marked": count})
