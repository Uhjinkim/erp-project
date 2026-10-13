from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.lifecycle import EmployeeNotFound, EmploymentLifecycleService
from workforce.application.services import HR_LEAVE_APPROVER_ROLE, HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.lifecycle import (
    EmploymentState,
    RetiredEmployee,
    RetiredEmployeeCriteria,
    ensure_rehire_allowed,
    validate_termination,
)
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    EmploymentHistory,
    Person,
    PersonalInfoChangeRequest,
    Position,
    Role,
)

TODAY = date(2026, 10, 13)
ACTIVE = EmploymentState(1001, "재직", date(2020, 1, 1), None)


# --- domain ---------------------------------------------------------------------------------


def test_hr_009_termination_accepts_today_or_past_after_hire_date() -> None:
    validate_termination(ACTIVE, term_date=TODAY, today=TODAY)
    validate_termination(ACTIVE, term_date=date(2020, 1, 1), today=TODAY)
    validate_termination(
        EmploymentState(1001, "휴직", date(2020, 1, 1), None), term_date=TODAY, today=TODAY
    )


@pytest.mark.parametrize(
    ("state", "term_date", "field"),
    [
        (ACTIVE, TODAY + timedelta(days=1), "term_date"),
        (ACTIVE, date(2019, 12, 31), "term_date"),
        (EmploymentState(1001, "퇴사", date(2020, 1, 1), date(2025, 1, 1)), TODAY, None),
    ],
)
def test_hr_009_termination_rejections(
    state: EmploymentState, term_date: date, field: str | None
) -> None:
    with pytest.raises(WorkforceRuleViolation) as exc:
        validate_termination(state, term_date=term_date, today=TODAY)
    assert exc.value.field == field


def test_hr_006_rehire_requires_all_prior_employments_terminated() -> None:
    retired = EmploymentState(900, "퇴사", date(2020, 1, 1), date(2025, 12, 31))
    ensure_rehire_allowed([retired], hire_date=date(2026, 1, 1))
    for prior, hire_date in (
        ([], date(2026, 1, 1)),
        ([retired, ACTIVE], date(2026, 1, 1)),
        ([retired], date(2025, 12, 31)),
    ):
        with pytest.raises(WorkforceRuleViolation):
            ensure_rehire_allowed(prior, hire_date=hire_date)


# --- application ----------------------------------------------------------------------------


class FakeLifecycleRepository:
    def __init__(self, *states: EmploymentState) -> None:
        self.states = {state.employee_no: state for state in states}
        self.terminated: list[tuple[int, date]] = []
        self.criteria: RetiredEmployeeCriteria | None = None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        yield

    def lock_employment(self, employee_no: int) -> EmploymentState | None:
        return self.states.get(employee_no)

    def terminate(self, employee_no: int, term_date: date) -> None:
        self.terminated.append((employee_no, term_date))

    def retired_employees(self, criteria: RetiredEmployeeCriteria) -> list[RetiredEmployee]:
        self.criteria = criteria
        return []


def make_lifecycle(repository: FakeLifecycleRepository) -> EmploymentLifecycleService:
    return EmploymentLifecycleService(repository, repository, lambda: TODAY)


def test_fn_hr_007_terminate_records_status_and_date_only() -> None:
    repository = FakeLifecycleRepository(ACTIVE)
    make_lifecycle(repository).terminate(1001, TODAY)
    assert repository.terminated == [(1001, TODAY)]


def test_fn_hr_007_terminate_unknown_or_invalid_writes_nothing() -> None:
    repository = FakeLifecycleRepository(ACTIVE)
    with pytest.raises(EmployeeNotFound):
        make_lifecycle(repository).terminate(9999, TODAY)
    with pytest.raises(WorkforceRuleViolation):
        make_lifecycle(repository).terminate(1001, TODAY + timedelta(days=1))
    assert repository.terminated == []


def test_fn_hr_008_rejects_reversed_term_date_range() -> None:
    repository = FakeLifecycleRepository()
    criteria = RetiredEmployeeCriteria(term_date_from=TODAY, term_date_to=date(2026, 1, 1))
    with pytest.raises(WorkforceRuleViolation) as exc:
        make_lifecycle(repository).list_retired(criteria)
    assert exc.value.field == "term_date_from"
    assert repository.criteria is None


# --- API ------------------------------------------------------------------------------------


