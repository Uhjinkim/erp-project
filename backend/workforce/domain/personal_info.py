from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import StrEnum

from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.policies import EmployeeCandidate

# HR-002 / FN-HR-002: 사원이 승인 없이 직접 수정하는 연락처·주소 항목.
SELF_EDITABLE_FIELDS = frozenset({"phone", "address"})


class ChangeRequestStatus(StrEnum):
    """HR-011: 개인정보 변경 요청 상태."""

    PENDING = "대기"
    APPROVED = "승인"
    REJECTED = "반려"
    CANCELLED = "취소"


@dataclass(frozen=True)
class ApprovalRequiredValues:
    """HR-003: 변경 요청과 인사관리자 승인을 거쳐야 하는 사내 이메일·급여계좌.

    변경 요청에서 ``None``은 '변경하지 않음'을 뜻한다.
    """

    email: str | None = None
    bank_code: str | None = None
    account_no: str | None = None

    def changed_fields(self) -> list[str]:
        return [item.name for item in fields(self) if getattr(self, item.name) is not None]

    def masked(self) -> "ApprovalRequiredValues":
        """계좌번호를 뒤 4자리만 남기고 가린 사본."""
        return replace(self, account_no=mask_account_no(self.account_no))


def mask_account_no(value: str | None) -> str | None:
    """급여계좌번호를 뒤 4자리만 남기고 가린다(예: ``123-456-7890`` → ``******7890``).

    구분 기호는 제거해 계좌 형식도 드러내지 않는다. 4자리 이하이면 모두 가린다.
    """
    if value is None:
        return None
    characters = [character for character in value if character.isalnum()]
    if len(characters) <= 4:
        return "*" * len(characters)
    return "*" * (len(characters) - 4) + "".join(characters[-4:])


def validate_self_editable_fields(field_names: set[str]) -> None:
    """HR-002: 일반 사원은 연락처·주소만 직접 수정한다."""
    if not field_names:
        raise WorkforceRuleViolation("수정할 항목이 없습니다.")
    forbidden = sorted(field_names - SELF_EDITABLE_FIELDS)
    if forbidden:
        raise WorkforceRuleViolation(
            "연락처·주소만 직접 수정할 수 있습니다. 사내 이메일·급여계좌는 변경 요청을, "
            "그 밖의 인사정보는 인사관리자에게 요청하세요.",
            field=forbidden[0],
        )


def validate_change_request_values(
    *,
    current: ApprovalRequiredValues,
    requested: ApprovalRequiredValues,
) -> None:
    """FN-HR-003: 승인형 변경 요청 값 검증(형식·중복 검증은 transport/application 담당)."""
    changed = requested.changed_fields()
    if not changed:
        raise WorkforceRuleViolation("변경할 사내 이메일 또는 급여계좌를 입력하세요.")
    if (requested.bank_code is None) != (requested.account_no is None):
        raise WorkforceRuleViolation(
            "급여계좌는 은행 코드와 계좌번호를 함께 입력해야 합니다.",
            field="account_no" if requested.account_no is None else "bank_code",
        )
    if all(getattr(requested, name) == getattr(current, name) for name in changed):
        raise WorkforceRuleViolation("현재 값과 다른 값을 입력하세요.")


@dataclass(frozen=True)
class ProcessorAssignment:
    """변경 요청 처리자. 요청 시점이 아니라 승인·반려 시점의 조직 정보로 결정한다.

    - ``any_hr_manager``: 인사관리자 누구나 처리한다.
    - ``employee_no``: 지정된 사원만 처리한다.
    - 둘 다 비어 있으면 superuser만 처리한다.
    superuser는 어느 경우든 처리할 수 있다.
    """

    any_hr_manager: bool = False
    employee_no: int | None = None

    def allows(
        self,
        *,
        actor_employee_no: int | None,
        actor_is_hr_manager: bool,
        actor_is_superuser: bool,
    ) -> bool:
        if actor_is_superuser:
            return True
        if self.any_hr_manager:
            return actor_is_hr_manager
        return self.employee_no is not None and actor_employee_no == self.employee_no


def resolve_change_request_processor(
    *,
    requester_is_hr_manager: bool,
    department_head: EmployeeCandidate | None,
    department_head_is_hr_manager: bool = False,
) -> ProcessorAssignment:
    """FN-HR-004 처리자 결정.

    일반 사원의 요청은 인사관리자가 처리한다. 인사관리자 본인의 요청은 상급자(소속 부서장)가
    처리하며, 요청자가 그 부서장이면 본인이 처리한다. 재직 중인 상급자가 없거나 상급자가
    인사관리자가 아니면(급여계좌 노출 방지, HR-001) superuser만 처리한다.
    """
    if not requester_is_hr_manager:
        return ProcessorAssignment(any_hr_manager=True)
    if (
        department_head is not None
        and department_head.is_active
        and department_head_is_hr_manager
    ):
        return ProcessorAssignment(employee_no=department_head.employee_no)
    return ProcessorAssignment()


@dataclass
class PersonalInfoChangeRequest:
    """FN-HR-003~005, FN-HR-011: 승인형 개인정보 변경 요청."""

    request_id: int | None
    employee_no: int
    previous: ApprovalRequiredValues
    requested: ApprovalRequiredValues
    status: ChangeRequestStatus
    requested_at: datetime
    processed_by: int | None = None
    processed_at: datetime | None = None
    reject_reason: str | None = None

    def approve(
        self, actor_employee_no: int | None, processed_at: datetime
    ) -> ApprovalRequiredValues:
        """FN-HR-004: 대기 요청을 승인하고, 실제 인사정보에 반영할 원래 요청값을 돌려준다.

        반환 후 요청 이력에는 가려진 계좌번호만 남는다.
        """
        self._require_pending()
        values_to_apply = self.requested
        self.status = ChangeRequestStatus.APPROVED
        self._record_processing(actor_employee_no, processed_at)
        return values_to_apply

    def reject(
        self,
        actor_employee_no: int | None,
        processed_at: datetime,
        reason: str | None,
    ) -> None:
        """FN-HR-004: 반려 시 실제 인사정보는 유지한다."""
        self._require_pending()
        self.status = ChangeRequestStatus.REJECTED
        self.reject_reason = reason.strip() if reason and reason.strip() else None
        self._record_processing(actor_employee_no, processed_at)

    def cancel(self, actor_employee_no: int | None, processed_at: datetime) -> None:
        """FN-HR-011: 요청자 본인만 대기 요청을 취소한다."""
        if actor_employee_no != self.employee_no:
            raise WorkforceRuleViolation("본인이 제출한 변경 요청만 취소할 수 있습니다.")
        self._require_pending()
        self.status = ChangeRequestStatus.CANCELLED
        self._record_processing(actor_employee_no, processed_at)

    def _require_pending(self) -> None:
        if self.status != ChangeRequestStatus.PENDING:
            raise WorkforceRuleViolation(
                f"대기 상태의 요청만 처리할 수 있습니다. (현재 상태: {self.status})"
            )

    def _record_processing(self, actor_employee_no: int | None, processed_at: datetime) -> None:
        self.processed_by = actor_employee_no
        self.processed_at = processed_at
        # 처리가 끝난 요청은 계좌번호 원문이 더 필요 없으므로 이력에서 가린다.
        self.requested = self.requested.masked()
