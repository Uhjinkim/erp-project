from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APIClient


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
