import os

from django.apps import AppConfig


class AbsencesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "absences"
    verbose_name = "Absences et indisponibilités"
    path = os.path.dirname(os.path.abspath(__file__))
