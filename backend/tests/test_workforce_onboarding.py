import copy
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.onboarding import (
    AccountCreationFailed,
    DuplicateEmail,
    EmployeeNoSequenceOutOfSync,
    NewHireAccount,
    NewHireRegistrationService,
    RegisterNewHireCommand,
    RegistrationConflict,
    RegistrationRetryExhausted,
    RehireCommand,
)
from workforce.application.services import HR_LEAVE_APPROVER_ROLE, HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.lifecycle import EmploymentState
from workforce.domain.onboarding import (
    EmploymentPeriod,
    ensure_no_period_overlap,
    validate_new_hire,
)
from workforce.infrastructure.accounts import DjangoAccountGateway
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    EmploymentHistory,
    Person,
    Position,
    Role,
)
from workforce.infrastructure.onboarding import DjangoNewHireUnitOfWork

URL = "/api/workforce/new-hires/"
PASSWORD = "Welcome!2026x"


# --- domain ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"name": "  "}, "name"),
        ({"gender": "X"}, "gender"),
        ({"gender": ""}, "gender"),
        ({"email": " "}, "email"),
        ({"base_salary": Decimal("-1")}, "base_salary"),
        ({"role_codes": ("HR_MANAGER", "HR_MANAGER")}, "role_codes"),
    ],
)
def test_hr_008_new_hire_requires_valid_values(overrides: dict[str, object], field: str) -> None:
    values = {
        "name": "신입",
        "gender": "M",
        "email": "new@example.com",
        "base_salary": Decimal("0"),
        "role_codes": (),
    }
    with pytest.raises(WorkforceRuleViolation) as exc:
        validate_new_hire(**{**values, **overrides})
    assert exc.value.field == field


JAN, MAR_END, APR, APR_END, MAY = (
    date(2026, 1, 1), date(2026, 3, 31), date(2026, 4, 1), date(2026, 4, 30), date(2026, 5, 1)
)


@pytest.mark.parametrize(
    ("existing", "new", "overlaps"),
    [
        (EmploymentPeriod(JAN, MAR_END), EmploymentPeriod(APR), False),
        (EmploymentPeriod(JAN, APR), EmploymentPeriod(APR), True),
        (EmploymentPeriod(JAN), EmploymentPeriod(APR), True),
        (EmploymentPeriod(MAY), EmploymentPeriod(APR, APR_END), False),
        (EmploymentPeriod(MAY), EmploymentPeriod(APR), True),
    ],
)
def test_hr_010_history_periods_cannot_overlap(
    existing: EmploymentPeriod, new: EmploymentPeriod, overlaps: bool
) -> None:
    assert existing.overlaps(new) is overlaps
    if overlaps:
        with pytest.raises(WorkforceRuleViolation):
            ensure_no_period_overlap([existing], new)
    else:
        ensure_no_period_overlap([existing], new)


def test_hr_010_history_end_cannot_precede_start() -> None:
    with pytest.raises(WorkforceRuleViolation):
        ensure_no_period_overlap([], EmploymentPeriod(date(2026, 4, 1), date(2026, 3, 1)))


# --- application ----------------------------------------------------------------------------