@pytest.fixture
def org(db: None) -> dict[str, object]:
    sales = Department.objects.create(dept_no=10, dept_name="영업팀")
    Department.objects.create(dept_no=20, dept_name="개발팀")
    Position.objects.create(position_code="STAFF", position_name="사원", sort_order=1)
    for code in (HR_MANAGER_ROLE, HR_LEAVE_APPROVER_ROLE):
        Role.objects.create(role_code=code, role_name=code)
    hr = create_employee(9001, "hr@example.com", dept_no=10)
    EmployeeRole.objects.create(employee=hr, role_id=HR_MANAGER_ROLE, assigned_at=timezone.now())
    staff = create_employee(1001, "staff@example.com", dept_no=10, name="홍길동")
    return {
        "dept": sales,
        "hr": User.objects.create_user(email="hr@example.com", password="pw", employee=hr),
        "staff": staff,
        "staff_user": User.objects.create_user(
            email="staff@example.com", password="Staff!2026x", employee=staff
        ),
    }


def create_employee(
    employee_no: int,
    email: str,
    *,
    dept_no: int,
    name: str | None = None,
    term_date: date | None = None,
    person: Person | None = None,
) -> Employee:
    person = person or Person.objects.create(
        name=name or f"사원 {employee_no}", birth_date=date(1990, 1, 1), gender="M"
    )
    return Employee.objects.create(
        employee_no=employee_no,
        person=person,
        department_id=dept_no,
        position_id="STAFF",
        tenure_status="퇴사" if term_date else "재직",
        email=email,
        hire_date=date(2020, 1, 1),
        term_date=term_date,
        account_no="1234567890",
    )


def hr_client(org: dict) -> APIClient:
    client = APIClient()
    client.force_authenticate(org["hr"])
    return client


def staff_client(org: dict) -> APIClient:
    client = APIClient()
    client.force_authenticate(org["staff_user"])
    return client


def terminate_url(employee_no: object) -> str:
    return f"/api/workforce/employees/{employee_no}/terminate/"


def test_fn_hr_007_only_hr_manager_can_terminate(org: dict) -> None:
    other = create_employee(1002, "other@example.com", dept_no=10)
    response = staff_client(org).post(terminate_url(1002), {"term_date": "2026-10-01"})
    assert response.status_code == 403
    assert APIClient().post(terminate_url(1002), {"term_date": "2026-10-01"}).status_code in {
        401,
        403,
    }
    other.refresh_from_db()
    assert other.tenure_status == "재직"


def test_fn_hr_007_terminate_blocks_access_and_preserves_records(org: dict) -> None:
    staff = org["staff"]
    # 부서장 지정, 역할, 인사이력, 대기 중 변경 요청이 있는 사원을 퇴사 처리한다.
    Department.objects.filter(dept_no=10).update(head=staff)
    role = EmployeeRole.objects.create(
        employee=staff, role_id=HR_LEAVE_APPROVER_ROLE, assigned_at=timezone.now()
    )
    history = EmploymentHistory.objects.create(
        employee=staff,
        start_date=date(2020, 1, 1),
        department_id=10,
        position_id="STAFF",
        base_salary=0,
    )
    change_request = PersonalInfoChangeRequest.objects.create(
        employee=staff, requested_email="new@example.com", requested_at=timezone.now()
    )

    response = hr_client(org).post(terminate_url(1001), {"term_date": "2026-10-01"})

    assert response.status_code == 200, response.data
    assert response.json()["tenure_status"] == "퇴사"
    assert response.json()["term_date"] == "2026-10-01"
    staff.refresh_from_db()
    assert (staff.tenure_status, staff.term_date) == ("퇴사", date(2026, 10, 1))
    # HR-004: 연결 계정이 비활성화되어 로그인할 수 없다.
    org["staff_user"].refresh_from_db()
    assert org["staff_user"].is_active is False
    login = APIClient().post(
        "/api/auth/login/", {"email": "staff@example.com", "password": "Staff!2026x"}
    )
    assert login.status_code == 400
    # HR-005: 다른 기록은 그대로 보존한다.
    role.refresh_from_db()
    history.refresh_from_db()
    change_request.refresh_from_db()
    assert role.revoked_at is None
    assert history.end_date is None
    assert change_request.status == "대기"
    assert Department.objects.get(dept_no=10).head_id == 1001


