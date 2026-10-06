from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

from evaluation.domain.exceptions import InvalidEvaluationError

MIN_SCORE = Decimal("0")
MAX_SCORE = Decimal("100")
SCORE_DECIMAL_PLACES = 2


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
