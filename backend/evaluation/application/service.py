from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime

from evaluation.application.dto import (
    CreateEvaluationCommand,
    ReassignEvaluationCommand,
    ReviseEvaluationCommand,
)
from evaluation.application.ports import WorkforceGateway
from evaluation.domain.entities import (
    CONTENT_ACTIONS,
    EVALUATOR_PERMISSION_MESSAGE,
    Evaluation,
    EvaluationHistory,
    EvaluatorCandidate,
    creation_history,
    ensure_can_evaluate,
    ensure_eligible_evaluator,
    restorable_status,
)
from evaluation.domain.exceptions import (
    DuplicateEvaluationError,
    EvaluationNotFoundError,
    EvaluationPermissionError,
    InactiveEmployeeError,
)
from evaluation.domain.repositories import EvaluationUnitOfWork
from evaluation.domain.value_objects import (
    EvaluationYear,
    ensure_creatable_year,
    ensure_minimum_tenure,
    evaluation_basis_date,
)


class EvaluationService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], EvaluationUnitOfWork],
        workforce: WorkforceGateway,
        clock: Callable[[], datetime],
        today: Callable[[], date] | None = None,
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.workforce = workforce
        self.clock = clock
        self.today = today or (lambda: clock().date())

    # Evaluator use cases -------------------------------------------------------------

    def create_evaluation(self, command: CreateEvaluationCommand) -> Evaluation:
        self._ensure_active(command.evaluator_no)
        today = self.today()
        ensure_creatable_year(command.eval_year, today.year)
        basis_date = evaluation_basis_date(command.eval_year, today)
        target = self.workforce.evaluation_target(command.employee_no, basis_date)
        # Check authority before revealing anything about the target (HR-001).
        if target is None:
            raise EvaluationPermissionError(EVALUATOR_PERMISSION_MESSAGE)
        ensure_can_evaluate(command.evaluator_no, target)
        if not target.is_employed:
            raise InactiveEmployeeError("퇴사한 사원은 새로 평가할 수 없습니다.")
        if target.hire_date is not None:
            ensure_minimum_tenure(target.hire_date, basis_date)

        evaluation = Evaluation.draft(
            target=target,
            evaluator_no=command.evaluator_no,
            eval_year=command.eval_year,
            score=command.score,
            comments=command.comments,
            now=self.clock(),
        )
        with self.unit_of_work_factory() as uow:
            if uow.evaluations.exists_for(command.employee_no, command.eval_year):
                raise DuplicateEvaluationError("해당 연도의 평가가 이미 존재합니다.")
            created = uow.evaluations.add(evaluation)
            uow.histories.add(creation_history(created))
            return created

    def revise_evaluation(self, command: ReviseEvaluationCommand) -> Evaluation:
        return self._evaluator_action(
            command.eval_id,
            command.actor_no,
            lambda evaluation, now: evaluation.revise(
                command.actor_no, command.score, command.comments, now
            ),
        )

    def submit_evaluation(self, eval_id: int, actor_no: int) -> Evaluation:
        return self._evaluator_action(
            eval_id, actor_no, lambda evaluation, now: evaluation.submit(actor_no, now)
        )

    # HR manager use cases ------------------------------------------------------------

    def return_evaluation(self, eval_id: int, actor_no: int, reason: str) -> Evaluation:
        return self._hr_action(
            eval_id,
            actor_no,
            lambda evaluation, _histories, now: evaluation.return_for_revision(
                actor_no, reason, now
            ),
        )

    def reassign_evaluation(self, command: ReassignEvaluationCommand) -> Evaluation:
        def reassign(
            evaluation: Evaluation, _histories: list[EvaluationHistory], now: datetime
        ) -> EvaluationHistory:
            # Checked only after the caller is known to be an HR manager.
            if not self.workforce.is_active_employee(command.new_evaluator_no):
                raise InactiveEmployeeError("재직 중인 사원만 평가자로 지정할 수 있습니다.")
            ensure_eligible_evaluator(self.workforce.is_department_head(command.new_evaluator_no))
            return evaluation.reassign(
                command.actor_no, command.new_evaluator_no, command.reason, now
            )

        return self._hr_action(command.eval_id, command.actor_no, reassign)

    def confirm_evaluation(self, eval_id: int, actor_no: int) -> Evaluation:
        def confirm(
            evaluation: Evaluation, histories: list[EvaluationHistory], now: datetime
        ) -> EvaluationHistory:
            authors = {entry.actor_no for entry in histories if entry.action in CONTENT_ACTIONS}
            return evaluation.confirm(actor_no, authors, now)

        # The target asking to confirm their own evaluation gets confirmation_not_allowed
        # rather than the EV-005 404 used by the other HR actions.
        return self._hr_action(eval_id, actor_no, confirm, hide_from_target=False)

    def cancel_confirmation(self, eval_id: int, actor_no: int, reason: str) -> Evaluation:
        return self._hr_action(
            eval_id,
            actor_no,
            lambda evaluation, _histories, now: evaluation.cancel_confirmation(
                actor_no, reason, now
            ),
        )

    def exclude_evaluation(self, eval_id: int, actor_no: int, reason: str) -> Evaluation:
        return self._hr_action(
            eval_id,
            actor_no,
            lambda evaluation, _histories, now: evaluation.exclude(actor_no, reason, now),
        )

    def cancel_exclusion(self, eval_id: int, actor_no: int, reason: str = "") -> Evaluation:
        return self._hr_action(
            eval_id,
            actor_no,
            lambda evaluation, histories, now: evaluation.cancel_exclusion(
                actor_no, restorable_status(histories), reason, now
            ),
        )

    def evaluator_candidates(self, actor_no: int) -> list[EvaluatorCandidate]:
        """Who an HR manager may pick when reassigning (FN-EV-001)."""
        self._ensure_active(actor_no)
        if not self.workforce.is_hr_manager(actor_no):
            raise EvaluationPermissionError("인사관리자만 처리할 수 있습니다.")
        return self.workforce.evaluator_candidates()

    # Queries -------------------------------------------------------------------------

    def get_evaluation(self, eval_id: int, viewer_no: int) -> Evaluation:
        self._ensure_active(viewer_no)
        is_hr = self.workforce.is_hr_manager(viewer_no)
        with self.unit_of_work_factory() as uow:
            return self._get_visible(uow, eval_id, viewer_no, is_hr)

    def list_history(self, eval_id: int, viewer_no: int) -> list[EvaluationHistory]:
        self._ensure_active(viewer_no)
        is_hr = self.workforce.is_hr_manager(viewer_no)
        with self.unit_of_work_factory() as uow:
            evaluation = self._get_visible(uow, eval_id, viewer_no, is_hr)
            if not evaluation.can_view_history(viewer_no, is_hr):
                raise EvaluationPermissionError("평가 이력을 조회할 권한이 없습니다.")
            return uow.histories.list_for(eval_id)

    def list_evaluations(self, viewer_no: int, eval_year: str | None = None) -> list[Evaluation]:
        self._ensure_active(viewer_no)
        if eval_year is not None:
            EvaluationYear(eval_year)
        is_hr = self.workforce.is_hr_manager(viewer_no)
        with self.unit_of_work_factory() as uow:
            if is_hr:
                evaluations = uow.evaluations.list_all(eval_year)
            else:
                evaluations = uow.evaluations.list_visible_to(viewer_no, eval_year)
        # Same rule as the detail view, e.g. an HR manager's own draft stays hidden (EV-005).
        return [item for item in evaluations if item.is_visible_to(viewer_no, is_hr)]

    # Helpers -------------------------------------------------------------------------

    def _evaluator_action(
        self,
        eval_id: int,
        actor_no: int,
        apply: Callable[[Evaluation, datetime], EvaluationHistory],
    ) -> Evaluation:
        # Re-checked on every save: a reassigned or retired evaluator is refused here.
        self._ensure_active(actor_no)
        is_hr = self.workforce.is_hr_manager(actor_no)
        with self.unit_of_work_factory() as uow:
            evaluation = self._get_visible(uow, eval_id, actor_no, is_hr)
            if actor_no == evaluation.evaluator_no:
                # Re-checked on every save: an evaluator who lost the head post must be
                # reassigned first.
                ensure_eligible_evaluator(self.workforce.is_department_head(actor_no))
            expected = replace(evaluation)
            history = apply(evaluation, self.clock())
            return self._save(uow, evaluation, expected, history)

    def _hr_action(
        self,
        eval_id: int,
        actor_no: int,
        apply: Callable[[Evaluation, list[EvaluationHistory], datetime], EvaluationHistory],
        *,
        hide_from_target: bool = True,
    ) -> Evaluation:
        self._ensure_active(actor_no)
        if not self.workforce.is_hr_manager(actor_no):
            raise EvaluationPermissionError("인사관리자만 처리할 수 있습니다.")
        with self.unit_of_work_factory() as uow:
            evaluation = uow.evaluations.get(eval_id)
            if hide_from_target and not evaluation.is_visible_to(
                actor_no, viewer_is_hr_manager=True
            ):
                # EV-005: an HR manager's own unconfirmed evaluation does not exist for them.
                raise EvaluationNotFoundError("평가를 찾을 수 없습니다.")
            expected = replace(evaluation)
            history = apply(evaluation, uow.histories.list_for(eval_id), self.clock())
            return self._save(uow, evaluation, expected, history)

    def _save(
        self,
        uow: EvaluationUnitOfWork,
        evaluation: Evaluation,
        expected: Evaluation,
        history: EvaluationHistory,
    ) -> Evaluation:
        saved = uow.evaluations.save(evaluation, expected)
        uow.histories.add(history)
        return saved

    def _get_visible(
        self, uow: EvaluationUnitOfWork, eval_id: int, viewer_no: int, is_hr: bool
    ) -> Evaluation:
        evaluation = uow.evaluations.get(eval_id)
        if not evaluation.is_visible_to(viewer_no, is_hr):
            # Hide existence of evaluations the viewer may not read.
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.")
        return evaluation

    def _ensure_active(self, employee_no: int) -> None:
        if not self.workforce.is_active_employee(employee_no):
            raise InactiveEmployeeError("재직 중인 사원만 인사평가를 사용할 수 있습니다.")
