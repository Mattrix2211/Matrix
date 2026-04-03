import os
from django.apps import AppConfig

class ThreadsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "threads"
    verbose_name = "Fils de discussion"
    path = os.path.dirname(os.path.abspath(__file__))
