from config.settings.base import *  # noqa: F403
from config.settings.development_data import (
    VACATION_DEVELOPMENT_EMPLOYEES as DEVELOPMENT_EMPLOYEES,
)

ENVIRONMENT = "test"
SECRET_KEY = "test-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

REDIS_URL = "redis://127.0.0.1:6379/0"
HEALTH_CHECK_TIMEOUT_SECONDS = 0.1
DEVELOPMENT_OFFLINE_MODE = False
VACATION_INTEGRATION_MODE = "development"
VACATION_INTEGRATION_READY = True
VACATION_DEVELOPMENT_EMPLOYEES = DEVELOPMENT_EMPLOYEES

# Legacy-table migrations are state-only in real environments. Tests create their tables directly.
MIGRATION_MODULES = {
    "accounts": None,
    "vacation": None,
    "workforce": None,
}
