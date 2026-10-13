from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from workforce.application.ports import AccountGateway, NewHireUnitOfWork, RoleCommandGateway
from workforce.application.services import assign_employee_role
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.lifecycle import ensure_rehire_allowed
from workforce.domain.onboarding import (
    EmploymentPeriod,
    ensure_no_period_overlap,
    validate_employment_terms,
    validate_new_hire,
    validate_person_values,
)


class DuplicateEmail(WorkforceRuleViolation):
    pass


class AccountCreationFailed(WorkforceRuleViolation):
    pass


class RegistrationConflict(Exception):
    """동시 등록으로 사번·이메일 고유 제약이 충돌해 트랜잭션이 롤백되었다."""


class EmployeeNoSequenceOutOfSync(Exception):
    """DB 사번 시퀀스가 기존 최대 사번보다 뒤처져 있다. 시퀀스를 맞추기 전에는 등록하지 않는다."""


class RegistrationRetryExhausted(WorkforceRuleViolation):
    pass


@dataclass(frozen=True)
class NewHireAccount:
    password: str


@dataclass(frozen=True)
class RegisterNewHireCommand:
    name: str
    birth_date: date
    gender: str
    email: str
    hire_date: date
    dept_no: int
    position_code: str
    base_salary: Decimal
    phone: str | None = None
    extension_no: str | None = None
    address: str | None = None
    role_codes: tuple[str, ...] = ()
    account: NewHireAccount | None = None


@dataclass(frozen=True)
class RehireCommand:
    """FN-HR-009 재입사. 인적사항(이름·생년월일·성별)은 값이 있을 때만 기존 Person을 갱신한다."""

    person_id: int
    email: str
    hire_date: date
    dept_no: int
    position_code: str
    base_salary: Decimal
    name: str | None = None
    birth_date: date | None = None
    gender: str | None = None
    phone: str | None = None
    extension_no: str | None = None
    address: str | None = None
    role_codes: tuple[str, ...] = ()
    account: NewHireAccount | None = None


EmploymentCommand = RegisterNewHireCommand | RehireCommand


@dataclass(frozen=True)
class RoleAssignmentResult:
    employee_role_id: int
    role_code: str


@dataclass(frozen=True)
class RegisteredNewHire:
    employee_no: int
    person_id: int
    name: str
    history_id: int
    account_id: int | None
    role_assignments: tuple[RoleAssignmentResult, ...]


