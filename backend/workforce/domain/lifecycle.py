"""FN-HR-007 퇴사 처리, FN-HR-008 퇴사자 조회, FN-HR-009 재입사 도메인 규칙.

HR-005: 퇴사 처리는 상태와 퇴사일만 바꾸고 인사이력·역할·평가·급여 기록은 보존한다.
HR-006: 재입사는 기존 Person에 새 사번의 고용을 추가하며 이전 사번을 재사용하지 않는다.
"""

from dataclasses import dataclass
from datetime import date

from workforce.domain.exceptions import WorkforceRuleViolation

TERMINATED = "퇴사"


@dataclass(frozen=True)
class EmploymentState:
    employee_no: int
    tenure_status: str
    hire_date: date
    term_date: date | None


@dataclass(frozen=True)
class RetiredEmployee:
    employee_no: int
    person_id: int
    name: str
    dept_no: int | None
    dept_name: str | None
    position_code: str | None
    position_name: str | None
    email: str | None
    hire_date: date
    term_date: date


@dataclass(frozen=True)
class RetiredEmployeeCriteria:
    """FN-HR-008 퇴사자 조회 조건. None인 조건은 적용하지 않는다."""

    name: str | None = None
    dept_no: int | None = None
    employee_no: int | None = None
    term_date_from: date | None = None
    term_date_to: date | None = None


def validate_retired_criteria(criteria: RetiredEmployeeCriteria) -> None:
    if (
        criteria.term_date_from is not None
        and criteria.term_date_to is not None
        and criteria.term_date_from > criteria.term_date_to
    ):
        raise WorkforceRuleViolation(
            "퇴사일 조회 시작일은 종료일보다 늦을 수 없습니다.", field="term_date_from"
        )


def validate_termination(state: EmploymentState, *, term_date: date, today: date) -> None:
    """HR-009: 퇴사일은 입사일 이후, 오늘 이전이어야 한다. 이미 퇴사한 고용은 거절한다."""
    if state.tenure_status == TERMINATED:
        raise WorkforceRuleViolation("이미 퇴사 처리된 사원입니다.")
    if term_date < state.hire_date:
        raise WorkforceRuleViolation("퇴사일은 입사일보다 빠를 수 없습니다.", field="term_date")
    if term_date > today:
        raise WorkforceRuleViolation(
            "퇴사일은 오늘 또는 이전 날짜만 지정할 수 있습니다.", field="term_date"
        )


def ensure_rehire_allowed(prior: list[EmploymentState], *, hire_date: date) -> None:
    """HR-006: 이전 고용이 모두 퇴사 상태이고 새 입사일이 마지막 퇴사일 이후여야 한다."""
    if not prior:
        raise WorkforceRuleViolation(
            "이전 고용 기록이 없어 재입사로 등록할 수 없습니다.", field="person_id"
        )
    if any(item.tenure_status != TERMINATED for item in prior):
        raise WorkforceRuleViolation(
            "재직 또는 휴직 중인 고용이 있어 재입사할 수 없습니다.", field="person_id"
        )
    last_term_date = max(
        (item.term_date for item in prior if item.term_date is not None), default=None
    )
    if last_term_date is not None and hire_date <= last_term_date:
        raise WorkforceRuleViolation(
            "재입사일은 마지막 퇴사일 이후여야 합니다.", field="hire_date"
        )