class FakeWorkforceDatabase:
    """NewHireUnitOfWork·AccountGateway·RoleCommandGateway를 함께 구현하는 인메모리 저장소.

    transaction() 안에서 예외가 나면 진입 시점 상태로 되돌린다.
    """

    def __init__(self) -> None:
        self.state: dict[str, object] = {
            "departments": {10},
            "positions": {"STAFF"},
            "roles": {HR_MANAGER_ROLE, HR_LEAVE_APPROVER_ROLE},
            "persons": {},
            "employees": {},
            "history": {},
            "assignments": {},
            "accounts": {},
        }
        # DB 시퀀스처럼 롤백되어도 되돌아가지 않는다.
        self.next_employee_no = 1001
        self.conflicts_remaining = 0
        self.account_failure: Exception | None = None

    def _table(self, name: str) -> dict:
        return self.state[name]

    @contextmanager
    def transaction(self) -> Iterator[None]:
        snapshot = copy.deepcopy(self.state)
        try:
            yield
        except BaseException:
            self.state = snapshot
            raise

    def department_exists(self, dept_no: int) -> bool:
        return dept_no in self.state["departments"]

    def position_exists(self, position_code: str) -> bool:
        return position_code in self.state["positions"]

    def missing_role_codes(self, role_codes: tuple[str, ...]) -> set[str]:
        return set(role_codes) - self.state["roles"]

    def employee_email_in_use(self, email: str) -> bool:
        return any(e["email"] == email for e in self._table("employees").values())

    def add_person(self, *, name: str, birth_date: date, gender: str) -> int:
        person_id = len(self._table("persons")) + 1
        self._table("persons")[person_id] = name
        return person_id

    def lock_person_employments(self, person_id: int) -> list[EmploymentState] | None:
        if person_id not in self._table("persons"):
            return None
        return [
            EmploymentState(
                no, row.get("tenure_status", "재직"), row["hire_date"], row.get("term_date")
            )
            for no, row in self._table("employees").items()
            if row.get("person_id") == person_id
        ]

    def person_name(self, person_id: int) -> str:
        return self._table("persons")[person_id]

    def update_person(self, person_id: int, *, name: str | None, **values: object) -> None:
        if name is not None:
            self._table("persons")[person_id] = name

    def add_employee(self, **values: object) -> int:
        employee_no = self.next_employee_no
        self.next_employee_no += 1
        if self.conflicts_remaining:
            self.conflicts_remaining -= 1
            raise RegistrationConflict("simulated concurrent insert")
        self._table("employees")[employee_no] = values
        return employee_no

    def history_periods(self, employee_no: int) -> list[EmploymentPeriod]:
        return [
            item["period"] for item in self._table("history").values()
            if item["employee_no"] == employee_no
        ]

    def add_history(self, *, employee_no: int, period: EmploymentPeriod, **values: object) -> int:
        history_id = len(self._table("history")) + 1
        self._table("history")[history_id] = {
            "employee_no": employee_no, "period": period, **values
        }
        return history_id

    # RoleCommandGateway
    def employee_is_active(self, employee_no: int) -> bool:
        return employee_no in self._table("employees")

    def has_active_assignment(self, employee_no: int, role_code: str) -> bool:
        return (employee_no, role_code) in self._table("assignments").values()

    def active_role_holder_count(self, role_code: str) -> int:
        return sum(1 for _, code in self._table("assignments").values() if code == role_code)

    def assign_role(self, employee_no: int, role_code: str) -> int:
        assignment_id = len(self._table("assignments")) + 1
        self._table("assignments")[assignment_id] = (employee_no, role_code)
        return assignment_id

    def revoke_role(self, employee_no: int, assignment_id: int) -> bool:
        return False

    # AccountGateway
    def email_in_use(self, email: str) -> bool:
        return email in self._table("accounts").values()

    def create_account(self, *, email: str, password: str, employee_no: int) -> int:
        if self.account_failure is not None:
            raise self.account_failure
        account_id = len(self._table("accounts")) + 1
        self._table("accounts")[account_id] = email
        return account_id


def make_command(**overrides: object) -> RegisterNewHireCommand:
    values: dict[str, object] = {
        "name": "신입 사원",
        "birth_date": date(1998, 3, 1),
        "gender": "F",
        "email": "new.hire@example.com",
        "hire_date": date(2026, 10, 15),
        "dept_no": 10,
        "position_code": "STAFF",
        "base_salary": Decimal("3200000.00"),
        "role_codes": (HR_MANAGER_ROLE,),
        "account": NewHireAccount(PASSWORD),
    }
    return RegisterNewHireCommand(**{**values, **overrides})


def make_service(db: FakeWorkforceDatabase) -> NewHireRegistrationService:
    return NewHireRegistrationService(db, db, db)


def written_rows(db: FakeWorkforceDatabase) -> int:
    return sum(
        len(db.state[name])
        for name in ("persons", "employees", "history", "assignments", "accounts")
    )


def test_fn_hr_006_registers_person_employee_history_roles_and_account() -> None:
    db = FakeWorkforceDatabase()

    result = make_service(db).register(make_command())

    assert result.employee_no == 1001
    assert db.state["employees"][1001]["email"] == "new.hire@example.com"
    history = db.state["history"][result.history_id]
    assert history["period"] == EmploymentPeriod(date(2026, 10, 15))
    assert (history["dept_no"], history["position_code"]) == (10, "STAFF")
    assert history["base_salary"] == Decimal("3200000.00")
    assert [item.role_code for item in result.role_assignments] == [HR_MANAGER_ROLE]
    assert db.state["accounts"][result.account_id] == "new.hire@example.com"


