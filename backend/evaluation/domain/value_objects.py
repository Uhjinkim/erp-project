from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from evaluation.domain.exceptions import (
    EvaluationYearNotAllowedError,
    InsufficientTenureError,
    InvalidEvaluationError,
)

MIN_SCORE = Decimal("0")
MAX_SCORE = Decimal("100")
SCORE_DECIMAL_PLACES = 2
REASON_MAX_LENGTH = 255
# Employees with this many months of service or fewer are not evaluated.
MINIMUM_TENURE_MONTHS = 3


class Grade(StrEnum):
    S = "S"
    A = "A"
    B = "B"
    C = "C"


# EV-003: 100점 만점 기준 S 90점 이상, A 80점 이상, B 70점 이상, C 70점 미만.
GRADE_THRESHOLDS: tuple[tuple[Decimal, Grade], ...] = (
    (Decimal("90"), Grade.S),
    (Decimal("80"), Grade.A),
    (Decimal("70"), Grade.B),
)


@dataclass(frozen=True)
class EvaluationScore:
    value: Decimal

    def __post_init__(self) -> None:
        try:
            value = Decimal(self.value)
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise InvalidEvaluationError("평가 점수는 숫자여야 합니다.") from exc
        if not value.is_finite():
            raise InvalidEvaluationError("평가 점수는 숫자여야 합니다.")
        if value < MIN_SCORE or value > MAX_SCORE:
            raise InvalidEvaluationError(
                f"평가 점수는 {MIN_SCORE}점 이상 {MAX_SCORE}점 이하여야 합니다."
            )
        if -value.normalize().as_tuple().exponent > SCORE_DECIMAL_PLACES:
            raise InvalidEvaluationError(
                f"평가 점수는 소수점 {SCORE_DECIMAL_PLACES}자리까지 입력할 수 있습니다."
            )
        object.__setattr__(self, "value", value)

    @property
    def grade(self) -> Grade:
        for threshold, grade in GRADE_THRESHOLDS:
            if self.value >= threshold:
                return grade
        return Grade.C


@dataclass(frozen=True)
class EvaluationYear:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 4 or not self.value.isascii() or not self.value.isdigit():
            raise InvalidEvaluationError("평가 연도는 YYYY 형식의 4자리 숫자여야 합니다.")


def ensure_creatable_year(eval_year: str, current_year: int) -> None:
    """New evaluations may only target the current or the previous year.

    Existing unfinished evaluations stay editable after the year changes, so this
    check applies to creation only.
    """
    EvaluationYear(eval_year)
    if int(eval_year) not in (current_year, current_year - 1):
        raise EvaluationYearNotAllowedError(
            f"평가는 {current_year - 1}년 또는 {current_year}년에 대해서만 생성할 수 있습니다."
        )


def evaluation_basis_date(eval_year: str, today: date) -> date:
    """The date whose department and position define the evaluation (연말 기준).

    A past year uses its 31 December, so a January transfer does not hand last year's
    evaluation to the new department. The current year has no year end yet, so it uses today.
    """
    EvaluationYear(eval_year)
    return min(date(int(eval_year), 12, 31), today)


def add_months(value: date, months: int) -> date:
    """Same day `months` later, clamped to the end of shorter months (e.g. 11/30 + 3 -> 2/28)."""
    month_index = value.month - 1 + months
    year, month = value.year + month_index // 12, month_index % 12 + 1
    next_month = date(year + month // 12, month % 12 + 1, 1)
    last_day = (next_month - date.resolution).day
    return date(year, month, min(value.day, last_day))


def ensure_minimum_tenure(hire_date: date, basis_date: date) -> None:
    """3개월 이하 근무자는 평가 대상이 아니다 (사용자 확인, 2026-10-08).

    Tenure is measured up to the evaluation basis date (연말 기준), so someone hired
    on 30 September has exactly three months on 30 December and is not evaluated.
    """
    if add_months(hire_date, MINIMUM_TENURE_MONTHS) >= basis_date:
        raise InsufficientTenureError(
            f"근무 기간이 {MINIMUM_TENURE_MONTHS}개월 이하인 사원은 평가 대상이 아닙니다."
        )


@dataclass(frozen=True)
class Reason:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidEvaluationError("사유를 입력해야 합니다.")
        if len(self.value) > REASON_MAX_LENGTH:
            raise InvalidEvaluationError(f"사유는 {REASON_MAX_LENGTH}자를 초과할 수 없습니다.")
