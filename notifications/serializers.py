from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        # Seul « lu / non lu » est modifiable par l'API
        read_only_fields = ("user", "verb", "level", "content_type", "object_id", "created_at")
