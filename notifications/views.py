from django.conf import settings
from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.views import APIView
from .models import Notification, PushSubscription
from .serializers import NotificationSerializer

class DefaultPermission(permissions.IsAuthenticated):
    pass

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related("user").all()
    serializer_class = NotificationSerializer
    permission_classes = [DefaultPermission]

    def get_queryset(self):
        # Limite les notifications à l'utilisateur courant, pour la confidentialité
        qs = super().get_queryset()
        if self.request and self.request.user and self.request.user.is_authenticated:
            return qs.filter(user=self.request.user)
        return qs.none()

    @decorators.action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return response.Response({"marked": count})


class PushPublicKeyView(APIView):
    """Expose la clé publique VAPID au script client (push.js), nécessaire
    pour créer un abonnement Web Push côté navigateur."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return response.Response({"publicKey": settings.VAPID_PUBLIC_KEY})


class PushSubscribeView(APIView):
    """Enregistre l'abonnement Web Push de l'appareil courant pour
    l'utilisateur connecté (format standard PushSubscription.toJSON())."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data
        endpoint = data.get("endpoint")
        keys = data.get("keys") or {}
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")
        if not endpoint or not p256dh or not auth:
            return response.Response(
                {"detail": "Abonnement incomplet (endpoint/p256dh/auth requis)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "user": request.user,
                "p256dh": p256dh,
                "auth": auth,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
            },
        )
        return response.Response({"detail": "Abonnement enregistré."}, status=status.HTTP_201_CREATED)


class PushUnsubscribeView(APIView):
    """Retire l'abonnement Web Push de l'appareil courant. Ne supprime que les
    abonnements appartenant à l'utilisateur connecté, pour la confidentialité."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get("endpoint")
        if not endpoint:
            return response.Response(
                {"detail": "Endpoint requis."}, status=status.HTTP_400_BAD_REQUEST
            )
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return response.Response({"detail": "Abonnement supprimé."})