def test_fn_hr_006_account_is_optional() -> None:
    db = FakeWorkforceDatabase()
    result = make_service(db).register(make_command(account=None, role_codes=()))
    assert result.account_id is None
    assert result.role_assignments == ()
    assert db.state["accounts"] == {}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"dept_no": 99}, "dept_no"),
        ({"position_code": "NOPE"}, "position_code"),
        ({"role_codes": ("NOPE",)}, "role_codes"),
    ],
)
def test_fn_hr_006_rejects_unknown_references(overrides: dict[str, object], field: str) -> None:
    db = FakeWorkforceDatabase()
    with pytest.raises(WorkforceRuleViolation) as exc:
        make_service(db).register(make_command(**overrides))
    assert exc.value.field == field
    assert written_rows(db) == 0


@pytest.mark.parametrize("table", ["employees", "accounts"])
def test_hr_008_rejects_email_used_by_employee_or_login_account(table: str) -> None:
    db = FakeWorkforceDatabase()
    if table == "employees":
        db.state["employees"][1] = {"email": "new.hire@example.com"}
    else:
        db.state["accounts"][1] = "new.hire@example.com"
    before = written_rows(db)

    with pytest.raises(DuplicateEmail):
        make_service(db).register(make_command())
    assert written_rows(db) == before


def test_fn_hr_006_account_failure_rolls_back_every_step() -> None:
    db = FakeWorkforceDatabase()
    db.account_failure = AccountCreationFailed("weak", field="account.password")

    with pytest.raises(AccountCreationFailed):
        make_service(db).register(make_command())
    assert written_rows(db) == 0


def test_fn_hr_006_role_rule_failure_rolls_back_every_step() -> None:
    db = FakeWorkforceDatabase()
    db.state["employees"][7] = {"email": "approver@example.com"}
    db.state["assignments"][1] = (7, HR_LEAVE_APPROVER_ROLE)
    before = written_rows(db)

    with pytest.raises(WorkforceRuleViolation):
        make_service(db).register(make_command(role_codes=(HR_LEAVE_APPROVER_ROLE,)))
    assert written_rows(db) == before


def test_fn_hr_006_retries_after_concurrent_registration_conflict() -> None:
    db = FakeWorkforceDatabase()
    db.conflicts_remaining = 2

    result = make_service(db).register(make_command())

    # 실패한 시도가 소비한 사번은 건너뛴다.
    assert result.employee_no == 1003
    assert len(db.state["persons"]) == 1


def test_fn_hr_006_gives_up_after_repeated_conflicts() -> None:
    db = FakeWorkforceDatabase()
    db.conflicts_remaining = NewHireRegistrationService.MAX_ATTEMPTS

    with pytest.raises(RegistrationRetryExhausted):
        make_service(db).register(make_command())
    assert written_rows(db) == 0


def seed_retired_person(db: FakeWorkforceDatabase, **employment: object) -> int:
    db.state["persons"][1] = "퇴사자"
    db.state["employees"][900] = {
        "person_id": 1,
        "email": "former@example.com",
        "tenure_status": "퇴사",
        "hire_date": date(2020, 1, 1),
        "term_date": date(2025, 12, 31),
        **employment,
    }
    return 1


def make_rehire(**overrides: object) -> RehireCommand:
    values: dict[str, object] = {
        "person_id": 1,
        "email": "rehired@example.com",
        "hire_date": date(2026, 10, 15),
        "dept_no": 10,
        "position_code": "STAFF",
        "base_salary": Decimal("3500000.00"),
        "account": NewHireAccount(PASSWORD),
    }
    return RehireCommand(**{**values, **overrides})


def test_fn_hr_009_rehire_adds_new_employee_no_to_same_person() -> None:
    db = FakeWorkforceDatabase()
    seed_retired_person(db)

    result = make_service(db).rehire(make_rehire())

    # HR-006: 이전 사번(900)을 재사용하지 않는다.
    assert result.employee_no == 1001
    assert result.person_id == 1
    assert result.name == "퇴사자"
    assert db.state["employees"][900]["tenure_status"] == "퇴사"
    assert db.state["employees"][1001]["email"] == "rehired@example.com"
    assert db.state["history"][result.history_id]["period"] == EmploymentPeriod(date(2026, 10, 15))
    assert db.state["accounts"][result.account_id] == "rehired@example.com"


