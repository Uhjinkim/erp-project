from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.services import HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.history import (
    HistoryEntry,
    TransferTarget,
    plan_cancellation,
    plan_correction,
    require_reason,
)
from workforce.infrastructure.history import DjangoEmploymentHistoryRepository
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    EmploymentHistory,
    EmploymentHistoryChange,
    Person,
    Position,
    Role,
)

TODAY = date(2026, 10, 13)
HIRED = date(2020, 3, 1)
TARGET = TransferTarget(1001, "재직", HIRED, 20, "SENIOR")
FIRST = HistoryEntry(1, HIRED, date(2026, 9, 30), 10, "STAFF", Decimal("3000000"))
LATEST = HistoryEntry(2, date(2026, 10, 1), None, 20, "SENIOR", Decimal("4000000"))


def correct(history: list[HistoryEntry] | None = None, target=TARGET, **overrides):
    values = {
        "history_id": 2,
        "start_date": LATEST.start_date,
        "dept_no": LATEST.dept_no,
        "position_code": LATEST.position_code,
        "base_salary": Decimal("4100000"),
        "today": TODAY,
        **overrides,
    }
    return plan_correction(target, [FIRST, LATEST] if history is None else history, **values)


# --- domain ---------------------------------------------------------------------------------


def test_fn_hr_010_correct_latest_values_without_touching_previous() -> None:
    result = correct()
    assert result.corrected.base_salary == Decimal("4100000")
    assert result.previous_end is None


@pytest.mark.parametrize("start_date", [date(2026, 9, 15), date(2026, 10, 5)])
def test_fn_hr_010_correcting_start_date_moves_previous_end(start_date: date) -> None:
    result = correct(start_date=start_date)
    assert result.previous_end == (1, start_date - timedelta(days=1))


def test_fn_hr_010_first_history_keeps_hire_date_start() -> None:
    only = HistoryEntry(1, HIRED, None, 10, "STAFF", Decimal("3000000"))
    assert correct([only], history_id=1, start_date=HIRED, dept_no=20).corrected.dept_no == 20
    with pytest.raises(WorkforceRuleViolation):
        correct([only], history_id=1, start_date=date(2020, 4, 1), dept_no=20)


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"base_salary": LATEST.base_salary}, None),
        ({"history_id": 1}, "history_id"),
        ({"history_id": 99}, "history_id"),
        ({"dept_no": 10, "position_code": "STAFF"}, None),
        ({"start_date": HIRED}, "start_date"),
        ({"start_date": TODAY + timedelta(days=1)}, "start_date"),
        ({"base_salary": Decimal("-1")}, "base_salary"),
    ],
)
def test_fn_hr_010_correction_rejections(overrides: dict[str, object], field: str | None) -> None:
    with pytest.raises(WorkforceRuleViolation) as exc:
        correct(**overrides)
    assert exc.value.field == field


def test_fn_hr_010_closed_latest_or_terminated_cannot_be_corrected() -> None:
    closed = HistoryEntry(2, date(2026, 10, 1), date(2026, 10, 5), 20, "SENIOR", Decimal("1"))
    with pytest.raises(WorkforceRuleViolation):
        correct([FIRST, closed])
    with pytest.raises(WorkforceRuleViolation):
        correct(target=TransferTarget(1001, "퇴사", HIRED, 20, "SENIOR"))


def test_fn_hr_010_cancellation_reopens_previous_history() -> None:
    result = plan_cancellation(TARGET, [FIRST, LATEST], history_id=2)
    assert result.cancelled == LATEST
    assert (result.reopened.history_id, result.reopened.end_date) == (1, None)
    with pytest.raises(WorkforceRuleViolation):
        plan_cancellation(TARGET, [FIRST, LATEST], history_id=1)
    with pytest.raises(WorkforceRuleViolation):
        only = HistoryEntry(1, HIRED, None, 10, "STAFF", Decimal(0))
        plan_cancellation(TARGET, [only], history_id=1)


@pytest.mark.parametrize("reason", [None, "", "   "])
def test_fn_hr_010_reason_is_required(reason: str | None) -> None:
    with pytest.raises(WorkforceRuleViolation) as exc:
        require_reason(reason)
    assert exc.value.field == "reason"


# --- API ------------------------------------------------------------------------------------


@pytest.fixture
def org(db: None) -> dict[str, object]:
    Department.objects.create(dept_no=10, dept_name="영업팀")
    Department.objects.create(dept_no=20, dept_name="개발팀")
    Position.objects.create(position_code="STAFF", position_name="사원", sort_order=1)
    Position.objects.create(position_code="SENIOR", position_name="대리", sort_order=2)
    Role.objects.create(role_code=HR_MANAGER_ROLE, role_name=HR_MANAGER_ROLE)
    hr = create_employee(9001, "hr@example.com")
    EmployeeRole.objects.create(employee=hr, role_id=HR_MANAGER_ROLE, assigned_at=timezone.now())
    staff = create_employee(1001, "staff@example.com")
    return {
        "hr": User.objects.create_user(email="hr@example.com", password="pw", employee=hr),
        "staff_user": User.objects.create_user(
            email="staff@example.com", password="pw", employee=staff
        ),
    }


