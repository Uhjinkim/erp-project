from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.services import HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.history import HistoryEntry, TransferTarget, plan_transfer
from workforce.infrastructure.history import DjangoEmploymentHistoryRepository
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    EmploymentHistory,
    Person,
    Position,
    Role,
)

TODAY = date(2026, 10, 13)
HIRED = date(2020, 3, 1)
TARGET = TransferTarget(1001, "재직", HIRED, 10, "STAFF")
OPEN = HistoryEntry(1, HIRED, None, 10, "STAFF", Decimal("3000000"))
SALARY = Decimal("4000000")


def plan(target: TransferTarget = TARGET, history: list[HistoryEntry] | None = None, **kw):
    values = {
        "start_date": date(2026, 10, 1),
        "dept_no": 20,
        "position_code": "SENIOR",
        "base_salary": SALARY,
        "previous_base_salary": None,
        "today": TODAY,
        **kw,
    }
    return plan_transfer(target, [OPEN] if history is None else history, **values)


# --- domain ---------------------------------------------------------------------------------


def test_fn_hr_010_transfer_closes_open_history_on_previous_day() -> None:
    result = plan()
    assert result.close == (1, date(2026, 9, 30))
    assert result.baseline is None
    assert result.new == HistoryEntry(None, date(2026, 10, 1), None, 20, "SENIOR", SALARY)


def test_fn_hr_010_first_transfer_creates_period_since_hire_date() -> None:
    result = plan(history=[], previous_base_salary=Decimal("3000000"))
    assert result.close is None
    assert result.baseline == HistoryEntry(
        None, HIRED, date(2026, 9, 30), 10, "STAFF", Decimal("3000000")
    )


def test_fn_hr_010_first_transfer_on_hire_date_needs_no_previous_period() -> None:
    result = plan(history=[], start_date=HIRED)
    assert result.baseline is None and result.close is None


def test_fn_hr_010_transfer_after_closed_history_does_not_close() -> None:
    closed = HistoryEntry(1, HIRED, date(2025, 12, 31), 10, "STAFF", SALARY)
    result = plan(history=[closed], start_date=date(2026, 1, 1))
    assert result.close is None


def test_fn_hr_010_position_change_only_is_allowed() -> None:
    assert plan(dept_no=10).new.position_code == "SENIOR"


@pytest.mark.parametrize(
    ("target", "history", "overrides", "field"),
    [
        (TransferTarget(1001, "퇴사", HIRED, 10, "STAFF"), None, {}, None),
        (TARGET, None, {"start_date": TODAY + timedelta(days=1)}, "start_date"),
        (TARGET, [], {"start_date": date(2020, 2, 29)}, "start_date"),
        (TARGET, None, {"start_date": HIRED}, "start_date"),
        (
            TARGET,
            [HistoryEntry(1, HIRED, date(2026, 5, 31), 10, "STAFF", SALARY)],
            {"start_date": date(2026, 5, 31)},
            "start_date",
        ),
        # 기본급만 바뀌는 등록은 거절한다.
        (TARGET, None, {"dept_no": 10, "position_code": "STAFF"}, None),
        (TARGET, None, {"base_salary": Decimal("-1")}, "base_salary"),
        (TARGET, [], {}, "previous_base_salary"),
        (TARGET, [], {"previous_base_salary": Decimal("-1")}, "previous_base_salary"),
        (TransferTarget(1001, "재직", HIRED, None, None), [], {}, "start_date"),
    ],
)
def test_fn_hr_010_transfer_rejections(
    target: TransferTarget,
    history: list[HistoryEntry] | None,
    overrides: dict[str, object],
    field: str | None,
) -> None:
    with pytest.raises(WorkforceRuleViolation) as exc:
        plan(target, history, **overrides)
    assert exc.value.field == field


def test_fn_hr_010_leave_of_absence_employee_can_be_transferred() -> None:
    assert plan(TransferTarget(1001, "휴직", HIRED, 10, "STAFF")).new.dept_no == 20


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
        "staff": staff,
        "staff_user": User.objects.create_user(
            email="staff@example.com", password="pw", employee=staff
        ),
    }


def create_employee(employee_no: int, email: str, **fields: object) -> Employee:
    person = Person.objects.create(
        name=f"사원 {employee_no}", birth_date=date(1990, 1, 1), gender="M"
    )
    values = {
        "department_id": 10,
        "position_id": "STAFF",
        "tenure_status": "재직",
        "hire_date": HIRED,
        **fields,
    }
    return Employee.objects.create(employee_no=employee_no, person=person, email=email, **values)


