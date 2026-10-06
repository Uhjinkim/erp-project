from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from evaluation.domain.exceptions import (
    EvaluationPermissionError,
    EvaluationStateError,
    SelfEvaluationError,
)
from evaluation.domain.value_objects import EvaluationScore, EvaluationYear, Grade


class EvaluationStatus(StrEnum):
    DRAFT = "작성중"
    CONFIRMED = "확정"


@dataclass(frozen=True)
class EvaluationTarget:
    """Workforce facts about the evaluated employee at the time of the request."""

    employee_no: int
    is_active: bool
    department_no: int | None
    position_code: str | None
    department_head_no: int | None


def ensure_can_evaluate(evaluator_no: int, target: EvaluationTarget) -> None:
    """EV-001/EV-002: only the target's department head evaluates, never themselves."""
    if evaluator_no == target.employee_no:
        raise SelfEvaluationError("본인을 평가할 수 없습니다.")
    if target.department_head_no is None or target.department_head_no != evaluator_no:
        raise EvaluationPermissionError("소속 부서장만 해당 사원을 평가할 수 있습니다.")


@dataclass
class Evaluation:
    eval_id: int | None
    employee_no: int
    eval_year: str
    snapshot_department_no: int | None
    snapshot_position_code: str | None
    evaluator_no: int
    score: Decimal
    grade: Grade
    comments: str
    status: EvaluationStatus
    updated_at: datetime
    confirmed_by: int | None = None
    confirmed_at: datetime | None = None
    employee_name: str | None = None
    evaluator_name: str | None = None

    def __post_init__(self) -> None:
        EvaluationYear(self.eval_year)
        self.score = EvaluationScore(self.score).value

    @classmethod
    def draft(
        cls,
        *,
        target: EvaluationTarget,
        evaluator_no: int,
        eval_year: str,
        score: Decimal,
        comments: str,
        now: datetime,
    ) -> "Evaluation":
        ensure_can_evaluate(evaluator_no, target)
        validated = EvaluationScore(score)
        return cls(
            eval_id=None,
            employee_no=target.employee_no,
            eval_year=eval_year,
            snapshot_department_no=target.department_no,
            snapshot_position_code=target.position_code,
            evaluator_no=evaluator_no,
            score=validated.value,
            grade=validated.grade,
            comments=comments,
            status=EvaluationStatus.DRAFT,
            updated_at=now,
        )

    def revise(self, actor_no: int, score: Decimal, comments: str, now: datetime) -> None:
        if actor_no != self.evaluator_no:
            raise EvaluationPermissionError("평가 작성자만 평가를 수정할 수 있습니다.")
        self._require_draft("확정된 평가는 수정할 수 없습니다.")
        validated = EvaluationScore(score)
        self.score = validated.value
        self.grade = validated.grade
        self.comments = comments
        self.updated_at = now

    def confirm(self, actor_no: int, now: datetime) -> None:
        """EV-004: the HR manager check is done by the use case before calling this."""
        self._require_draft("이미 확정된 평가입니다.")
        self.status = EvaluationStatus.CONFIRMED
        self.confirmed_by = actor_no
        self.confirmed_at = now
        self.updated_at = now

    def is_visible_to(self, viewer_no: int, viewer_is_hr_manager: bool) -> bool:
        if viewer_is_hr_manager or viewer_no == self.evaluator_no:
            return True
        return viewer_no == self.employee_no and self.status == EvaluationStatus.CONFIRMED

    def _require_draft(self, message: str) -> None:
        if self.status != EvaluationStatus.DRAFT:
            raise EvaluationStateError(message)
