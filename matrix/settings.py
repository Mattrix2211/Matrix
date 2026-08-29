import os
from pathlib import Path
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Valeur de secours utilisée uniquement en développement local (DEBUG=1 par
# défaut). En production (DJANGO_DEBUG=0), une clé secrète explicite et
# différente de cette valeur de dev est obligatoire — voir le contrôle
# ci-dessous, qui fait échouer le démarrage plutôt que de retomber
# silencieusement sur cette clé publique.
_CLE_SECRETE_DEV_PAR_DEFAUT = "dev-secret-key"

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", _CLE_SECRETE_DEV_PAR_DEFAUT)
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

# Garde-fou de démarrage : en production (DEBUG=False), il est interdit de
# démarrer avec la clé secrète de développement — un fallback silencieux
# exposerait une clé publique connue en environnement réel. En dev local
# (DEBUG=True, comportement par défaut sans variables d'environnement
# positionnées), aucune vérification n'est faite pour ne pas gêner le
# développement quotidien.
if not DEBUG and SECRET_KEY == _CLE_SECRETE_DEV_PAR_DEFAUT:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit être défini avec une valeur de production "
        "(différente de la clé de développement) lorsque DJANGO_DEBUG=0."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "rest_framework",
    "django_filters",
    "crispy_forms",
    "crispy_bootstrap5",
    "storages",
    # project apps
    "accounts.apps.AccountsConfig",
    "org.apps.OrgConfig",
    "assets.apps.AssetsConfig",
    "maintenance.apps.MaintenanceConfig",
    "logistics.apps.LogisticsConfig",
    "training.apps.TrainingConfig",
    "threads.apps.ThreadsConfig",
    "notifications.apps.NotificationsConfig",
    "dashboard.apps.DashboardConfig",
    "calendar_app.apps.CalendarAppConfig",
    "reports.apps.ReportsConfig",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "matrix.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "matrix" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "matrix.context_processors.installations_notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "matrix.wsgi.application"
ASGI_APPLICATION = "matrix.asgi.application"

# Database: default to SQLite; use Postgres if env set
if os.getenv("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "matrix"),
            "USER": os.getenv("DB_USER", "matrix"),
            "PASSWORD": os.getenv("DB_PASSWORD", "matrix"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "matrix" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
}

# Celery / Redis
from celery.schedules import crontab

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_BEAT_SCHEDULE = {
    "generate_occurrences_daily": {
        "task": "maintenance.tasks.generate_occurrences",
        "schedule": 60 * 60 * 24,
        "args": (90,),
    },
    "compute_overdue_hourly": {
        "task": "maintenance.tasks.compute_overdue",
        "schedule": 60 * 60,
    },
    "notify_expiring_training_daily": {
        "task": "notifications.tasks.notify_expiring_training",
        "schedule": 60 * 60 * 24,
    },
    "notify_overdue_occurrences_hourly": {
        "task": "notifications.tasks.notify_overdue_occurrences",
        "schedule": 60 * 60,
    },
    "notify_low_stock_daily": {
        "task": "notifications.tasks.notify_low_stock",
        "schedule": 60 * 60 * 24,
    },
    # Installations fixes (propulseurs, pompes, circuits électriques) : mêmes besoins
    # que le matériel mobile ci-dessus, mais jamais planifiés jusqu'ici.
    "generate_installation_occurrences_daily": {
        "task": "maintenance.tasks.generate_installation_occurrences",
        "schedule": 60 * 60 * 24,
        "args": (90,),
    },
    "generate_installation_notifications_daily": {
        "task": "notifications.tasks.generate_installation_notifications",
        # Déclenchement toutes les minutes : la tâche elle-même compare l'heure
        # courante à la préférence de chaque marin (UserProfile.notification_time)
        # pour décider s'il faut le notifier. Un horaire fixe (crontab(hour=8,
        # minute=0)) ne déclenchait la tâche qu'une fois par jour et ne couvrait
        # donc que les marins ayant gardé la préférence par défaut (08:00) : tout
        # marin ayant personnalisé son horaire n'était jamais notifié. Même
        # principe que notify_ma_journee_minute ci-dessous.
        "schedule": crontab(minute="*"),
    },
    "generate_installation_maintenance_notifications_daily": {
        "task": "notifications.tasks.generate_installation_maintenance_notifications",
        # Voir le commentaire de generate_installation_notifications_daily ci-dessus :
        # même bug, même correctif.
        "schedule": crontab(minute="*"),
    },
    # Dérive sur les relevés techniques (isolement, heures de marche) : contrairement
    # aux échéances ci-dessus, ce calcul ne dépend pas de la préférence d'heure
    # de chaque marin (pas de notifier() par utilisateur), un horaire fixe une
    # fois par jour suffit donc - un calcul de tendance n'a pas besoin d'être
    # aussi instantané qu'une échéance déjà atteinte.
    "detect_installation_drift_daily": {
        "task": "notifications.tasks.detect_installation_drift",
        "schedule": crontab(hour=8, minute=30),
    },
    # Digest calendrier quotidien « Ma journée »/« Ma journée de demain » : la
    # tâche elle-même compare l'heure courante à la préférence de chaque marin
    # (UserProfile.notification_time / notification_time_soir), donc un
    # déclenchement toutes les minutes suffit à respecter des préférences
    # différentes d'un marin à l'autre (même principe que les alertes
    # d'échéance d'installations ci-dessus).
    "notify_ma_journee_minute": {
        "task": "notifications.tasks.notify_ma_journee",
        "schedule": crontab(minute="*"),
    },
    "notify_ma_journee_demain_minute": {
        "task": "notifications.tasks.notify_ma_journee_demain",
        "schedule": crontab(minute="*"),
    },
}

# Email
# Par défaut, en dev: backend console (affiche le mail dans le terminal)
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@localhost")

# Si vous passez en SMTP, renseignez les variables d'environnement suivantes:
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "0") == "0"  # privilégier TLS

# Storages (local dev by default)
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Notifications Web Push (alertes critiques hors navigateur ouvert) : paire de
# clés VAPID générée UNE FOIS via `python manage.py generate_vapid_keys`, puis
# stockée en variables d'environnement — jamais régénérée à la volée (sinon
# tous les abonnements existants deviennent invalides). Si absentes, l'envoi
# Web Push est simplement désactivé (cf. notifications/push.py) : les
# notifications in-app continuent de fonctionner normalement.
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_ADMIN_EMAIL = os.getenv("VAPID_ADMIN_EMAIL", "no-reply@localhost")

# Security (sane defaults for dev; harden in prod)
CSRF_TRUSTED_ORIGINS = [
    origin for origin in [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
]

# Durcissement HTTPS : actif uniquement en production (DEBUG=False), pour ne
# pas casser le développement local en HTTP simple (runserver, tests).
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
