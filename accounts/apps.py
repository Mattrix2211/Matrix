import os
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Comptes"
    # Fix Windows multiple-path issue by pinning absolute path
    path = os.path.dirname(os.path.abspath(__file__))

    def ready(self):
        from matrix.core import checks  # noqa: F401 - enregistre le garde-fou migrations en attente
