from collections.abc import Callable
from datetime import datetime

from evaluation.application.dto import CreateEvaluationCommand, ReviseEvaluationCommand
from evaluation.application.ports import WorkforceGateway
from evaluation.domain.entities import Evaluation
from evaluation.domain.exceptions import (
    DuplicateEvaluationError,
    EmployeeNotFoundError,
    EvaluationNotFoundError,
    EvaluationPermissionError,
    InactiveEmployeeError,
)
from evaluation.domain.repositories import EvaluationRepository
from evaluation.domain.value_objects import EvaluationYear


class EvaluationService:
    def __init__(
        self,
        repository: EvaluationRepository,
        workforce: WorkforceGateway,
        clock: Callable[[], datetime],
    ) -> None:
        self.repository = repository
        self.workforce = workforce
        self.clock = clock

    def create_evaluation(self, command: CreateEvaluationCommand) -> Evaluation:
        self._ensure_active(command.evaluator_no)
        EvaluationYear(command.eval_year)
        target = self.workforce.evaluation_target(command.employee_no)
        if target is None:
            raise EmployeeNotFoundError("평가 대상 사원을 찾을 수 없습니다.")
        if not target.is_active:
            raise InactiveEmployeeError("재직 중인 사원만 평가할 수 있습니다.")

        evaluation = Evaluation.draft(
            target=target,
            evaluator_no=command.evaluator_no,
            eval_year=command.eval_year,
            score=command.score,
            comments=command.comments,
            now=self.clock(),
        )
        if self.repository.exists_for(command.employee_no, command.eval_year):
            raise DuplicateEvaluationError("해당 연도의 평가가 이미 존재합니다.")
        return self.repository.add(evaluation)

    def revise_evaluation(self, command: ReviseEvaluationCommand) -> Evaluation:
        self._ensure_active(command.actor_no)
        evaluation = self.repository.get(command.eval_id)
        evaluation.revise(command.actor_no, command.score, command.comments, self.clock())
        return self.repository.save_draft(evaluation)

    def confirm_evaluation(self, eval_id: int, actor_no: int) -> Evaluation:
        self._ensure_active(actor_no)
        if not self.workforce.is_hr_manager(actor_no):
            raise EvaluationPermissionError("인사관리자만 평가를 확정할 수 있습니다.")
        evaluation = self.repository.get(eval_id)
        evaluation.confirm(actor_no, self.clock())
        return self.repository.save_draft(evaluation)

    def get_evaluation(self, eval_id: int, viewer_no: int) -> Evaluation:
        self._ensure_active(viewer_no)
        evaluation = self.repository.get(eval_id)
        if not evaluation.is_visible_to(viewer_no, self.workforce.is_hr_manager(viewer_no)):
            # Hide existence of evaluations the viewer may not read.
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.")
        return evaluation

    def list_evaluations(self, viewer_no: int, eval_year: str | None = None) -> list[Evaluation]:
        self._ensure_active(viewer_no)
        if eval_year is not None:
            EvaluationYear(eval_year)
        if self.workforce.is_hr_manager(viewer_no):
            return self.repository.list_all(eval_year)
        return self.repository.list_visible_to(viewer_no, eval_year)

    def _ensure_active(self, employee_no: int) -> None:
        if not self.workforce.is_active_employee(employee_no):
            raise InactiveEmployeeError("재직 중인 사원만 인사평가를 사용할 수 있습니다.")