@pytest.mark.parametrize(
    ("employee_no", "body", "status_code"),
    [
        (1001, {"term_date": (timezone.localdate() + timedelta(days=1)).isoformat()}, 400),
        (1001, {"term_date": "2019-12-31"}, 400),
        (1001, {}, 400),
        (1001, {"term_date": "not-a-date"}, 400),
        (5555, {"term_date": "2026-10-01"}, 404),
        ("abc", {"term_date": "2026-10-01"}, 404),
    ],
)
def test_fn_hr_007_terminate_rejects_invalid_requests(
    org: dict, employee_no: object, body: dict, status_code: int
) -> None:
    response = hr_client(org).post(terminate_url(employee_no), body, format="json")
    assert response.status_code == status_code
    org["staff"].refresh_from_db()
    assert org["staff"].tenure_status == "재직"


def test_fn_hr_007_cannot_terminate_twice(org: dict) -> None:
    create_employee(1002, "retired@example.com", dept_no=10, term_date=date(2025, 1, 1))
    response = hr_client(org).post(terminate_url(1002), {"term_date": "2026-10-01"})
    assert response.status_code == 400
    assert Employee.objects.get(employee_no=1002).term_date == date(2025, 1, 1)


RETIRED_URL = "/api/workforce/employees/terminated/"


@pytest.fixture
def retired(org: dict) -> None:
    for employee_no, email, dept_no, name, term_date in (
        (2001, "kim@example.com", 10, "김퇴사", date(2025, 3, 31)),
        (2002, "lee@example.com", 20, "이퇴사", date(2026, 6, 30)),
        (2003, "park@example.com", 20, "박퇴사", date(2024, 1, 15)),
    ):
        create_employee(employee_no, email, dept_no=dept_no, name=name, term_date=term_date)


def test_fn_hr_008_only_hr_manager_can_list_retired(org: dict, retired: None) -> None:
    assert staff_client(org).get(RETIRED_URL).status_code == 403
    assert APIClient().get(RETIRED_URL).status_code in {401, 403}


def test_fn_hr_008_lists_only_retired_employees_newest_first(org: dict, retired: None) -> None:
    response = hr_client(org).get(RETIRED_URL)
    assert response.status_code == 200
    rows = response.json()
    assert [row["emp_no"] for row in rows] == [2002, 2001, 2003]
    assert rows[0] == {
        "emp_no": 2002,
        "person_id": rows[0]["person_id"],
        "name": "이퇴사",
        "dept_no": 20,
        "dept_name": "개발팀",
        "position_code": "STAFF",
        "position_name": "사원",
        "email": "lee@example.com",
        "hire_date": "2020-01-01",
        "term_date": "2026-06-30",
    }
    # 급여계좌는 목록에 노출하지 않는다.
    assert "account_no" not in rows[0]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ({"name": "김"}, [2001]),
        ({"name": "  "}, [2002, 2001, 2003]),
        ({"dept_no": 20}, [2002, 2003]),
        ({"emp_no": 2003}, [2003]),
        ({"term_date_from": "2025-01-01"}, [2002, 2001]),
        ({"term_date_to": "2025-03-31"}, [2001, 2003]),
        ({"term_date_from": "2025-01-01", "term_date_to": "2025-12-31"}, [2001]),
        ({"name": "홍길동"}, []),
    ],
)
def test_fn_hr_008_filters_retired_employees(
    org: dict, retired: None, query: dict, expected: list[int]
) -> None:
    response = hr_client(org).get(RETIRED_URL, query)
    assert response.status_code == 200
    assert [row["emp_no"] for row in response.json()] == expected


@pytest.mark.parametrize(
    "query",
    [
        {"term_date_from": "2026-01-01", "term_date_to": "2025-01-01"},
        {"term_date_from": "bad"},
        {"dept_no": "x"},
    ],
)
def test_fn_hr_008_rejects_invalid_filters(org: dict, retired: None, query: dict) -> None:
    assert hr_client(org).get(RETIRED_URL, query).status_code == 400


def rehire_url(person_id: int) -> str:
    return f"/api/workforce/persons/{person_id}/rehire/"


def rehire_payload(**overrides: object) -> dict[str, object]:
    return {
        "email": "rehired@example.com",
        "hire_date": "2026-10-15",
        "dept_no": 20,
        "position_code": "STAFF",
        "base_salary": "3500000.00",
        "account": {"password": "Welcome!2026x"},
        **overrides,
    }


@pytest.fixture
def former(org: dict) -> Employee:
    employee = create_employee(
        2001, "former@example.com", dept_no=10, name="재입사자", term_date=date(2025, 12, 31)
    )
    User.objects.create_user(
        email="former@example.com", password="Old!2026x", employee=employee, is_active=False
    )
    return employee


