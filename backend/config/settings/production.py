from config.settings.base import *  # noqa: F403
from config.settings.base import env, load_environment

ENVIRONMENT = "production"
load_environment(ENVIRONMENT)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
    }
}

REDIS_URL = env("REDIS_URL")
HEALTH_CHECK_TIMEOUT_SECONDS = env("HEALTH_CHECK_TIMEOUT_SECONDS")

# Production uses the database workforce adapters and session-authenticated employee identity.
VACATION_INTEGRATION_MODE = "database"
VACATION_INTEGRATION_READY = True
DEVELOPMENT_OFFLINE_MODE = False

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