class NewHireRegistrationService:
    """FN-HR-006 신규 입사, FN-HR-009 재입사 유스케이스.

    Person·Employee·최초 인사이력·역할·계정을 한 트랜잭션으로 등록한다. 부서장 지정은 조직
    책임이므로 이 유스케이스에서 다루지 않는다.
    """

    MAX_ATTEMPTS = 3

    def __init__(
        self,
        unit_of_work: NewHireUnitOfWork,
        accounts: AccountGateway,
        roles: RoleCommandGateway,
    ) -> None:
        self.unit_of_work = unit_of_work
        self.accounts = accounts
        self.roles = roles

    def register(self, command: RegisterNewHireCommand) -> RegisteredNewHire:
        validate_new_hire(
            name=command.name,
            gender=command.gender,
            email=command.email,
            base_salary=command.base_salary,
            role_codes=command.role_codes,
        )
        return self._with_retry(lambda: self._register_once(command))

    def rehire(self, command: RehireCommand) -> RegisteredNewHire:
        validate_person_values(name=command.name, gender=command.gender)
        validate_employment_terms(
            email=command.email, base_salary=command.base_salary, role_codes=command.role_codes
        )
        return self._with_retry(lambda: self._rehire_once(command))

    def _with_retry(self, attempt: Callable[[], RegisteredNewHire]) -> RegisteredNewHire:
        # 사전 검사 뒤 다른 요청이 같은 이메일을 먼저 커밋했거나, 수동 입력 사번이 시퀀스 값과
        # 겹치면 고유 제약이 충돌한다. 전체를 롤백한 뒤 처음부터 다시 검증한다. 재시도에서
        # 이메일 중복이면 DuplicateEmail로 끝나고, 시퀀스는 이미 다음 값으로 넘어가 있다.
        for _ in range(self.MAX_ATTEMPTS):
            try:
                return attempt()
            except RegistrationConflict:
                continue
        raise RegistrationRetryExhausted(
            "동시에 등록 요청이 많아 처리하지 못했습니다. 잠시 후 다시 시도하세요."
        )

    def _register_once(self, command: RegisterNewHireCommand) -> RegisteredNewHire:
        uow = self.unit_of_work
        with uow.transaction():
            self._ensure_employment_allowed(command)
            name = command.name.strip()
            person_id = uow.add_person(
                name=name, birth_date=command.birth_date, gender=command.gender
            )
            return self._create_employment(person_id, name, command)

    def _rehire_once(self, command: RehireCommand) -> RegisteredNewHire:
        uow = self.unit_of_work
        with uow.transaction():
            # 같은 Person의 동시 재입사로 재직 고용이 2건 생기지 않도록 Person을 잠근다.
            prior = uow.lock_person_employments(command.person_id)
            if prior is None:
                raise WorkforceRuleViolation("인적사항을 찾을 수 없습니다.", field="person_id")
            ensure_rehire_allowed(prior, hire_date=command.hire_date)
            self._ensure_employment_allowed(command)
            person_updates = (command.name, command.birth_date, command.gender)
            if any(value is not None for value in person_updates):
                uow.update_person(
                    command.person_id,
                    name=command.name.strip() if command.name is not None else None,
                    birth_date=command.birth_date,
                    gender=command.gender,
                )
            # HR-006: 이전 사번을 재사용하지 않고 새 사번을 발급한다.
            name = uow.person_name(command.person_id)
            return self._create_employment(command.person_id, name, command)

    def _ensure_employment_allowed(self, command: EmploymentCommand) -> None:
        uow = self.unit_of_work
        if not uow.department_exists(command.dept_no):
            raise WorkforceRuleViolation("존재하지 않는 부서입니다.", field="dept_no")
        if not uow.position_exists(command.position_code):
            raise WorkforceRuleViolation("존재하지 않는 직급입니다.", field="position_code")
        missing = uow.missing_role_codes(command.role_codes)
        if missing:
            raise WorkforceRuleViolation(
                f"존재하지 않는 역할입니다: {', '.join(sorted(missing))}", field="role_codes"
            )
        if uow.employee_email_in_use(command.email) or self.accounts.email_in_use(
            command.email
        ):
            raise DuplicateEmail("이미 사용 중인 이메일입니다.", field="email")

    def _create_employment(
        self, person_id: int, name: str, command: EmploymentCommand
    ) -> RegisteredNewHire:
        uow = self.unit_of_work
        employee_no = uow.add_employee(
            person_id=person_id,
            dept_no=command.dept_no,
            position_code=command.position_code,
            email=command.email,
            hire_date=command.hire_date,
            phone=command.phone,
            extension_no=command.extension_no,
            address=command.address,
        )

        # FN-HR-010/HR-010: 최초 인사이력은 입사일부터 종료일 없이 기록한다.
        period = EmploymentPeriod(start_date=command.hire_date)
        ensure_no_period_overlap(uow.history_periods(employee_no), period)
        history_id = uow.add_history(
            employee_no=employee_no,
            period=period,
            dept_no=command.dept_no,
            position_code=command.position_code,
            base_salary=command.base_salary,
        )

        role_assignments = tuple(
            RoleAssignmentResult(
                assign_employee_role(employee_no, role_code, self.roles), role_code
            )
            for role_code in command.role_codes
        )

        account_id = None
        if command.account is not None:
            account_id = self.accounts.create_account(
                email=command.email,
                password=command.account.password,
                employee_no=employee_no,
            )

        return RegisteredNewHire(
            employee_no=employee_no,
            person_id=person_id,
            name=name,
            history_id=history_id,
            account_id=account_id,
            role_assignments=role_assignments,
        )
