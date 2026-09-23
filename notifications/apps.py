import os
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
    verbose_name = "Notifications"
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        from . import signals  # noqa: F401 - connecte le signal d'envoi Web Push
