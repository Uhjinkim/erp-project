from django.db import IntegrityError, transaction
from django.db.models import Q

from evaluation.domain.entities import Evaluation, EvaluationHistory, EvaluationStatus
from evaluation.domain.exceptions import (
    DuplicateEvaluationError,
    EvaluationConflictError,
    EvaluationNotFoundError,
)
from evaluation.domain.repositories import (
    EvaluationHistoryRepository,
    EvaluationRepository,
    EvaluationUnitOfWork,
)
from evaluation.infrastructure.mappers import history_model_to_entity, model_to_entity
from evaluation.infrastructure.models import EvaluationHistoryModel, EvaluationModel

CONFLICT_MESSAGE = "다른 사용자가 먼저 평가를 변경했습니다. 새로고침 후 다시 시도하세요."


class DjangoEvaluationRepository(EvaluationRepository):
    def add(self, evaluation: Evaluation) -> Evaluation:
        try:
            # Savepoint so a unique violation does not poison the outer transaction.
            with transaction.atomic():
                model = EvaluationModel.objects.create(
                    employee_id=evaluation.employee_no,
                    eval_year=evaluation.eval_year,
                    snapshot_department_id=evaluation.snapshot_department_no,
                    snapshot_position_id=evaluation.snapshot_position_code,
                    evaluator_id=evaluation.evaluator_no,
                    created_by_id=evaluation.created_by,
                    score=evaluation.score,
                    grade=evaluation.grade.value,
                    comments=evaluation.comments,
                    eval_status=evaluation.status.value,
                    confirmed_by_id=evaluation.confirmed_by,
                    confirmed_at=evaluation.confirmed_at,
                    updated_at=evaluation.updated_at,
                )
        except IntegrityError as exc:
            if self.exists_for(evaluation.employee_no, evaluation.eval_year):
                raise DuplicateEvaluationError("해당 연도의 평가가 이미 존재합니다.") from exc
            raise
        return self.get(model.eval_id)

    def get(self, eval_id: int) -> Evaluation:
        try:
            return model_to_entity(self._select_related().get(eval_id=eval_id))
        except EvaluationModel.DoesNotExist as exc:
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.") from exc

    def save(self, evaluation: Evaluation, expected: Evaluation) -> Evaluation:
        # Optimistic check: the row must still look like what this request loaded.
        updated = EvaluationModel.objects.filter(
            eval_id=expected.eval_id,
            eval_status=expected.status.value,
            evaluator_id=expected.evaluator_no,
            updated_at=expected.updated_at,
        ).update(
            evaluator_id=evaluation.evaluator_no,
            score=evaluation.score,
            grade=evaluation.grade.value,
            comments=evaluation.comments,
            eval_status=evaluation.status.value,
            confirmed_by_id=evaluation.confirmed_by,
            confirmed_at=evaluation.confirmed_at,
            updated_at=evaluation.updated_at,
        )
        if not updated:
            if EvaluationModel.objects.filter(eval_id=expected.eval_id).exists():
                raise EvaluationConflictError(CONFLICT_MESSAGE)
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


class DjangoEvaluationHistoryRepository(EvaluationHistoryRepository):
    def add(self, entry: EvaluationHistory) -> EvaluationHistory:
        model = EvaluationHistoryModel.objects.create(
            evaluation_id=entry.eval_id,
            action=entry.action.value,
            from_status=entry.from_status.value if entry.from_status else None,
            to_status=entry.to_status.value,
            actor_id=entry.actor_no,
            from_evaluator_id=entry.from_evaluator_no,
            to_evaluator_id=entry.to_evaluator_no,
            score=entry.score,
            reason=entry.reason,
            changed_at=entry.changed_at,
        )
        entry.history_id = model.history_id
        return entry

    def list_for(self, eval_id: int) -> list[EvaluationHistory]:
        return [
            history_model_to_entity(model)
            for model in EvaluationHistoryModel.objects.select_related("actor__person").filter(
                evaluation_id=eval_id
            )
        ]


class DjangoEvaluationUnitOfWork(EvaluationUnitOfWork):
    def __enter__(self):
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self.evaluations = DjangoEvaluationRepository()
        self.histories = DjangoEvaluationHistoryRepository()
        return self

    def __exit__(self, *args: object):
        return self._atomic.__exit__(*args)
