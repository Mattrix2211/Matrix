from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from bordops.core.models import TimeStampedModel, OwnedModel

User = get_user_model()

class Thread(TimeStampedModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"Thread {self.content_type} {self.object_id}"

class Message(TimeStampedModel, OwnedModel):
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    body = models.TextField()
    is_system = models.BooleanField(default=False)

class Attachment(TimeStampedModel, OwnedModel):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="thread_attachments/")
    name = models.CharField(max_length=255)
