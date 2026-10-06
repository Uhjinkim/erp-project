from django.db.models import Q

from evaluation.domain.entities import Evaluation, EvaluationStatus
from evaluation.domain.exceptions import EvaluationNotFoundError, EvaluationStateError
from evaluation.domain.repositories import EvaluationRepository
from evaluation.infrastructure.mappers import model_to_entity
from evaluation.infrastructure.models import EvaluationModel


class DjangoEvaluationRepository(EvaluationRepository):
    def add(self, evaluation: Evaluation) -> Evaluation:
        model = EvaluationModel.objects.create(
            employee_id=evaluation.employee_no,
            eval_year=evaluation.eval_year,
            snapshot_department_id=evaluation.snapshot_department_no,
            snapshot_position_id=evaluation.snapshot_position_code,
            evaluator_id=evaluation.evaluator_no,
            score=evaluation.score,
            grade=evaluation.grade.value,
            comments=evaluation.comments,
            eval_status=evaluation.status.value,
            confirmed_by_id=evaluation.confirmed_by,
            confirmed_at=evaluation.confirmed_at,
            updated_at=evaluation.updated_at,
        )
        return self.get(model.eval_id)

    def get(self, eval_id: int) -> Evaluation:
        try:
            return model_to_entity(self._select_related().get(eval_id=eval_id))
        except EvaluationModel.DoesNotExist as exc:
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.") from exc

    def save_draft(self, evaluation: Evaluation) -> Evaluation:
        # The status condition keeps a concurrent confirmation from being overwritten.
        updated = EvaluationModel.objects.filter(
            eval_id=evaluation.eval_id,
            eval_status=EvaluationStatus.DRAFT.value,
        ).update(
            score=evaluation.score,
            grade=evaluation.grade.value,
            comments=evaluation.comments,
            eval_status=evaluation.status.value,
            confirmed_by_id=evaluation.confirmed_by,
            confirmed_at=evaluation.confirmed_at,
            updated_at=evaluation.updated_at,
        )
        if not updated:
            if EvaluationModel.objects.filter(eval_id=evaluation.eval_id).exists():
                raise EvaluationStateError("확정된 평가는 변경할 수 없습니다.")
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.")
        assert evaluation.eval_id is not None
        return self.get(evaluation.eval_id)

    def exists_for(self, employee_no: int, eval_year: str) -> bool:
        return EvaluationModel.objects.filter(
            employee_id=employee_no,
            eval_year=eval_year,
        ).exists()

    def list_all(self, eval_year: str | None = None) -> list[Evaluation]:
        return self._list(self._select_related(), eval_year)

    def list_visible_to(self, viewer_no: int, eval_year: str | None = None) -> list[Evaluation]:
        query = self._select_related().filter(
            Q(evaluator_id=viewer_no)
            | Q(employee_id=viewer_no, eval_status=EvaluationStatus.CONFIRMED.value)
        )
        return self._list(query, eval_year)

    def _list(self, query, eval_year: str | None) -> list[Evaluation]:
        if eval_year is not None:
            query = query.filter(eval_year=eval_year)
        return [model_to_entity(model) for model in query]

    def _select_related(self):
        return EvaluationModel.objects.select_related("employee__person", "evaluator__person")
