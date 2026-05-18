"""
Development settings for the Automobile Backend API.

Inherits from base.py and overrides only what's needed for local development.
"""

from config.settings.base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

SECRET_KEY = "dev-secret-key-change-in-production-abc123xyz"

# ---------------------------------------------------------------------------
# Database — SQLite for development
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

# ---------------------------------------------------------------------------
# Cache — LocMemCache for rate limiting in development
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "automobile-backend-dev",
    }
}

# ---------------------------------------------------------------------------
# Email — use in-memory backend in development/testing so no real SMTP needed.
# To test with real SMTP, set EMAIL_BACKEND to smtp and fill credentials below.
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@automobile-backend.local"

# Uncomment and fill these to use real SMTP in development:
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = "your-email@gmail.com"
# EMAIL_HOST_PASSWORD = "your-app-password"
# DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ---------------------------------------------------------------------------
# File storage — local filesystem in development
# ---------------------------------------------------------------------------

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# ---------------------------------------------------------------------------
# CORS — allow all origins in development
# ---------------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = True

# ---------------------------------------------------------------------------
# Logging — show SQL queries in development (optional, set to WARNING to mute)
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
