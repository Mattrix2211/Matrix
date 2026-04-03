import os
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Comptes"
    # Fix Windows multiple-path issue by pinning absolute path
    path = os.path.dirname(os.path.abspath(__file__))
