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
