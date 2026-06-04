from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = "test-secret-key-not-for-production"

SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

EXTERNAL_API_BASE_URL = "https://ext-amali.vercel.app"

# Speed up password hashing in tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Silence migration output
MIGRATION_MODULES: dict[str, str] = {}

MEDIA_ROOT = "/tmp/insightflow_test_media"
