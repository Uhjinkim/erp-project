from math import isfinite

from django.core.exceptions import ImproperlyConfigured
from redis.backoff import NoBackoff
from redis.retry import Retry


def reference_cache_settings(env, redis_url: str, environment: str) -> dict[str, object]:
    """Separate cache alias; do not change sessions or the default cache."""
    enabled = env.bool("REFERENCE_CACHE_ENABLED", default=environment == "production")
    try:
        ttl = env.int("REFERENCE_CACHE_TTL", default=180)
        timeout = env.float("REFERENCE_CACHE_TIMEOUT", default=0.2)
    except (TypeError, ValueError) as error:
        raise ImproperlyConfigured("Invalid reference cache TTL or timeout.") from error
    if not 1 <= ttl <= 300 or not isfinite(timeout) or not 0 < timeout <= 1:
        raise ImproperlyConfigured("Invalid reference cache TTL (1..300) or timeout (0..1].")
    return {
        "REFERENCE_CACHE_ENABLED": enabled,
        "REFERENCE_CACHE_TTL": ttl,
        "CACHES": {
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
            "reference": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": env("REFERENCE_CACHE_URL", default=redis_url),
                "KEY_PREFIX": env(
                    "REFERENCE_CACHE_KEY_PREFIX", default=f"erp:{environment}:reference:v1"
                ),
                "TIMEOUT": ttl,
                "OPTIONS": {
                    "socket_connect_timeout": timeout,
                    "socket_timeout": timeout,
                    "max_connections": 8,
                    "retry": Retry(NoBackoff(), 0),
                },
            },
        },
    }
