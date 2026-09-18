from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_request_approve_and_history_flow() -> None:
    client = APIClient()
    now = datetime.now(UTC) + timedelta(days=10)

    response = client.post(
        "/api/vacations/requests/",
        {
            "type_id": "ANNUAL",
            "start_datetime": now.isoformat(),
            "end_datetime": (now + timedelta(days=1)).isoformat(),
            "use_days": "1.00",
            "reason": "통합 테스트",
        },
        format="json",
        HTTP_X_EMPLOYEE_NO="1001",
    )

    assert response.status_code == 201
    request_id = response.json()["request_id"]

    response = client.post(
        f"/api/vacations/requests/{request_id}/approve/",
        format="json",
        HTTP_X_EMPLOYEE_NO="2001",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "승인"

    response = client.get(
        f"/api/vacations/requests/{request_id}/history/",
        HTTP_X_EMPLOYEE_NO="1001",
    )

    assert response.status_code == 200
    assert [entry["to_status"] for entry in response.json()] == ["대기", "승인"]