def test_fn_hr_009_only_hr_manager_can_rehire(org: dict, former: Employee) -> None:
    before = Employee.objects.count()
    response = staff_client(org).post(
        rehire_url(former.person_id), rehire_payload(), format="json"
    )
    assert response.status_code == 403
    assert Employee.objects.count() == before


def test_fn_hr_009_rehire_issues_new_employee_no_for_same_person(
    org: dict, former: Employee
) -> None:
    response = hr_client(org).post(
        rehire_url(former.person_id), rehire_payload(name="재입사자(개명)"), format="json"
    )

    assert response.status_code == 201, response.data
    body = response.json()
    # HR-006: 새 사번을 발급하고 이전 사번을 재사용하지 않는다.
    assert body["emp_no"] != former.employee_no
    assert body["emp_no"] > 9001
    assert body["person_id"] == former.person_id
    assert body["name"] == "재입사자(개명)"
    new_employee = Employee.objects.get(employee_no=body["emp_no"])
    assert new_employee.is_active_employee
    assert new_employee.department_id == 20
    assert EmploymentHistory.objects.filter(employee=new_employee).count() == 1
    # 이전 고용과 계정은 그대로 보존된다(HR-005).
    former.refresh_from_db()
    assert (former.tenure_status, former.email) == ("퇴사", "former@example.com")
    assert User.objects.get(email="former@example.com").is_active is False
    # 새 계정으로 로그인할 수 있다.
    login = APIClient().post(
        "/api/auth/login/", {"email": "rehired@example.com", "password": "Welcome!2026x"}
    )
    assert login.status_code == 200
    assert login.json()["employee"]["emp_no"] == body["emp_no"]


def test_fn_hr_009_rehire_keeps_person_values_when_omitted(org: dict, former: Employee) -> None:
    response = hr_client(org).post(
        rehire_url(former.person_id), rehire_payload(account=None), format="json"
    )
    assert response.status_code == 201, response.data
    assert response.json()["name"] == "재입사자"
    person = Person.objects.get(person_id=former.person_id)
    assert (person.name, person.birth_date, person.gender) == ("재입사자", date(1990, 1, 1), "M")


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"email": "former@example.com"}, "email"),
        ({"hire_date": "2025-12-31"}, "hire_date"),
        ({"dept_no": 99}, "dept_no"),
    ],
)
def test_fn_hr_009_rehire_rejections_leave_no_rows(
    org: dict, former: Employee, overrides: dict, field: str
) -> None:
    before = (Employee.objects.count(), User.objects.count(), EmploymentHistory.objects.count())
    response = hr_client(org).post(
        rehire_url(former.person_id), rehire_payload(**overrides), format="json"
    )
    assert response.status_code == 400
    assert response.json()["field"] == field
    after = (Employee.objects.count(), User.objects.count(), EmploymentHistory.objects.count())
    assert after == before


def test_fn_hr_009_active_person_cannot_be_rehired(org: dict) -> None:
    response = hr_client(org).post(
        rehire_url(org["staff"].person_id), rehire_payload(), format="json"
    )
    assert response.status_code == 400
    assert response.json()["field"] == "person_id"


def test_fn_hr_009_unknown_person_and_invalid_input(org: dict, former: Employee) -> None:
    client = hr_client(org)
    assert client.post(rehire_url(99999), rehire_payload(), format="json").status_code == 400
    response = client.post(rehire_url(former.person_id), rehire_payload(gender="X"), format="json")
    assert response.status_code == 400
    assert "gender" in response.json()
    response = client.post(
        rehire_url(former.person_id), rehire_payload(emp_no=2001), format="json"
    )
    assert response.status_code == 400
    assert "emp_no" in response.json()


def test_fn_hr_009_terminated_then_rehired_flow(org: dict) -> None:
    client = hr_client(org)
    assert client.post(terminate_url(1001), {"term_date": "2026-10-01"}).status_code == 200

    retired = client.get(RETIRED_URL).json()
    assert [row["emp_no"] for row in retired] == [1001]

    response = client.post(
        rehire_url(org["staff"].person_id),
        rehire_payload(hire_date="2026-10-02", account=None),
        format="json",
    )
    assert response.status_code == 201, response.data
    assert Person.objects.get(person_id=org["staff"].person_id).employments.count() == 2
    # 재입사 후에도 이전 고용은 퇴사자 목록에 남는다.
    assert [row["emp_no"] for row in client.get(RETIRED_URL).json()] == [1001]
