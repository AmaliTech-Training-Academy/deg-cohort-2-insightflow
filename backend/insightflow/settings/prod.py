import os

from .base import *  # noqa: F401, F403

DEBUG = False

_allowed = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h for h in _allowed.split(",") if h]

CORS_ALLOW_ALL_ORIGINS = True
# CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
