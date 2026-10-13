"""FN-HR-010 인사이력 조회·발령 등록 도메인 규칙(HR-010).

이력 기간은 시작일·종료일을 모두 포함한다(DB ``daterange(start, end, '[]')`` 배타 제약과 동일).
따라서 이어지는 이력의 이전 종료일은 새 시작일의 전날이다.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.lifecycle import TERMINATED
from workforce.domain.onboarding import EmploymentPeriod, ensure_no_period_overlap


@dataclass(frozen=True)
class HistoryEntry:
    history_id: int | None
    start_date: date
    end_date: date | None
    dept_no: int
    position_code: str
    base_salary: Decimal
    dept_name: str | None = None
    position_name: str | None = None

    @property
    def period(self) -> EmploymentPeriod:
        return EmploymentPeriod(self.start_date, self.end_date)


@dataclass(frozen=True)
class TransferTarget:
    employee_no: int
    tenure_status: str
    hire_date: date
    dept_no: int | None
    position_code: str | None


@dataclass(frozen=True)
class TransferPlan:
    close: tuple[int, date] | None
    baseline: HistoryEntry | None
    new: HistoryEntry


def plan_transfer(
    target: TransferTarget,
    history: list[HistoryEntry],
    *,
    start_date: date,
    dept_no: int,
    position_code: str,
    base_salary: Decimal,
    previous_base_salary: Decimal | None,
    today: date,
) -> TransferPlan:
    """발령 1건을 기존 이력에 반영하는 계획을 만든다.

    - 진행 중(종료일 없음) 이력은 발령일 전날로 마감한다.
    - 이력이 없는 사원은 입사일~발령일 전날 기간을 현재 부서·직급으로 함께 기록한다.
    - 부서 또는 직급이 바뀌는 발령만 등록한다.
    """
    if target.tenure_status == TERMINATED:
        raise WorkforceRuleViolation("퇴사한 사원은 발령할 수 없습니다.")
    if start_date > today:
        raise WorkforceRuleViolation(
            "발령일은 오늘 또는 이전 날짜만 지정할 수 있습니다.", field="start_date"
        )
    if start_date < target.hire_date:
        raise WorkforceRuleViolation("발령일은 입사일보다 빠를 수 없습니다.", field="start_date")
    salaries = (("base_salary", base_salary), ("previous_base_salary", previous_base_salary))
    for field, value in salaries:
        if value is not None and value < 0:
            raise WorkforceRuleViolation("기본급은 0 이상이어야 합니다.", field=field)

    close: tuple[int, date] | None = None
    baseline: HistoryEntry | None = None
    remaining = list(history)
    if history:
        latest = max(history, key=lambda item: (item.start_date, item.history_id or 0))
        current = (latest.dept_no, latest.position_code)
        if latest.end_date is None:
            if start_date <= latest.start_date:
                raise WorkforceRuleViolation(
                    "발령일은 현재 이력의 시작일보다 늦어야 합니다.", field="start_date"
                )
            close = (latest.history_id, start_date - timedelta(days=1))
            remaining = [item for item in history if item is not latest]
            remaining.append(
                HistoryEntry(
                    latest.history_id,
                    latest.start_date,
                    close[1],
                    latest.dept_no,
                    latest.position_code,
                    latest.base_salary,
                )
            )
        elif start_date <= latest.end_date:
            raise WorkforceRuleViolation(
                "발령일은 마지막 이력의 종료일보다 늦어야 합니다.", field="start_date"
            )
    else:
        current = (target.dept_no, target.position_code)
        if start_date > target.hire_date:
            if target.dept_no is None or target.position_code is None:
                raise WorkforceRuleViolation(
                    "현재 부서·직급이 없어 이전 기간 이력을 만들 수 없습니다.", field="start_date"
                )
            if previous_base_salary is None:
                raise WorkforceRuleViolation(
                    "인사이력이 없는 사원의 첫 발령에는 이전 기간 기본급이 필요합니다.",
                    field="previous_base_salary",
                )
            baseline = HistoryEntry(
                None,
                target.hire_date,
                start_date - timedelta(days=1),
                target.dept_no,
                target.position_code,
                previous_base_salary,
            )

    if (dept_no, position_code) == current:
        raise WorkforceRuleViolation("부서 또는 직급이 바뀌는 발령만 등록할 수 있습니다.")

    new = HistoryEntry(None, start_date, None, dept_no, position_code, base_salary)
    periods = [item.period for item in remaining]
    if baseline is not None:
        ensure_no_period_overlap(periods, baseline.period, field="start_date")
        periods.append(baseline.period)
    ensure_no_period_overlap(periods, new.period, field="start_date")
    return TransferPlan(close=close, baseline=baseline, new=new)
