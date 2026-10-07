from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from evaluation.domain.exceptions import (
    ConfirmationNotAllowedError,
    EvaluationPermissionError,
    EvaluationStateError,
    InvalidEvaluationError,
    SelfEvaluationError,
)
from evaluation.domain.value_objects import EvaluationScore, EvaluationYear, Grade, Reason


class EvaluationStatus(StrEnum):
    DRAFT = "작성중"
    SUBMITTED = "제출"
    RETURNED = "반려"
    CONFIRMED = "확정"
    EXCLUDED = "제외"


# The evaluator edits only these; a submitted evaluation must be returned first.
EDITABLE_STATUSES = frozenset({EvaluationStatus.DRAFT, EvaluationStatus.RETURNED})
UNCONFIRMED_STATUSES = frozenset(
    {EvaluationStatus.DRAFT, EvaluationStatus.SUBMITTED, EvaluationStatus.RETURNED}
)


class EvaluationAction(StrEnum):
    CREATE = "CREATE"
    REVISE = "REVISE"
    SUBMIT = "SUBMIT"
    RETURN = "RETURN"
    REASSIGN = "REASSIGN"
    CONFIRM = "CONFIRM"
    CANCEL_CONFIRMATION = "CANCEL_CONFIRMATION"
    EXCLUDE = "EXCLUDE"
    CANCEL_EXCLUSION = "CANCEL_EXCLUSION"


# Actions that author the evaluation content. Their actors may not confirm it.
CONTENT_ACTIONS = frozenset(
    {EvaluationAction.CREATE, EvaluationAction.REVISE, EvaluationAction.SUBMIT}
)


@dataclass(frozen=True)
class EvaluationTarget:
    """Workforce facts about the evaluated employee at the time of the request."""

    employee_no: int
    is_employed: bool
    department_no: int | None
    position_code: str | None
    department_head_no: int | None
    parent_department_head_no: int | None = None

    @property
    def is_department_head(self) -> bool:
        return self.department_head_no == self.employee_no

    @property
    def designated_evaluator_no(self) -> int | None:
        """EV-001: members are evaluated by their department head, heads by the parent's head."""
        if self.is_department_head:
            return self.parent_department_head_no
        return self.department_head_no


EVALUATOR_PERMISSION_MESSAGE = "해당 사원을 평가할 권한이 없습니다."


def ensure_can_evaluate(evaluator_no: int, target: EvaluationTarget) -> None:
    """EV-001/EV-002: only the designated department head evaluates, never themselves."""
    if evaluator_no == target.employee_no:
        raise SelfEvaluationError("본인을 평가할 수 없습니다.")
    if target.designated_evaluator_no != evaluator_no:
        # One message for every case so callers cannot infer the target's role or status.
        raise EvaluationPermissionError(EVALUATOR_PERMISSION_MESSAGE)


@dataclass
class EvaluationHistory:
    history_id: int | None
    eval_id: int
    action: EvaluationAction
    from_status: EvaluationStatus | None
    to_status: EvaluationStatus
    actor_no: int
    changed_at: datetime
    from_evaluator_no: int | None = None
    to_evaluator_no: int | None = None
    score: Decimal | None = None
    reason: str = ""
    actor_name: str | None = None