def test_fn_hr_009_rehire_updates_person_values_when_given() -> None:
    db = FakeWorkforceDatabase()
    seed_retired_person(db)

    result = make_service(db).rehire(make_rehire(name=" 개명자 ", gender="F"))

    assert result.name == "개명자"
    assert db.state["persons"][1] == "개명자"


@pytest.mark.parametrize(
    ("employment", "overrides", "field"),
    [
        ({"tenure_status": "재직", "term_date": None}, {}, "person_id"),
        ({"tenure_status": "휴직", "term_date": None}, {}, "person_id"),
        ({}, {"hire_date": date(2025, 12, 31)}, "hire_date"),
        ({}, {"person_id": 77}, "person_id"),
        ({}, {"email": "former@example.com"}, "email"),
        ({}, {"gender": "X"}, "gender"),
    ],
)
def test_fn_hr_009_rehire_rejections_leave_no_rows(
    employment: dict[str, object], overrides: dict[str, object], field: str
) -> None:
    db = FakeWorkforceDatabase()
    seed_retired_person(db, **employment)
    before = written_rows(db)

    with pytest.raises(WorkforceRuleViolation) as exc:
        make_service(db).rehire(make_rehire(**overrides))
    assert exc.value.field == field
    assert written_rows(db) == before


def test_fn_hr_009_person_without_employment_is_not_a_rehire() -> None:
    db = FakeWorkforceDatabase()
    db.state["persons"][1] = "고용 이력 없음"

    with pytest.raises(WorkforceRuleViolation) as exc:
        make_service(db).rehire(make_rehire())
    assert exc.value.field == "person_id"


def test_fn_hr_009_second_rehire_is_rejected_while_first_is_active() -> None:
    db = FakeWorkforceDatabase()
    seed_retired_person(db)
    make_service(db).rehire(make_rehire())

    with pytest.raises(WorkforceRuleViolation):
        make_service(db).rehire(make_rehire(email="again@example.com"))


# --- API ------------------------------------------------------------------------------------


@pytest.fixture
def org(db: None) -> dict[str, object]:
    department = Department.objects.create(dept_no=10, dept_name="인사팀")
    Position.objects.create(position_code="STAFF", position_name="사원", sort_order=1)
    for code in (HR_MANAGER_ROLE, HR_LEAVE_APPROVER_ROLE):
        Role.objects.create(role_code=code, role_name=code)
    hr = create_employee(9001, "hr@example.com", department)
    EmployeeRole.objects.create(
        employee=hr, role_id=HR_MANAGER_ROLE, assigned_at=timezone.now()
    )
    staff = create_employee(1001, "staff@example.com", department)
    return {
        "hr": User.objects.create_user(email="hr@example.com", password="pw", employee=hr),
        "staff": User.objects.create_user(
            email="staff@example.com", password="pw", employee=staff
        ),
    }


def create_employee(employee_no: int, email: str, department: Department) -> Employee:
    person = Person.objects.create(
        name=f"사원 {employee_no}", birth_date=date(1990, 1, 1), gender="M"
    )
    return Employee.objects.create(
        employee_no=employee_no,
        person=person,
        department=department,
        position_id="STAFF",
        tenure_status=Employee.TenureStatus.ACTIVE,
        email=email,
        hire_date=date(2020, 1, 1),
    )


def payload(**overrides: object) -> dict[str, object]:
    return {
        "name": "신입 사원",
        "birth_date": "1998-03-01",
        "gender": "F",
        "email": "New.Hire@Example.com",
        "hire_date": "2026-10-15",
        "dept_no": 10,
        "position_code": "STAFF",
        "phone": "010-0000-0000",
        "base_salary": "3200000.00",
        "role_codes": [HR_MANAGER_ROLE],
        "account": {"password": PASSWORD},
        **overrides,
    }


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def counts() -> tuple[int, ...]:
    return (
        Person.objects.count(),
        Employee.objects.count(),
        EmploymentHistory.objects.count(),
        EmployeeRole.objects.count(),
        User.objects.count(),
    )


