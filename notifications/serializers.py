from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Seul le marquage lu/non lu est modifiable par l'API : les notifications
    sont créées côté serveur (signaux), jamais par le client."""

    class Meta:
        model = Notification
        fields = (
            "id", "user", "verb", "level", "is_read",
            "content_type", "object_id", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "user", "verb", "level", "content_type", "object_id",
            "created_at", "updated_at",
        )
