"""Réglages des processus enfants du test de cohérence multi-processus :
même base que le test parent (PostgreSQL) ou fichier SQLite temporaire."""
import os

from matrix.settings import *  # noqa: F401,F403

if os.getenv("DB_HOST"):
    DATABASES["default"]["NAME"] = os.environ["MATRIX_DB_NOM"]  # noqa: F405
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ["MATRIX_DB_FICHIER"]}}
