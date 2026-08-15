import os
from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
    verbose_name = "Bilans PDF"
    path = os.path.dirname(os.path.abspath(__file__))
