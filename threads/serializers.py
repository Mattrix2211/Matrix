from rest_framework import serializers
from .models import Thread, Message, Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    """`created_by`/`updated_by` sont posés côté serveur (AttachmentViewSet) ;
    le message d'une pièce jointe ne peut plus changer après création."""

    class Meta:
        model = Attachment
        fields = ("id", "message", "file", "name", "created_by", "updated_by", "created_at", "updated_at")
        read_only_fields = ("id", "created_by", "updated_by", "created_at", "updated_at")

    def validate_message(self, message):
        if self.instance is not None and message != self.instance.message:
            raise serializers.ValidationError("Une pièce jointe ne peut pas être déplacée vers un autre message.")
        return message


class MessageSerializer(serializers.ModelSerializer):
    """L'auteur est toujours l'utilisateur connecté (posé par MessageViewSet) ;
    `is_system` est réservé aux messages automatiques créés côté serveur ; le
    fil d'un message ne peut plus changer après création."""

    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = (
            "id", "thread", "author", "body", "is_system", "attachments",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "author", "is_system", "created_by", "updated_by", "created_at", "updated_at",
        )

    def validate_thread(self, thread):
        if self.instance is not None and thread != self.instance.thread:
            raise serializers.ValidationError("Un message ne peut pas être déplacé vers un autre fil.")
        return thread


class ThreadSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Thread
        fields = ("id", "content_type", "object_id", "messages", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        # L'objet auquel un fil est rattaché ne change jamais : le déplacer
        # vers un objet d'un autre périmètre contournerait le scoping.
        if self.instance is not None:
            for champ in ("content_type", "object_id"):
                if champ in attrs and attrs[champ] != getattr(self.instance, champ):
                    raise serializers.ValidationError(
                        {champ: "Un fil de discussion ne peut pas être rattaché à un autre objet."}
                    )
        return attrs
