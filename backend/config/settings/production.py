from config.settings.base import *  # noqa: F403
from config.settings.base import env, load_environment
from config.settings.reference_cache import reference_cache_settings

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
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "sslmode": env("DB_SSLMODE", default="verify-full"),
            "sslrootcert": env("DB_SSLROOTCERT"),
            "connect_timeout": env.int("DB_CONNECT_TIMEOUT", default=5),
        },
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

# Only a trusted nginx proxy may reach Gunicorn on the private Compose network.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
# We control this hostname only; do not force HTTPS on unrelated subdomains or preload it.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# Reference-list cache only; domain decisions continue to read the database.
globals().update(reference_cache_settings(env, REDIS_URL, ENVIRONMENT))
