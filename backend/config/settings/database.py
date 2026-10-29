from math import isfinite

from django.core.exceptions import ImproperlyConfigured


def development_connection_options(env) -> dict[str, object]:
    """runserver 요청 스레드 사이에서 재사용할 작은 프로세스별 풀."""
    # SSH forwarding can take several seconds for the initial database handshake.
    connect_timeout = env.int("DB_CONNECT_TIMEOUT", default=10)
    if connect_timeout <= 0:
        raise ImproperlyConfigured("DB_CONNECT_TIMEOUT must be positive.")
    options: dict[str, object] = {"connect_timeout": connect_timeout}
    if not env.bool("DB_POOL_ENABLED", default=True):
        return options
    minimum = env.int("DB_POOL_MIN_SIZE", default=0)
    maximum = env.int("DB_POOL_MAX_SIZE", default=4)
    try:
        timeout = env.float("DB_POOL_TIMEOUT", default=15)
    except (TypeError, ValueError):
        raise ImproperlyConfigured("DB_POOL_TIMEOUT must be a positive number.") from None
    if (
        minimum < 0 or maximum < 1 or minimum > maximum
        or not isfinite(timeout) or timeout <= 0
    ):
        raise ImproperlyConfigured("Invalid DB_POOL_MIN_SIZE, DB_POOL_MAX_SIZE or DB_POOL_TIMEOUT.")
    options["pool"] = {
        "min_size": minimum,
        "max_size": maximum,
        "timeout": timeout,
        "max_idle": 60,
        "reconnect_timeout": 30,
    }
    return options
