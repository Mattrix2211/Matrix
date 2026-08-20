from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from matrix.core.models import TimeStampedModel

User = get_user_model()


class NotificationLevel(models.TextChoices):
    """Niveau de gravité d'une notification. Seul le niveau DANGER déclenche un
    envoi Web Push (cf. notifications/signals.py) : les niveaux WARNING/INFO
    restent strictement in-app pour ne pas noyer l'équipage d'alertes de
    moindre importance."""
    INFO = "info", "Information"
    WARNING = "warning", "Attention"
    DANGER = "danger", "Critique"


class Notification(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    verb = models.CharField(max_length=255)
    level = models.CharField(max_length=10, choices=NotificationLevel.choices, default=NotificationLevel.INFO)
    is_read = models.BooleanField(default=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    target = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ("-created_at",)


class PushSubscription(TimeStampedModel):
    """Abonnement Web Push d'un utilisateur sur un appareil/navigateur donné
    (format standard Web Push API : endpoint + clés de chiffrement p256dh/auth,
    fournis par navigator.serviceWorker.pushManager.subscribe() côté client)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=500, unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Abonnement push de {self.user} ({self.endpoint[:40]}…)"
