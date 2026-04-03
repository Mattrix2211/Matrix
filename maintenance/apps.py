import os
from django.apps import AppConfig

class MaintenanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "maintenance"
    verbose_name = "Maintenance"
    path = os.path.dirname(os.path.abspath(__file__))