def test_fn_hr_006_regular_employee_and_anonymous_cannot_register(org: dict) -> None:
    before = counts()
    assert client_for(org["staff"]).post(URL, payload(), format="json").status_code == 403
    assert APIClient().post(URL, payload(), format="json").status_code in {401, 403}
    assert counts() == before


def test_fn_hr_006_hr_manager_registers_new_hire(org: dict) -> None:
    response = client_for(org["hr"]).post(URL, payload(), format="json")

    assert response.status_code == 201, response.data
    body = response.json()
    assert body["emp_no"] == 9002
    assert body["email"] == "new.hire@example.com"
    assert body["tenure_status"] == "재직"
    assert body["account"] == {"id": body["account"]["id"], "email": "new.hire@example.com"}
    assert [role["role_code"] for role in body["roles"]] == [HR_MANAGER_ROLE]
    assert "password" not in str(body)

    employee = Employee.objects.select_related("person").get(employee_no=9002)
    assert (employee.person.name, employee.person.gender) == ("신입 사원", "F")
    assert employee.is_active_employee
    history = EmploymentHistory.objects.get(history_id=body["history_id"])
    assert (history.employee_id, history.start_date, history.end_date) == (
        9002, date(2026, 10, 15), None,
    )
    assert (history.department_id, history.position_id) == (10, "STAFF")
    assert history.base_salary == Decimal("3200000.00")
    account = User.objects.get(pk=body["account"]["id"])
    assert account.employee_id == 9002 and account.check_password(PASSWORD)
    # 역할 배정과 부서장 지정은 별개다.
    assert Department.objects.get(dept_no=10).head_id is None


def test_fn_hr_006_registers_without_account(org: dict) -> None:
    before_users = User.objects.count()
    response = client_for(org["hr"]).post(
        URL, payload(account=None, role_codes=[]), format="json"
    )
    assert response.status_code == 201, response.data
    assert response.json()["account"] is None
    assert User.objects.count() == before_users


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"name": ""}, "name"),
        ({"birth_date": None}, "birth_date"),
        ({"gender": "X"}, "gender"),
        ({"email": "not-an-email"}, "email"),
        ({"hire_date": None}, "hire_date"),
        ({"dept_no": None}, "dept_no"),
        ({"account": {"password": "short"}}, "account"),
        ({"emp_no": 5555}, "emp_no"),
        ({"base_salary": None}, "base_salary"),
        ({"base_salary": "-1"}, "base_salary"),
    ],
)
def test_fn_hr_006_rejects_invalid_input(
    org: dict, overrides: dict[str, object], field: str
) -> None:
    before = counts()
    response = client_for(org["hr"]).post(URL, payload(**overrides), format="json")
    assert response.status_code == 400
    assert field in response.json()
    assert counts() == before


@pytest.mark.parametrize("field", ["gender", "base_salary"])
def test_fn_hr_006_rejects_missing_required_field(org: dict, field: str) -> None:
    body = payload()
    del body[field]
    response = client_for(org["hr"]).post(URL, body, format="json")
    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"dept_no": 99}, "dept_no"),
        ({"position_code": "NOPE"}, "position_code"),
        ({"role_codes": ["NOPE"]}, "role_codes"),
        ({"email": "STAFF@example.com"}, "email"),
    ],
)
def test_fn_hr_006_rejects_unknown_references_and_duplicate_email(
    org: dict, overrides: dict[str, object], field: str
) -> None:
    before = counts()
    response = client_for(org["hr"]).post(URL, payload(**overrides), format="json")
    assert response.status_code == 400
    assert response.json()["field"] == field
    assert counts() == before


def test_hr_008_rejects_email_used_only_by_login_account(org: dict) -> None:
    User.objects.create_user(email="new.hire@example.com", password="pw")
    before = counts()
    response = client_for(org["hr"]).post(URL, payload(), format="json")
    assert response.status_code == 400
    assert response.json()["field"] == "email"
    assert counts() == before


def test_fn_hr_006_account_creation_failure_rolls_back(org: dict) -> None:
    before = counts()
    # 8자 이상이지만 CommonPasswordValidator에 걸리는 비밀번호
    response = client_for(org["hr"]).post(
        URL, payload(account={"password": "password"}), format="json"
    )
    assert response.status_code == 400
    assert response.json()["field"] == "account.password"
    assert counts() == before