def client_for(user: User | None) -> APIClient:
    client = APIClient()
    if user is not None:
        client.force_authenticate(user)
    return client


def url(employee_no: object) -> str:
    return f"/api/workforce/employees/{employee_no}/history/"


def transfer(**overrides: object) -> dict[str, object]:
    return {
        "start_date": "2026-10-01",
        "dept_no": 20,
        "position_code": "SENIOR",
        "base_salary": "4000000.00",
        **overrides,
    }


def open_history(employee_no: int = 1001) -> EmploymentHistory:
    return EmploymentHistory.objects.create(
        employee_id=employee_no,
        start_date=HIRED,
        department_id=10,
        position_id="STAFF",
        base_salary=Decimal("3000000"),
    )


def test_fn_hr_010_only_hr_manager_can_view_or_register(org: dict) -> None:
    for client in (client_for(org["staff_user"]), client_for(None)):
        assert client.get(url(1001)).status_code in {401, 403}
        assert client.post(url(1001), transfer(), format="json").status_code in {401, 403}
    # 본인 이력도 사원 본인은 조회할 수 없다(본인 조회 범위 제외 결정).
    assert client_for(org["staff_user"]).get(url(1001)).status_code == 403
    assert EmploymentHistory.objects.count() == 0


def test_fn_hr_010_lists_history_newest_first(org: dict) -> None:
    EmploymentHistory.objects.create(
        employee_id=1001,
        start_date=HIRED,
        end_date=date(2023, 12, 31),
        department_id=10,
        position_id="STAFF",
        base_salary=Decimal("3000000"),
    )
    EmploymentHistory.objects.create(
        employee_id=1001,
        start_date=date(2024, 1, 1),
        department_id=20,
        position_id="SENIOR",
        base_salary=Decimal("3500000"),
    )
    response = client_for(org["hr"]).get(url(1001))
    assert response.status_code == 200
    rows = response.json()
    assert [row["start_date"] for row in rows] == ["2024-01-01", "2020-03-01"]
    assert rows[0] == {
        "history_id": rows[0]["history_id"],
        "start_date": "2024-01-01",
        "end_date": None,
        "dept_no": 20,
        "dept_name": "개발팀",
        "position_code": "SENIOR",
        "position_name": "대리",
        "base_salary": "3500000.00",
    }


@pytest.mark.parametrize("employee_no", [5555, "abc"])
def test_fn_hr_010_unknown_employee_is_404(org: dict, employee_no: object) -> None:
    client = client_for(org["hr"])
    assert client.get(url(employee_no)).status_code == 404
    assert client.post(url(employee_no), transfer(), format="json").status_code == 404


def test_fn_hr_010_transfer_closes_history_and_updates_current_assignment(org: dict) -> None:
    previous = open_history()

    response = client_for(org["hr"]).post(url(1001), transfer(), format="json")

    assert response.status_code == 201, response.data
    body = response.json()
    assert [(row["start_date"], row["end_date"]) for row in body["history"]] == [
        ("2026-10-01", None),
        ("2020-03-01", "2026-09-30"),
    ]
    assert body["released_head_dept_nos"] == []
    previous.refresh_from_db()
    assert previous.end_date == date(2026, 9, 30)
    staff = Employee.objects.get(employee_no=1001)
    assert (staff.department_id, staff.position_id) == (20, "SENIOR")


def test_fn_hr_010_first_transfer_records_previous_period(org: dict) -> None:
    response = client_for(org["hr"]).post(
        url(1001), transfer(previous_base_salary="3000000.00"), format="json"
    )

    assert response.status_code == 201, response.data
    rows = EmploymentHistory.objects.filter(employee_id=1001).order_by("start_date")
    assert [
        (r.start_date, r.end_date, r.department_id, r.position_id, r.base_salary) for r in rows
    ] == [
        (HIRED, date(2026, 9, 30), 10, "STAFF", Decimal("3000000.00")),
        (date(2026, 10, 1), None, 20, "SENIOR", Decimal("4000000.00")),
    ]


def test_fn_hr_010_first_transfer_requires_previous_base_salary(org: dict) -> None:
    response = client_for(org["hr"]).post(url(1001), transfer(), format="json")
    assert response.status_code == 400
    assert response.json()["field"] == "previous_base_salary"
    assert EmploymentHistory.objects.count() == 0
    assert Employee.objects.get(employee_no=1001).department_id == 10


def test_fn_hr_010_department_head_is_released_on_department_change(org: dict) -> None:
    open_history()
    Department.objects.filter(dept_no=10).update(head_id=1001)

    response = client_for(org["hr"]).post(url(1001), transfer(), format="json")

    assert response.status_code == 201, response.data
    assert response.json()["released_head_dept_nos"] == [10]
    assert Department.objects.get(dept_no=10).head_id is None