def create_employee(employee_no: int, email: str) -> Employee:
    person = Person.objects.create(
        name=f"사원 {employee_no}", birth_date=date(1990, 1, 1), gender="M"
    )
    return Employee.objects.create(
        employee_no=employee_no,
        person=person,
        department_id=10,
        position_id="STAFF",
        tenure_status="재직",
        email=email,
        hire_date=HIRED,
    )


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def base(employee_no: int = 1001) -> str:
    return f"/api/workforce/employees/{employee_no}/history/"


@pytest.fixture
def transferred(org: dict) -> dict[str, int]:
    """부서장(영업팀)인 1001을 개발팀 대리로 발령한 상태."""
    first = EmploymentHistory.objects.create(
        employee_id=1001,
        start_date=HIRED,
        department_id=10,
        position_id="STAFF",
        base_salary=Decimal("3000000"),
    )
    Department.objects.filter(dept_no=10).update(head_id=1001)
    response = client_for(org["hr"]).post(
        base(),
        {
            "start_date": "2026-10-01",
            "dept_no": 20,
            "position_code": "SENIOR",
            "base_salary": "4000000",
            "reason": "정기 인사",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.json()["released_head_dept_nos"] == [10]
    return {"first": first.history_id, "latest": response.json()["history"][0]["history_id"]}


def correction(**overrides: object) -> dict[str, object]:
    return {
        "start_date": "2026-10-01",
        "dept_no": 20,
        "position_code": "SENIOR",
        "base_salary": "4100000",
        "reason": "기본급 오입력",
        **overrides,
    }


def test_fn_hr_010_only_hr_manager_can_correct_cancel_or_view_changes(
    org: dict, transferred: dict
) -> None:
    client = client_for(org["staff_user"])
    latest = transferred["latest"]
    assert client.post(f"{base()}{latest}/correct/", correction()).status_code == 403
    assert client.post(f"{base()}{latest}/cancel/", {"reason": "x"}).status_code == 403
    assert client.get(f"{base()}changes/").status_code == 403


def test_fn_hr_010_correct_latest_history_and_record_change(
    org: dict, transferred: dict
) -> None:
    response = client_for(org["hr"]).post(
        f"{base()}{transferred['latest']}/correct/", correction(), format="json"
    )

    assert response.status_code == 200, response.data
    assert response.json()["history"][0]["base_salary"] == "4100000.00"
    change = EmploymentHistoryChange.objects.get(action="정정")
    assert change.history_id == transferred["latest"]
    assert change.before_values["base_salary"] == "4000000.00"
    assert change.after_values["base_salary"] == "4100000.00"
    assert (change.reason, change.changed_by_id) == ("기본급 오입력", 9001)


@pytest.mark.parametrize(
    ("start_date", "previous_end"),
    [("2026-09-15", date(2026, 9, 14)), ("2026-10-05", date(2026, 10, 4))],
)
def test_fn_hr_010_correct_start_date_adjusts_previous_end(
    org: dict, transferred: dict, start_date: str, previous_end: date
) -> None:
    response = client_for(org["hr"]).post(
        f"{base()}{transferred['latest']}/correct/",
        correction(start_date=start_date, base_salary="4000000"),
        format="json",
    )
    assert response.status_code == 200, response.data
    assert EmploymentHistory.objects.get(history_id=transferred["first"]).end_date == previous_end
    latest = EmploymentHistory.objects.get(history_id=transferred["latest"])
    assert latest.start_date == date.fromisoformat(start_date)


def test_fn_hr_010_correct_department_updates_current_assignment(
    org: dict, transferred: dict
) -> None:
    Department.objects.create(dept_no=30, dept_name="기획팀")
    response = client_for(org["hr"]).post(
        f"{base()}{transferred['latest']}/correct/",
        correction(dept_no=30, base_salary="4000000", reason="부서 오입력"),
        format="json",
    )
    assert response.status_code == 200, response.data
    assert Employee.objects.get(employee_no=1001).department_id == 30


@pytest.mark.parametrize(
    ("target", "overrides", "field"),
    [
        ("first", {}, "history_id"),
        ("latest", {"dept_no": 10, "position_code": "STAFF"}, None),
        ("latest", {"base_salary": "4000000"}, None),
        ("latest", {"dept_no": 99}, "dept_no"),
    ],
)
def test_fn_hr_010_correction_rejections_change_nothing(
    org: dict, transferred: dict, target: str, overrides: dict, field: str | None
) -> None:
    response = client_for(org["hr"]).post(
        f"{base()}{transferred[target]}/correct/", correction(**overrides), format="json"
    )
    assert response.status_code == 400
    assert response.json().get("field") == field
    assert EmploymentHistory.objects.get(history_id=transferred["latest"]).base_salary == Decimal(
        "4000000"
    )
    assert not EmploymentHistoryChange.objects.filter(action="정정").exists()


@pytest.mark.parametrize("body", [{}, {"reason": ""}, {"reason": "   "}])
def test_fn_hr_010_reason_is_required_for_correction_and_cancel(
    org: dict, transferred: dict, body: dict
) -> None:
    client = client_for(org["hr"])
    latest = transferred["latest"]
    payload = {key: value for key, value in correction().items() if key != "reason"}
    assert client.post(f"{base()}{latest}/correct/", {**payload, **body}).status_code == 400
    assert client.post(f"{base()}{latest}/cancel/", body).status_code == 400
    assert EmploymentHistory.objects.filter(history_id=latest).exists()


def test_fn_hr_010_cancel_reverts_assignment_and_restores_vacant_head(
    org: dict, transferred: dict
) -> None:
    response = client_for(org["hr"]).post(
        f"{base()}{transferred['latest']}/cancel/", {"reason": "발령 철회"}, format="json"
    )

    assert response.status_code == 200, response.data
    body = response.json()
    assert [(row["history_id"], row["end_date"]) for row in body["history"]] == [
        (transferred["first"], None)
    ]
    assert body["restored_head_dept_nos"] == [10]
    assert not EmploymentHistory.objects.filter(history_id=transferred["latest"]).exists()
    staff = Employee.objects.get(employee_no=1001)
    assert (staff.department_id, staff.position_id) == (10, "STAFF")
    assert Department.objects.get(dept_no=10).head_id == 1001
    change = EmploymentHistoryChange.objects.get(action="취소")
    assert change.before_values["dept_no"] == 20
    assert change.restored_head_dept_nos == [10]


def test_fn_hr_010_cancel_does_not_override_new_department_head(
    org: dict, transferred: dict
) -> None:
    create_employee(1002, "successor@example.com")
    Department.objects.filter(dept_no=10).update(head_id=1002)

    response = client_for(org["hr"]).post(
        f"{base()}{transferred['latest']}/cancel/", {"reason": "발령 철회"}, format="json"
    )

    assert response.status_code == 200, response.data
    assert response.json()["restored_head_dept_nos"] == []
    assert Department.objects.get(dept_no=10).head_id == 1002


def test_fn_hr_010_first_history_cannot_be_cancelled(org: dict) -> None:
    only = EmploymentHistory.objects.create(
        employee_id=1001,
        start_date=HIRED,
        department_id=10,
        position_id="STAFF",
        base_salary=Decimal("3000000"),
    )
    response = client_for(org["hr"]).post(
        f"{base()}{only.history_id}/cancel/", {"reason": "x"}, format="json"
    )
    assert response.status_code == 400
    assert EmploymentHistory.objects.filter(history_id=only.history_id).exists()


def test_fn_hr_010_cancel_failure_rolls_back(
    org: dict, transferred: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: object, change: object) -> None:
        raise RuntimeError("audit failed")

    monkeypatch.setattr(DjangoEmploymentHistoryRepository, "record_change", boom)
    with pytest.raises(RuntimeError):
        client_for(org["hr"]).post(
            f"{base()}{transferred['latest']}/cancel/", {"reason": "발령 철회"}, format="json"
        )

    assert EmploymentHistory.objects.filter(history_id=transferred["latest"]).exists()
    assert EmploymentHistory.objects.get(history_id=transferred["first"]).end_date == date(
        2026, 9, 30
    )
    assert Employee.objects.get(employee_no=1001).department_id == 20
    assert Department.objects.get(dept_no=10).head_id is None


def test_fn_hr_010_change_log_lists_transfer_correction_cancel(
    org: dict, transferred: dict
) -> None:
    client = client_for(org["hr"])
    latest = transferred["latest"]
    client.post(f"{base()}{latest}/correct/", correction(), format="json")
    client.post(f"{base()}{latest}/cancel/", {"reason": "발령 철회"}, format="json")

    response = client.get(f"{base()}changes/")

    assert response.status_code == 200
    rows = response.json()
    assert [row["action"] for row in rows] == ["취소", "정정", "발령"]
    assert rows[2]["after"]["dept_no"] == 20 and rows[2]["before"] is None
    assert rows[2]["released_head_dept_nos"] == [10]
    assert rows[0]["after"] is None and rows[0]["changed_by"] == 9001
    assert client.get(base(5555) + "changes/").status_code == 404
