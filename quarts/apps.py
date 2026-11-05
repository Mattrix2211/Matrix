import os
from django.apps import AppConfig


class QuartsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quarts"
    verbose_name = "Quarts et tours de service"
    path = os.path.dirname(os.path.abspath(__file__))
