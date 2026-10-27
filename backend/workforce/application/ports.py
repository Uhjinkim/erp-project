from contextlib import AbstractContextManager
from datetime import date
from decimal import Decimal
from typing import Protocol

from workforce.domain.history import HistoryChange, HistoryEntry, TransferTarget
from workforce.domain.lifecycle import (
    EmploymentState,
    RetiredEmployee,
    RetiredEmployeeCriteria,
)
from workforce.domain.onboarding import EmploymentPeriod
from workforce.domain.personal_info import (
    ApprovalRequiredValues,
    ChangeRequestStatus,
    PersonalInfoChangeRequest,
)
from workforce.domain.policies import EmployeeCandidate, EmployeeProfile


class WorkforceQueryGateway(Protocol):
    def has_active_role(self, employee_no: int, role_code: str) -> bool: ...

    def department_head(self, employee_no: int) -> EmployeeCandidate | None: ...

    def parent_department_head(self, employee_no: int) -> EmployeeCandidate | None: ...

    def active_role_holders(self, role_code: str, *, limit: int) -> list[EmployeeCandidate]: ...


class EmployeeProfileGateway(Protocol):
    def employee_profile(self, employee_no: int) -> EmployeeProfile | None: ...


class RoleCommandGateway(Protocol):
    def employee_is_active(self, employee_no: int) -> bool: ...

    def has_active_assignment(self, employee_no: int, role_code: str) -> bool: ...

    def active_role_holder_count(self, role_code: str) -> int: ...

    def assign_role(self, employee_no: int, role_code: str) -> int: ...

    def revoke_role(self, employee_no: int, assignment_id: int) -> bool: ...


class PersonalInfoRepository(Protocol):
    """HR-002/HR-003 개인정보 수정 요청 저장소 포트."""

    def transaction(self) -> AbstractContextManager[None]: ...

    def lock_employee(self, employee_no: int) -> None: ...

    def is_active_employee(self, employee_no: int) -> bool: ...

    def current_values(self, employee_no: int) -> ApprovalRequiredValues | None: ...

    def email_in_use(self, email: str, *, exclude_employee_no: int) -> bool: ...

    def has_pending_request(self, employee_no: int) -> bool: ...

    def apply_values(self, employee_no: int, values: ApprovalRequiredValues) -> None: ...

    def update_login_email(self, employee_no: int, email: str) -> None: ...

    def add_request(self, request: PersonalInfoChangeRequest) -> PersonalInfoChangeRequest: ...

    def get_request(
        self, request_id: int, *, for_update: bool = False
    ) -> PersonalInfoChangeRequest | None: ...

    def save_request(self, request: PersonalInfoChangeRequest) -> None: ...

    def list_requests(
        self, *, employee_no: int | None, status: ChangeRequestStatus | None
    ) -> list[PersonalInfoChangeRequest]: ...


class NewHireUnitOfWork(Protocol):
    """FN-HR-006 신규 입사자 등록 저장소 포트.

    ``transaction()`` 안의 쓰기는 계정·역할 gateway 쓰기까지 함께 커밋되거나 롤백된다.
    동시 등록으로 고유·배타 제약이 충돌하면 ``RegistrationConflict``를 던진다.
    """

    def transaction(self) -> AbstractContextManager[None]: ...

    def department_exists(self, dept_no: int) -> bool: ...

    def position_exists(self, position_code: str) -> bool: ...

    def missing_role_codes(self, role_codes: tuple[str, ...]) -> set[str]: ...

    def employee_email_in_use(self, email: str) -> bool: ...

    def add_person(self, *, name: str, birth_date: date, gender: str) -> int: ...

    def lock_person_employments(self, person_id: int) -> list[EmploymentState] | None:
        """FN-HR-009: Person을 잠그고 그 Person의 고용 기록을 반환한다. Person이 없으면 None."""
        ...

    def person_name(self, person_id: int) -> str: ...

    def update_person(
        self,
        person_id: int,
        *,
        name: str | None,
        birth_date: date | None,
        gender: str | None,
    ) -> None: ...

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
        """사원을 추가하고 DB가 발급한 사번을 반환한다(HR-007)."""
        ...

    def history_periods(self, employee_no: int) -> list[EmploymentPeriod]: ...

    def add_history(
        self,
        *,
        employee_no: int,
        period: EmploymentPeriod,
        dept_no: int,
        position_code: str,
        base_salary: Decimal,
    ) -> int: ...


class AccountGateway(Protocol):
    """accounts 컨텍스트의 로그인 계정 생성 포트. 실패하면 ``AccountCreationFailed``."""

    def email_in_use(self, email: str) -> bool: ...

    def create_account(self, *, email: str, password: str, employee_no: int) -> int: ...


class EmploymentLifecycleRepository(Protocol):
    """FN-HR-007 퇴사 처리 저장소 포트."""

    def transaction(self) -> AbstractContextManager[None]: ...

    def lock_employment(self, employee_no: int) -> EmploymentState | None: ...

    def terminate(self, employee_no: int, term_date: date) -> None:
        """상태를 퇴사로 바꾸고 퇴사일을 기록한다. 연결 계정은 비활성화된다(HR-004)."""
        ...


class RetiredEmployeeQuery(Protocol):
    """FN-HR-008 퇴사자 조회 포트."""

    def retired_employees(self, criteria: RetiredEmployeeCriteria) -> list[RetiredEmployee]: ...


class EmploymentHistoryRepository(Protocol):
    """FN-HR-010 인사이력 조회·발령 저장소 포트."""

    def transaction(self) -> AbstractContextManager[None]: ...

    def employee_exists(self, employee_no: int) -> bool: ...

    def lock_transfer_target(self, employee_no: int) -> TransferTarget | None: ...

    def history(self, employee_no: int) -> list[HistoryEntry]:
        """시작일 최신순으로 반환한다."""
        ...

    def department_exists(self, dept_no: int) -> bool: ...

    def position_exists(self, position_code: str) -> bool: ...

    def close_history(self, history_id: int, end_date: date | None) -> None:
        """종료일을 바꾼다. None이면 다시 진행 중 이력이 된다."""
        ...

    def update_history(self, entry: HistoryEntry) -> None: ...

    def delete_history(self, history_id: int) -> None: ...

    def add_history(self, employee_no: int, entry: HistoryEntry) -> int: ...

    def update_current_assignment(
        self, employee_no: int, *, dept_no: int, position_code: str
    ) -> None: ...

    def release_department_heads(self, employee_no: int, *, keep_dept_no: int) -> list[int]:
        """keep_dept_no 외 부서의 부서장 지정을 해제하고 해제한 부서번호를 반환한다."""
        ...

    def restore_department_heads(self, employee_no: int, dept_nos: list[int]) -> list[int]:
        """부서장이 비어 있는 부서만 다시 지정하고 복원한 부서번호를 반환한다."""
        ...

    def released_heads_for(self, employee_no: int, history_id: int) -> list[int]:
        """이 이력의 발령·정정 기록에서 해제한 부서번호를 모은다."""
        ...

    def record_change(self, change: HistoryChange) -> None: ...

    def changes(self, employee_no: int) -> list[HistoryChange]: ...
