from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from payroll.domain.exceptions import InvalidPayPeriodError, InvalidPayrollAmountError


@dataclass(frozen=True)
class PayPeriod:
    """A settlement month, identified by its first calendar day."""

    value: date

    def __post_init__(self) -> None:
        if self.value.day != 1:
            raise InvalidPayPeriodError("정산기간은 대상 연월의 1일로 지정해야 합니다.")

    @property
    def year(self) -> int:
        return self.value.year

    @property
    def month(self) -> int:
        return self.value.month

    @classmethod
    def of(cls, year: int, month: int) -> "PayPeriod":
        if not 1 <= month <= 12:
            raise InvalidPayPeriodError("정산월은 1월에서 12월 사이여야 합니다.")
        return cls(date(year, month, 1))


@dataclass(frozen=True)
class PayrollAmount:
    value: Decimal

    def __post_init__(self) -> None:
        if self.value < 0:
            raise InvalidPayrollAmountError("급여 구성항목 금액은 0 이상이어야 합니다.")
