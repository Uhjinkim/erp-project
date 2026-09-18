from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from vacation.domain.exceptions import InvalidStatusTransitionError, VacationPermissionError
from vacation.domain.value_objects import UseDays, VacationPeriod


class VacationStatus(StrEnum):
    PENDING = "대기"
    APPROVED = "승인"
    REJECTED = "반려"
    CANCELLED = "취소"
    RECALLED = "회수"


@dataclass(frozen=True)
class VacationType:
    type_id: str
    type_name: str
    is_paid: bool
    deduct_days: Decimal

    def __post_init__(self) -> None:
        if self.deduct_days < 0:
            raise ValueError("기본 차감일수는 0 이상이어야 합니다.")


@dataclass
class VacationRequest:
    request_id: int | None
    employee_no: int
    type_id: str
    period: VacationPeriod
    use_days: UseDays
    status: VacationStatus
    approver_no: int
    request_reason: str | None = None
    approved_at: datetime | None = None
    reject_reason: str | None = None

    def approve(self, actor_employee_no: int, approved_at: datetime) -> None:
        self._require_pending_approver(actor_employee_no)
        self.status = VacationStatus.APPROVED
        self.approved_at = approved_at
        self.reject_reason = None

    def reject(self, actor_employee_no: int, reason: str) -> None:
        self._require_pending_approver(actor_employee_no)
        if not reason.strip():
            raise InvalidStatusTransitionError("반려 사유는 필수입니다.")
        self.status = VacationStatus.REJECTED
        self.reject_reason = reason.strip()

    def cancel(self, actor_employee_no: int) -> None:
        self._require_owner(actor_employee_no)
        self._require_status(VacationStatus.PENDING)
        self.status = VacationStatus.CANCELLED

    def recall(self, actor_employee_no: int, reason: str) -> None:
        if actor_employee_no != self.approver_no:
            raise VacationPermissionError("기존 승인자만 승인된 휴가를 회수할 수 있습니다.")
        self._require_status(VacationStatus.APPROVED)
        if not reason.strip():
            raise InvalidStatusTransitionError("회수 사유는 필수입니다.")
        self.status = VacationStatus.RECALLED
        self.approved_at = None

    def resubmit(
        self,
        actor_employee_no: int,
        type_id: str,
        period: VacationPeriod,
        use_days: UseDays,
        approver_no: int,
        request_reason: str | None,
    ) -> None:
        self._require_owner(actor_employee_no)
        self._require_status(VacationStatus.RECALLED)
        self.type_id = type_id
        self.period = period
        self.use_days = use_days
        self.approver_no = approver_no
        self.request_reason = request_reason
        self.reject_reason = None
        self.status = VacationStatus.PENDING

    def _require_pending_approver(self, actor_employee_no: int) -> None:
        if actor_employee_no != self.approver_no:
            raise VacationPermissionError("현재 승인자만 처리할 수 있습니다.")
        self._require_status(VacationStatus.PENDING)

    def _require_owner(self, actor_employee_no: int) -> None:
        if actor_employee_no != self.employee_no:
            raise VacationPermissionError("신청자 본인만 처리할 수 있습니다.")

    def _require_status(self, expected: VacationStatus) -> None:
        if self.status != expected:
            raise InvalidStatusTransitionError(
                f"{expected.value} 상태의 신청만 처리할 수 있습니다. 현재 상태: {self.status.value}"
            )


@dataclass(frozen=True)
class VacationHistory:
    history_id: int | None
    request_id: int
    from_status: VacationStatus | None
    to_status: VacationStatus
    actor_employee_no: int
    reason: str | None
    changed_at: datetime
