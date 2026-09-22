from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from payroll.domain.value_objects import PayPeriod

# PY-009 / FN-PY-001: KRW payroll is settled in whole won; foreign-currency
# conversion fractions are rounded up only at final net-pay calculation.
WON_QUANTUM = Decimal("1")

# 급여 정산일자 정책(담당자 확정, 2026-09-22): 매월 25일이며, 25일이 토·일요일이거나
# 등록된 공휴일이면 직전 평일로 당긴다. Notion의 "정산일자 후보 미확정" 안건은 이 결정으로
# 해소되었으나, Notion 원문 자체는 팀이 별도로 갱신해야 한다.
SETTLEMENT_DAY = 25


def round_up_to_won(amount: Decimal) -> Decimal:
    return amount.quantize(WON_QUANTUM, rounding=ROUND_CEILING)


def _last_day_of_month(year: int, month: int) -> int:
    next_month_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (next_month_first - timedelta(days=1)).day


def resolve_payment_date(period: PayPeriod, holidays: frozenset[date] = frozenset()) -> date:
    target_day = min(SETTLEMENT_DAY, _last_day_of_month(period.year, period.month))
    candidate = date(period.year, period.month, target_day)
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate -= timedelta(days=1)
    return candidate
