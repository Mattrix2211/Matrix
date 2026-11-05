from matrix.settings import *  # noqa
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = ["https://matrix.bord.local"]
SECURE_HSTS_SECONDS = 3600
