from datetime import date, timedelta

from payroll.domain.value_objects import PayPeriod

# 급여 정산일자 정책(담당자 확정, 2026-09-22): 매월 25일이며, 25일이 토·일요일이거나
# 등록된 공휴일이면 직전 평일로 당긴다. Notion의 "정산일자 후보 미확정" 안건은 이 결정으로
# 해소되었으나, Notion 원문 자체는 팀이 별도로 갱신해야 한다.
SETTLEMENT_DAY = 25

# 급여명세서 표시 순서(급여 담당자 지정, 2026-10-07): 지급 — 기본급·고정수당·초과근무수당·상여,
# 공제 — 국민연금·건강보험·고용보험·소득세. 목록에 없는 항목은 그 뒤에 코드순으로 둔다.
PAYSLIP_ORDER = (
    "BASE_PAY",
    "FIXED_ALLOWANCE",
    "OVERTIME_ALLOWANCE",
    "BONUS",
    "NATIONAL_PENSION",
    "HEALTH_INSURANCE",
    "EMPLOYMENT_INSURANCE",
    "INCOME_TAX",
)


def payslip_rank(component_code: str) -> tuple[int, str]:
    if component_code in PAYSLIP_ORDER:
        return PAYSLIP_ORDER.index(component_code), component_code
    return len(PAYSLIP_ORDER), component_code


def _last_day_of_month(year: int, month: int) -> int:
    next_month_first = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return (next_month_first - timedelta(days=1)).day


def resolve_payment_date(period: PayPeriod, holidays: frozenset[date] = frozenset()) -> date:
    target_day = min(SETTLEMENT_DAY, _last_day_of_month(period.year, period.month))
    candidate = date(period.year, period.month, target_day)
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate -= timedelta(days=1)
    return candidate