def test_fn_hr_010_department_head_is_kept_on_position_change(org: dict) -> None:
    open_history()
    Department.objects.filter(dept_no=10).update(head_id=1001)

    response = client_for(org["hr"]).post(url(1001), transfer(dept_no=10), format="json")

    assert response.status_code == 201, response.data
    assert response.json()["released_head_dept_nos"] == []
    assert Department.objects.get(dept_no=10).head_id == 1001


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"start_date": (timezone.localdate() + timedelta(days=1)).isoformat()}, "start_date"),
        ({"start_date": "2020-03-01"}, "start_date"),
        ({"dept_no": 10, "position_code": "STAFF"}, None),
        ({"dept_no": 99}, "dept_no"),
        ({"position_code": "NOPE"}, "position_code"),
    ],
)
def test_fn_hr_010_rule_rejections_change_nothing(
    org: dict, overrides: dict[str, object], field: str | None
) -> None:
    previous = open_history()
    response = client_for(org["hr"]).post(url(1001), transfer(**overrides), format="json")
    assert response.status_code == 400
    assert response.json().get("field") == field
    previous.refresh_from_db()
    assert previous.end_date is None
    assert EmploymentHistory.objects.count() == 1
    assert Employee.objects.get(employee_no=1001).department_id == 10


@pytest.mark.parametrize(
    "overrides",
    [
        {"start_date": None},
        {"base_salary": None},
        {"base_salary": "-1"},
        {"previous_base_salary": "-1"},
        {"dept_no": "x"},
    ],
)
def test_fn_hr_010_rejects_invalid_input(org: dict, overrides: dict[str, object]) -> None:
    open_history()
    response = client_for(org["hr"]).post(url(1001), transfer(**overrides), format="json")
    assert response.status_code == 400
    assert EmploymentHistory.objects.count() == 1


def test_fn_hr_010_terminated_employee_cannot_be_transferred(org: dict) -> None:
    create_employee(1002, "retired@example.com", tenure_status="퇴사", term_date=date(2025, 1, 1))
    response = client_for(org["hr"]).post(
        url(1002), transfer(previous_base_salary="0"), format="json"
    )
    assert response.status_code == 400
    assert EmploymentHistory.objects.filter(employee_id=1002).count() == 0


def test_fn_hr_010_failure_after_closing_rolls_back(
    org: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    previous = open_history()

    def boom(self: object, employee_no: int, **kwargs: object) -> None:
        raise RuntimeError("update failed")

    monkeypatch.setattr(DjangoEmploymentHistoryRepository, "update_current_assignment", boom)
    with pytest.raises(RuntimeError):
        client_for(org["hr"]).post(url(1001), transfer(), format="json")

    previous.refresh_from_db()
    assert previous.end_date is None
    assert EmploymentHistory.objects.count() == 1


def test_fn_hr_010_transfer_after_new_hire_registration(org: dict) -> None:
    client = client_for(org["hr"])
    hired = client.post(
        "/api/workforce/new-hires/",
        {
            "name": "신입",
            "birth_date": "1998-01-01",
            "gender": "F",
            "email": "new@example.com",
            "hire_date": "2026-09-01",
            "dept_no": 10,
            "position_code": "STAFF",
            "base_salary": "3000000",
        },
        format="json",
    )
    assert hired.status_code == 201, hired.data
    employee_no = hired.json()["emp_no"]

    response = client.post(url(employee_no), transfer(), format="json")

    assert response.status_code == 201, response.data
    assert [(row["start_date"], row["end_date"]) for row in response.json()["history"]] == [
        ("2026-10-01", None),
        ("2026-09-01", "2026-09-30"),
    ]


def test_fn_hr_010_evaluation_reads_assignment_before_and_after_transfer(org: dict) -> None:
    from evaluation.infrastructure.workforce_gateways import DjangoWorkforceGateway

    # 이력 없는 사원의 첫 발령: 이전 기간이 기록되어 과거 기준일은 이전 부서로 판정된다.
    response = client_for(org["hr"]).post(
        url(1001), transfer(previous_base_salary="3000000"), format="json"
    )
    assert response.status_code == 201, response.data

    gateway = DjangoWorkforceGateway()
    before = gateway.evaluation_target(1001, date(2025, 12, 31))
    after = gateway.evaluation_target(1001, date(2026, 10, 1))
    assert (before.department_no, before.position_code) == (10, "STAFF")
    assert (after.department_no, after.position_code) == (20, "SENIOR")
