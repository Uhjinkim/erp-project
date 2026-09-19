import socket
from typing import TypedDict
from urllib.parse import urlparse

from django.conf import settings
from django.db import connection


class ServiceHealth(TypedDict, total=False):
    status: str
    detail: str


def _failure_detail(error: Exception) -> str:
    if settings.DEBUG:
        return f"{type(error).__name__}: {error}"
    return type(error).__name__


def _check_database() -> ServiceHealth:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {"status": "connected"}
    except Exception as error:  # The health endpoint must report failures instead of crashing.
        return {"status": "disconnected", "detail": _failure_detail(error)}


def _check_redis() -> ServiceHealth:
    redis_url = urlparse(settings.REDIS_URL)
    if not redis_url.hostname:
        return {"status": "not_configured"}

    port = redis_url.port or (6380 if redis_url.scheme == "rediss" else 6379)
    try:
        with socket.create_connection(
            (redis_url.hostname, port),
            timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS,
        ):
            pass
        return {"status": "connected"}
    except OSError as error:
        return {"status": "disconnected", "detail": _failure_detail(error)}


def _check_workforce() -> ServiceHealth:
    if not settings.VACATION_INTEGRATION_READY:
        return {"status": "not_configured"}
    if settings.VACATION_INTEGRATION_MODE == "development":
        return {"status": "development_simulation"}
    try:
        from workforce.infrastructure.models import Employee

        Employee.objects.exists()
        return {"status": "connected"}
    except Exception as error:  # Keep health reporting available for schema/integration failures.
        return {"status": "disconnected", "detail": _failure_detail(error)}


def get_system_health() -> dict[str, object]:
    if settings.DEVELOPMENT_OFFLINE_MODE:
        services: dict[str, ServiceHealth] = {
            "backend": {"status": "connected"},
            "database": {"status": "offline_simulation"},
            "redis": {"status": "offline_simulation"},
            "workforce": {"status": "development_simulation"},
        }
        return {
            "status": "offline",
            "environment": settings.ENVIRONMENT,
            "services": services,
            "end_to_end": {"status": "disconnected"},
        }

    database = _check_database()
    redis = _check_redis()
    workforce = _check_workforce()
    services = {
        "backend": {"status": "connected"},
        "database": database,
        "redis": redis,
        "workforce": workforce,
    }
    end_to_end_connected = (
        database["status"] == "connected"
        and redis["status"] == "connected"
        and workforce["status"] in {"connected", "development_simulation"}
        and settings.VACATION_INTEGRATION_READY
    )

    if end_to_end_connected:
        status = "online"
    elif database["status"] == "disconnected":
        status = "offline"
    else:
        status = "degraded"

    return {
        "status": status,
        "environment": settings.ENVIRONMENT,
        "services": services,
        "end_to_end": {"status": "connected" if end_to_end_connected else "disconnected"},
    }
