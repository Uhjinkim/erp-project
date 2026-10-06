from dataclasses import dataclass, fields
from datetime import datetime
from enum import StrEnum

from workforce.domain.exceptions import WorkforceRuleViolation

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

    def approve(self, actor_employee_no: int | None, processed_at: datetime) -> None:
        """FN-HR-004: 인사관리자는 대기 요청만 승인한다."""
        self._require_pending()
        self.status = ChangeRequestStatus.APPROVED
        self._record_processing(actor_employee_no, processed_at)

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
