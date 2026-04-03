import os
from django.apps import AppConfig

class LogisticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logistics"
    verbose_name = "Logistique"
    path = os.path.dirname(os.path.abspath(__file__))
