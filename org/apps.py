import os
from django.apps import AppConfig

class OrgConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "org"
    verbose_name = "Organisation"
    path = os.path.dirname(os.path.abspath(__file__))
