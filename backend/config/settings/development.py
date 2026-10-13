from config.settings.base import *  # noqa: F403
from config.settings.base import BASE_DIR, env, load_environment
from config.settings.development_data import (
    VACATION_DEVELOPMENT_EMPLOYEES as DEVELOPMENT_EMPLOYEES,
)

ENVIRONMENT = "development"
load_environment(ENVIRONMENT)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-development-key")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# The frontend (Vite) and nginx run on different ports than the backend, so a login
# POST is a cross-origin request from Django's point of view unless these are trusted.
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

DEVELOPMENT_OFFLINE_MODE = env("DEVELOPMENT_OFFLINE_MODE")

if DEVELOPMENT_OFFLINE_MODE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": env(
                "DEVELOPMENT_SQLITE_PATH",
                default=str(BASE_DIR / ".development.sqlite3"),
            ),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", default="erp"),
            "USER": env("DB_USER", default="erp"),
            "PASSWORD": env("DB_PASSWORD", default="erp"),
            "HOST": env("DB_HOST", default="127.0.0.1"),
            "PORT": env("DB_PORT", default="5432"),
        }
    }

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
HEALTH_CHECK_TIMEOUT_SECONDS = env("HEALTH_CHECK_TIMEOUT_SECONDS")

VACATION_INTEGRATION_MODE = env("VACATION_INTEGRATION_MODE", default="development")
VACATION_INTEGRATION_READY = True
VACATION_DEVELOPMENT_EMPLOYEES = DEVELOPMENT_EMPLOYEES

# Local testing only: set false when the test employees were all hired recently.
EVALUATION_MINIMUM_TENURE_ENABLED = env.bool("EVALUATION_MINIMUM_TENURE_ENABLED", default=True)