@dataclass
class Evaluation:
    """An evaluation of one employee for one year.

    `evaluator_no` is the current evaluator, who alone edits and submits the content.
    `created_by` is the first author and never changes. Neither follows later
    organization changes; only an HR manager reassigns the evaluator.
    """

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
    created_by: int | None = None
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
            created_by=evaluator_no,
        )

    # Evaluator actions -------------------------------------------------------------

    def revise(
        self, actor_no: int, score: Decimal, comments: str | None, now: datetime
    ) -> EvaluationHistory:
        """Comments of None keep the current text; an empty string clears it."""
        self._require_current_evaluator(actor_no)
        self._require_status(EDITABLE_STATUSES, "작성중 또는 반려된 평가만 수정할 수 있습니다.")
        validated = EvaluationScore(score)
        self.score = validated.value
        self.grade = validated.grade
        if comments is not None:
            self.comments = comments
        return self._record(EvaluationAction.REVISE, actor_no, self.status, now)

    def submit(self, actor_no: int, now: datetime) -> EvaluationHistory:
        self._require_current_evaluator(actor_no)
        self._require_status(EDITABLE_STATUSES, "작성중 또는 반려된 평가만 제출할 수 있습니다.")
        return self._record(EvaluationAction.SUBMIT, actor_no, EvaluationStatus.SUBMITTED, now)

    # HR manager actions (the use case checks the HR role) --------------------------

    def return_for_revision(self, actor_no: int, reason: str, now: datetime) -> EvaluationHistory:
        """반려: send a submitted evaluation back to the same evaluator for revision."""
        self._require_not_target(actor_no)
        Reason(reason)
        self._require_status({EvaluationStatus.SUBMITTED}, "제출된 평가만 반려할 수 있습니다.")
        return self._record(
            EvaluationAction.RETURN, actor_no, EvaluationStatus.RETURNED, now, reason=reason
        )

    def reassign(
        self, actor_no: int, new_evaluator_no: int, reason: str, now: datetime
    ) -> EvaluationHistory:
        """Hand the unconfirmed evaluation to another evaluator.

        A submitted evaluation goes back to 작성중 so the new evaluator reviews the
        inherited draft and submits it under their own name.
        """
        self._require_not_target(actor_no)
        Reason(reason)
        self._require_status(UNCONFIRMED_STATUSES, "확정 전 평가만 평가자를 변경할 수 있습니다.")
        if new_evaluator_no == self.employee_no:
            raise SelfEvaluationError("평가 대상자를 평가자로 지정할 수 없습니다.")
        if new_evaluator_no == self.evaluator_no:
            raise InvalidEvaluationError("현재 평가자와 같은 사원으로 변경할 수 없습니다.")
        previous_evaluator = self.evaluator_no
        self.evaluator_no = new_evaluator_no
        to_status = (
            EvaluationStatus.DRAFT if self.status == EvaluationStatus.SUBMITTED else self.status
        )
        return self._record(
            EvaluationAction.REASSIGN,
            actor_no,
            to_status,
            now,
            reason=reason,
            from_evaluator_no=previous_evaluator,
            to_evaluator_no=new_evaluator_no,
        )

    def confirm(self, actor_no: int, content_authors: set[int], now: datetime) -> EvaluationHistory:
        """EV-004: separate the confirmer from everyone who shaped the content."""
        if actor_no == self.employee_no:
            raise ConfirmationNotAllowedError("본인의 평가는 확정할 수 없습니다.")
        if actor_no == self.evaluator_no or actor_no in content_authors:
            raise ConfirmationNotAllowedError(
                "평가를 작성한 사원은 해당 평가를 확정할 수 없습니다."
            )
        self._require_status({EvaluationStatus.SUBMITTED}, "제출된 평가만 확정할 수 있습니다.")
        history = self._record(
            EvaluationAction.CONFIRM, actor_no, EvaluationStatus.CONFIRMED, now
        )
        self.confirmed_by = actor_no
        self.confirmed_at = now
        return history

    def cancel_confirmation(self, actor_no: int, reason: str, now: datetime) -> EvaluationHistory:
        """정정: a confirmed evaluation is never edited directly.

        Cancelling returns it to the current evaluator as 반려; they revise and resubmit,
        and an HR manager confirms it again under the usual separation rules.
        """
        self._require_not_target(actor_no)
        Reason(reason)
        self._require_status(
            {EvaluationStatus.CONFIRMED}, "확정된 평가만 확정을 취소할 수 있습니다."
        )
        history = self._record(
            EvaluationAction.CANCEL_CONFIRMATION,
            actor_no,
            EvaluationStatus.RETURNED,
            now,
            reason=reason,
        )
        self.confirmed_by = None
        self.confirmed_at = None
        return history

    def exclude(self, actor_no: int, reason: str, now: datetime) -> EvaluationHistory:
        """평가 제외: distinct from a zero score; the content is kept for a later cancel."""
        self._require_not_target(actor_no)
        Reason(reason)
        self._require_status(UNCONFIRMED_STATUSES, "확정 전 평가만 평가에서 제외할 수 있습니다.")
        return self._record(
            EvaluationAction.EXCLUDE, actor_no, EvaluationStatus.EXCLUDED, now, reason=reason
        )

    def cancel_exclusion(
        self,
        actor_no: int,
        restored_status: EvaluationStatus,
        reason: str,
        now: datetime,
    ) -> EvaluationHistory:
        self._require_not_target(actor_no)
        self._require_status({EvaluationStatus.EXCLUDED}, "제외된 평가가 아닙니다.")
        if restored_status not in UNCONFIRMED_STATUSES:
            raise EvaluationStateError("제외 이전 상태를 복원할 수 없습니다.")
        return self._record(
            EvaluationAction.CANCEL_EXCLUSION, actor_no, restored_status, now, reason=reason
        )

    # Visibility --------------------------------------------------------------------

    def is_visible_to(self, viewer_no: int, viewer_is_hr_manager: bool) -> bool:
        """Unconfirmed work is for the current evaluator and HR; the target sees it once confirmed.

        A reassigned former evaluator loses access because only the current evaluator counts.
        """
        if viewer_is_hr_manager or viewer_no == self.evaluator_no:
            return True
        return viewer_no == self.employee_no and self.status == EvaluationStatus.CONFIRMED

    def can_view_history(self, viewer_no: int, viewer_is_hr_manager: bool) -> bool:
        return viewer_is_hr_manager or viewer_no == self.evaluator_no

    # Helpers -----------------------------------------------------------------------

    def _record(
        self,
        action: EvaluationAction,
        actor_no: int,
        to_status: EvaluationStatus,
        now: datetime,
        *,
        reason: str = "",
        from_evaluator_no: int | None = None,
        to_evaluator_no: int | None = None,
    ) -> EvaluationHistory:
        assert self.eval_id is not None
        from_status = self.status
        self.status = to_status
        self.updated_at = now
        return EvaluationHistory(
            history_id=None,
            eval_id=self.eval_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            actor_no=actor_no,
            changed_at=now,
            from_evaluator_no=from_evaluator_no,
            to_evaluator_no=to_evaluator_no,
            score=self.score,
            reason=reason,
        )

    def _require_current_evaluator(self, actor_no: int) -> None:
        if actor_no != self.evaluator_no:
            raise EvaluationPermissionError("현재 지정된 평가자만 처리할 수 있습니다.")

    def _require_not_target(self, actor_no: int) -> None:
        if actor_no == self.employee_no:
            raise EvaluationPermissionError("본인의 평가는 처리할 수 없습니다.")

    def _require_status(self, allowed: set | frozenset, message: str) -> None:
        if self.status not in allowed:
            raise EvaluationStateError(message)


def creation_history(evaluation: Evaluation) -> EvaluationHistory:
    assert evaluation.eval_id is not None
    return EvaluationHistory(
        history_id=None,
        eval_id=evaluation.eval_id,
        action=EvaluationAction.CREATE,
        from_status=None,
        to_status=evaluation.status,
        actor_no=evaluation.evaluator_no,
        changed_at=evaluation.updated_at,
        to_evaluator_no=evaluation.evaluator_no,
        score=evaluation.score,
    )


def restorable_status(histories: list[EvaluationHistory]) -> EvaluationStatus:
    """The status an excluded evaluation had right before its latest exclusion."""
    for entry in reversed(histories):
        if entry.action == EvaluationAction.EXCLUDE and entry.from_status is not None:
            return entry.from_status
    raise EvaluationStateError("제외 이력을 찾을 수 없습니다.")
