from rest_framework import viewsets, permissions
from .models import Thread, Message, Attachment
from .serializers import ThreadSerializer, MessageSerializer, AttachmentSerializer
from matrix.core.permissions import IsAuthorOrReadOnly, RolePermission
from matrix.core.roles import RoleLevel

class DefaultPermission(permissions.IsAuthenticated):
    pass

class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all()
    serializer_class = ThreadSerializer
    permission_classes = [RolePermission]
    # limiter l'écriture aux chefs de section et plus
    min_role_level_write = RoleLevel.CHEF_SECTION

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.select_related("thread", "author").all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthorOrReadOnly]

class AttachmentViewSet(viewsets.ModelViewSet):
    queryset = Attachment.objects.select_related("message").all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthorOrReadOnly]
