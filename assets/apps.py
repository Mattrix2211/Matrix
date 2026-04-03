import os
from django.apps import AppConfig

class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "assets"
    verbose_name = "Actifs"
    path = os.path.dirname(os.path.abspath(__file__))
