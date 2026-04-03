import os
from django.apps import AppConfig

class CalendarAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "calendar_app"
    verbose_name = "Calendrier"
    path = os.path.dirname(os.path.abspath(__file__))