def test_fn_hr_006_role_rule_failure_after_inserts_rolls_back(org: dict) -> None:
    EmployeeRole.objects.create(
        employee_id=1001, role_id=HR_LEAVE_APPROVER_ROLE, assigned_at=timezone.now()
    )
    before = counts()
    response = client_for(org["hr"]).post(
        URL, payload(role_codes=[HR_LEAVE_APPROVER_ROLE]), format="json"
    )
    assert response.status_code == 400
    assert counts() == before


def test_fn_hr_006_unexpected_account_error_rolls_back(
    org: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: object, **kwargs: object) -> int:
        raise RuntimeError("accounts unavailable")

    monkeypatch.setattr(DjangoAccountGateway, "create_account", boom)
    before = counts()
    with pytest.raises(RuntimeError):
        client_for(org["hr"]).post(URL, payload(), format="json")
    assert counts() == before


def test_fn_hr_006_employee_no_collision_with_manual_entry_is_retried(
    org: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_add = DjangoNewHireUnitOfWork.add_employee
    calls = {"count": 0}

    def colliding_add(self: DjangoNewHireUnitOfWork, **values: object) -> int:
        # 첫 시도는 발급 사번이 수동 입력된 기존 사번(1001)과 겹친 것처럼 PK 충돌을 낸다.
        calls["count"] += 1
        if calls["count"] == 1:
            Employee(
                employee_no=1001,
                person_id=values["person_id"],
                department_id=values["dept_no"],
                position_id=values["position_code"],
                tenure_status="재직",
                email="collision@example.com",
                hire_date=values["hire_date"],
            ).save(force_insert=True)
        return real_add(self, **values)

    monkeypatch.setattr(DjangoNewHireUnitOfWork, "add_employee", colliding_add)
    before = counts()

    response = client_for(org["hr"]).post(URL, payload(), format="json")

    assert response.status_code == 201, response.data
    assert response.json()["emp_no"] == 9002
    assert calls["count"] == 2
    # 실패한 첫 시도의 Person 등은 남지 않는다.
    assert Person.objects.count() == before[0] + 1


def test_fn_hr_006_non_conflict_integrity_error_is_not_retried(
    org: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"count": 0}

    def failing_history(self: DjangoNewHireUnitOfWork, **values: object) -> int:
        calls["count"] += 1
        raise IntegrityError("CHECK constraint failed: chk_emp_history_salary")

    monkeypatch.setattr(DjangoNewHireUnitOfWork, "add_history", failing_history)
    before = counts()
    with pytest.raises(IntegrityError):
        client_for(org["hr"]).post(URL, payload(), format="json")
    assert calls["count"] == 1
    assert counts() == before


def test_hr_007_lagging_employee_no_sequence_blocks_registration(
    org: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    # SQLite AUTOINCREMENT는 뒤처지지 않으므로, 시퀀스가 기존 최대 사번(9001)보다 낮은
    # 값을 준 것처럼 발급값을 바꾼다. 공유 DB는 실제로 시퀀스 1, 최대 사번 910050 상태였다.
    manager = Employee.objects
    real_create = manager.create
    monkeypatch.setattr(manager, "create", lambda **values: real_create(employee_no=5, **values))
    before = counts()

    with pytest.raises(EmployeeNoSequenceOutOfSync):
        client_for(org["hr"]).post(URL, payload(), format="json")
    assert counts() == before


def test_fn_hr_006_concurrent_duplicate_email_is_rejected_without_leftovers(
    org: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_check = DjangoNewHireUnitOfWork.employee_email_in_use
    calls = {"count": 0}

    def racing_check(self: DjangoNewHireUnitOfWork, email: str) -> bool:
        # 첫 시도의 사전 검사 직후 다른 요청이 같은 이메일을 커밋한 것처럼 동작한다.
        calls["count"] += 1
        return False if calls["count"] == 1 else real_check(self, email)

    monkeypatch.setattr(DjangoNewHireUnitOfWork, "employee_email_in_use", racing_check)
    before = counts()

    response = client_for(org["hr"]).post(
        URL, payload(email="staff@example.com", account=None), format="json"
    )

    assert response.status_code == 400
    assert response.json()["field"] == "email"
    assert counts() == before
