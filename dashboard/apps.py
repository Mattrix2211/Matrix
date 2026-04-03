import os
from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"
    verbose_name = "Tableaux de bord"
    path = os.path.dirname(os.path.abspath(__file__))
