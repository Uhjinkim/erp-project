from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from payroll.domain.exceptions import EmptyPayrollItemsError, InvalidPayrollTransitionError
from payroll.domain.policies import round_up_to_won
from payroll.domain.value_objects import PayPeriod


class PayrollStatus(StrEnum):
    DRAFT = "작성중"
    CONFIRMED = "확정"


class ComponentCategory(StrEnum):
    EARNING = "지급"
    DEDUCTION = "공제"


class PayrollAction(StrEnum):
    CREATED = "생성"
    ITEMS_UPDATED = "구성항목 수정"
    CONFIRMED = "확정"
    CONFIRMATION_CANCELLED = "확정취소"
    RECONFIRMED = "재확정"


@dataclass(frozen=True)
class PayrollComponentType:
    code: str
    name: str
    category: ComponentCategory
    is_active: bool


@dataclass
class PayrollItem:
    component_code: str
    category: ComponentCategory
    amount: Decimal
    item_id: int | None = None


@dataclass
class PayrollStatement:
    statement_id: int | None
    employee_no: int
    period: PayPeriod
    payment_date: date
    status: PayrollStatus
    created_by: int
    items: list[PayrollItem] = field(default_factory=list)
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None

    @property
    def total_earnings(self) -> Decimal:
        return sum(
            (item.amount for item in self.items if item.category == ComponentCategory.EARNING),
            Decimal("0"),
        )

    @property
    def total_deductions(self) -> Decimal:
        return sum(
            (item.amount for item in self.items if item.category == ComponentCategory.DEDUCTION),
            Decimal("0"),
        )

    @property
    def net_pay(self) -> Decimal:
        return round_up_to_won(self.total_earnings - self.total_deductions)

    def replace_items(self, items: list[PayrollItem]) -> None:
        self._require_status(PayrollStatus.DRAFT, "확정된 급여는 직접 수정할 수 없습니다.")
        if not items:
            raise EmptyPayrollItemsError("급여 구성항목은 최소 1건 이상이어야 합니다.")
        self.items = items

    def confirm(self, actor_employee_no: int, confirmed_at: datetime) -> bool:
        """Return True when this is the first confirmation, False when it is a reconfirmation."""
        self._require_status(PayrollStatus.DRAFT, "작성/정산중 상태만 확정할 수 있습니다.")
        if not self.items:
            raise EmptyPayrollItemsError("구성항목이 없는 급여는 확정할 수 없습니다.")
        is_first_confirmation = self.confirmed_at is None
        self.status = PayrollStatus.CONFIRMED
        self.confirmed_by = actor_employee_no
        self.confirmed_at = confirmed_at
        return is_first_confirmation

    def cancel_confirmation(self, reason: str) -> None:
        self._require_status(PayrollStatus.CONFIRMED, "확정 상태만 확정취소할 수 있습니다.")
        if not reason.strip():
            raise InvalidPayrollTransitionError("확정취소 사유는 필수입니다.")
        self.status = PayrollStatus.DRAFT

    def _require_status(self, expected: PayrollStatus, message: str) -> None:
        if self.status != expected:
            raise InvalidPayrollTransitionError(message)


@dataclass(frozen=True)
class PayrollHistory:
    history_id: int | None
    statement_id: int
    action: PayrollAction
    actor_employee_no: int
    changed_at: datetime
    reason: str | None = None
    change_summary: str | None = None
