from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from vacation.domain.exceptions import InvalidUseDaysError, InvalidVacationPeriodError


@dataclass(frozen=True)
class VacationPeriod:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise InvalidVacationPeriodError("종료일시는 시작일시보다 빠를 수 없습니다.")


@dataclass(frozen=True)
class UseDays:
    value: Decimal

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidUseDaysError("차감일수는 0보다 커야 합니다.")
        if self.value.as_tuple().exponent < -2:
            raise InvalidUseDaysError("차감일수는 소수점 둘째 자리까지만 입력할 수 있습니다.")
