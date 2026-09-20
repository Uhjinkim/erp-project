from unittest.mock import patch

from django.test import override_settings
from redis.exceptions import AuthenticationError, TimeoutError
from rest_framework.test import APIClient

from config.health import _check_redis


@override_settings(
    REDIS_URL="redis://health-user:health-password@127.0.0.1:6379/0",
    HEALTH_CHECK_TIMEOUT_SECONDS=0.25,
)
@patch("config.health.Redis.from_url")
def test_redis_health_uses_configured_url_and_ping(from_url) -> None:
    client = from_url.return_value
    client.ping.return_value = True

    assert _check_redis() == {"status": "connected"}
    from_url.assert_called_once_with(
        "redis://health-user:health-password@127.0.0.1:6379/0",
        socket_connect_timeout=0.25,
        socket_timeout=0.25,
    )
    client.ping.assert_called_once_with()
    client.close.assert_called_once_with()


@override_settings(DEBUG=False, REDIS_URL="redis://127.0.0.1:6379/0")
@patch("config.health.Redis.from_url")
def test_redis_health_reports_authentication_failure(from_url) -> None:
    client = from_url.return_value
    client.ping.side_effect = AuthenticationError("invalid credentials")

    assert _check_redis() == {"status": "disconnected", "detail": "AuthenticationError"}
    client.close.assert_called_once_with()


@override_settings(DEBUG=False, REDIS_URL="redis://127.0.0.1:6379/0")
@patch("config.health.Redis.from_url")
def test_redis_health_reports_timeout(from_url) -> None:
    client = from_url.return_value
    client.ping.side_effect = TimeoutError("timed out")

    assert _check_redis() == {"status": "disconnected", "detail": "TimeoutError"}
    client.close.assert_called_once_with()


@override_settings(REDIS_URL="")
@patch("config.health.Redis.from_url")
def test_redis_health_reports_missing_configuration(from_url) -> None:
    assert _check_redis() == {"status": "not_configured"}
    from_url.assert_not_called()


@override_settings(DEBUG=False, REDIS_URL="redis://[")
@patch("config.health.Redis.from_url")
def test_redis_health_reports_invalid_configuration(from_url) -> None:
    assert _check_redis() == {"status": "disconnected", "detail": "ValueError"}
    from_url.assert_not_called()


@patch("config.health._check_redis", return_value={"status": "connected"})
@patch("config.health._check_database", return_value={"status": "connected"})
def test_health_reports_connected_end_to_end(_database, _redis) -> None:
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert response.json()["end_to_end"]["status"] == "connected"


@override_settings(DEVELOPMENT_OFFLINE_MODE=True)
def test_health_reports_development_offline_simulation() -> None:
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "offline"
    assert response.json()["services"]["database"]["status"] == "offline_simulation"


@patch("config.health._check_redis", return_value={"status": "connected"})
@patch("config.health._check_database", return_value={"status": "disconnected"})
def test_health_reports_database_disconnection(_database, _redis) -> None:
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "offline"
    assert response.json()["end_to_end"]["status"] == "disconnected"


@override_settings(
    VACATION_INTEGRATION_MODE="production",
    VACATION_INTEGRATION_READY=False,
)
@patch("config.health._check_redis", return_value={"status": "connected"})
@patch("config.health._check_database", return_value={"status": "connected"})
def test_health_reports_unconfigured_production_integration(_database, _redis) -> None:
    response = APIClient().get("/api/health/")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["services"]["workforce"]["status"] == "not_configured"
    assert response.json()["end_to_end"]["status"] == "disconnected"


@override_settings(DEVELOPMENT_OFFLINE_MODE=True)
def test_vacation_api_is_unavailable_in_development_offline_mode() -> None:
    response = APIClient().get(
        "/api/vacations/types/",
        HTTP_X_EMPLOYEE_NO="1001",
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "개발 오프라인 모드에서는 휴가 API가 비활성화됩니다."


@override_settings(
    VACATION_INTEGRATION_MODE="production",
    VACATION_INTEGRATION_READY=True,
)
def test_production_does_not_accept_development_employee_header() -> None:
    response = APIClient().get(
        "/api/vacations/types/",
        HTTP_X_EMPLOYEE_NO="1001",
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
