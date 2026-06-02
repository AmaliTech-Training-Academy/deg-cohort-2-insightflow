import os

from .base import *  # noqa: F401, F403

DEBUG = True

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "insightflow-dev-secret-key-change-in-production"
)

SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY  # noqa: F405
