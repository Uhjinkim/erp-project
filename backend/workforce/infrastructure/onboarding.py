from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction

from workforce.application.onboarding import (
    EmployeeNoSequenceOutOfSync,
    RegistrationConflict,
)
from workforce.domain.lifecycle import EmploymentState
from workforce.domain.onboarding import EmploymentPeriod
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmploymentHistory,
    Person,
    Position,
    Role,
)

# PostgreSQL unique_violation, exclusion_violation
CONFLICT_SQLSTATES = frozenset({"23505", "23P01"})


def is_registration_conflict(exc: IntegrityError) -> bool:
    sqlstate = getattr(exc.__cause__, "sqlstate", None)
    if sqlstate is not None:
        return sqlstate in CONFLICT_SQLSTATES
    # SQLite(테스트)는 SQLSTATE를 주지 않는다.
    return "UNIQUE constraint failed" in str(exc)


class DjangoNewHireUnitOfWork:
    """FN-HR-006 등록 단위 작업. 같은 DB 연결의 계정·역할 쓰기도 이 트랜잭션에 포함된다."""

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            with transaction.atomic():
                yield
        except IntegrityError as exc:
            # 사전 검사 이후 다른 요청이 같은 사번·이메일을 먼저 커밋한 경우만 재시도 대상이다.
            # CHECK·NOT NULL 위반 등은 입력 검증 누락이므로 그대로 올려 숨기지 않는다.
            if not is_registration_conflict(exc):
                raise
            raise RegistrationConflict(str(exc)) from exc

    def department_exists(self, dept_no: int) -> bool:
        return Department.objects.filter(dept_no=dept_no).exists()

    def position_exists(self, position_code: str) -> bool:
        return Position.objects.filter(position_code=position_code).exists()

    def missing_role_codes(self, role_codes: tuple[str, ...]) -> set[str]:
        found = Role.objects.filter(role_code__in=role_codes).values_list("role_code", flat=True)
        return set(role_codes) - set(found)

    def employee_email_in_use(self, email: str) -> bool:
        return Employee.objects.filter(email__iexact=email).exists()

    def add_person(self, *, name: str, birth_date: date, gender: str) -> int:
        return Person.objects.create(name=name, birth_date=birth_date, gender=gender).person_id

    def lock_person_employments(self, person_id: int) -> list[EmploymentState] | None:
        if not Person.objects.select_for_update().filter(person_id=person_id).exists():
            return None
        return [
            EmploymentState(employee_no, tenure_status, hire_date, term_date)
            for employee_no, tenure_status, hire_date, term_date in Employee.objects.filter(
                person_id=person_id
            ).values_list("employee_no", "tenure_status", "hire_date", "term_date")
        ]

    def person_name(self, person_id: int) -> str:
        return Person.objects.values_list("name", flat=True).get(person_id=person_id)

    def update_person(
        self,
        person_id: int,
        *,
        name: str | None,
        birth_date: date | None,
        gender: str | None,
    ) -> None:
        changes = {
            field: value
            for field, value in (("name", name), ("birth_date", birth_date), ("gender", gender))
            if value is not None
        }
        Person.objects.filter(person_id=person_id).update(**changes)

    def add_employee(
        self,
        *,
        person_id: int,
        dept_no: int,
        position_code: str,
        email: str,
        hire_date: date,
        phone: str | None,
        extension_no: str | None,
        address: str | None,
    ) -> int:
        # HR-007: 사번은 employees.emp_no identity 시퀀스가 발급한다.
        employee = Employee.objects.create(
            person_id=person_id,
            department_id=dept_no,
            position_id=position_code,
            tenure_status=Employee.TenureStatus.ACTIVE,
            email=email,
            hire_date=hire_date,
            phone=phone,
            extension_no=extension_no,
            address=address,
        )
        # 수동 입력 사번이 시퀀스보다 앞서 있으면 기존 체계와 동떨어진 사번이 발급된다.
        # 불변 사번이므로 발급하지 않고 롤백한다(migration 0005가 시퀀스를 맞춘다).
        if Employee.objects.filter(employee_no__gt=employee.employee_no).exists():
            raise EmployeeNoSequenceOutOfSync(
                f"사번 시퀀스가 기존 최대 사번보다 뒤처져 있습니다(발급값 {employee.employee_no})."
            )
        return employee.employee_no

    def history_periods(self, employee_no: int) -> list[EmploymentPeriod]:
        return [
            EmploymentPeriod(start_date=start, end_date=end)
            for start, end in EmploymentHistory.objects.filter(employee_id=employee_no)
            .values_list("start_date", "end_date")
        ]

    def add_history(
        self,
        *,
        employee_no: int,
        period: EmploymentPeriod,
        dept_no: int,
        position_code: str,
        base_salary: Decimal,
    ) -> int:
        return EmploymentHistory.objects.create(
            employee_id=employee_no,
            start_date=period.start_date,
            end_date=period.end_date,
            department_id=dept_no,
            position_id=position_code,
            base_salary=base_salary,
        ).history_id
