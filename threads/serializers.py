from rest_framework import serializers
from .models import Thread, Message, Attachment

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = "__all__"
        read_only_fields = ["created_by", "updated_by"]

class MessageSerializer(serializers.ModelSerializer):
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = "__all__"
        # Auteur et message système sont posés par le serveur, jamais par l'appelant.
        read_only_fields = ["author", "is_system", "created_by", "updated_by"]

    def validate_thread(self, thread):
        if self.instance and thread != self.instance.thread:
            raise serializers.ValidationError("Un message ne peut pas changer de fil.")
        return thread

class ThreadSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Thread
        fields = "__all__"
