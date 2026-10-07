from evaluation.domain.entities import (
    Evaluation,
    EvaluationAction,
    EvaluationHistory,
    EvaluationStatus,
)
from evaluation.domain.value_objects import Grade
from evaluation.infrastructure.models import EvaluationHistoryModel, EvaluationModel


def model_to_entity(model: EvaluationModel) -> Evaluation:
    return Evaluation(
        eval_id=model.eval_id,
        employee_no=model.employee_id,
        eval_year=model.eval_year,
        snapshot_department_no=model.snapshot_department_id,
        snapshot_position_code=model.snapshot_position_id,
        evaluator_no=model.evaluator_id,
        score=model.score,
        grade=Grade(model.grade),
        comments=model.comments or "",
        status=EvaluationStatus(model.eval_status),
        updated_at=model.updated_at,
        created_by=model.created_by_id,
        confirmed_by=model.confirmed_by_id,
        confirmed_at=model.confirmed_at,
        employee_name=model.employee.person.name,
        evaluator_name=model.evaluator.person.name,
    )


def history_model_to_entity(model: EvaluationHistoryModel) -> EvaluationHistory:
    return EvaluationHistory(
        history_id=model.history_id,
        eval_id=model.evaluation_id,
        action=EvaluationAction(model.action),
        from_status=EvaluationStatus(model.from_status) if model.from_status else None,
        to_status=EvaluationStatus(model.to_status),
        actor_no=model.actor_id,
        changed_at=model.changed_at,
        from_evaluator_no=model.from_evaluator_id,
        to_evaluator_no=model.to_evaluator_id,
        score=model.score,
        reason=model.reason,
        actor_name=model.actor.person.name,
    )
