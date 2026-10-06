from evaluation.domain.entities import Evaluation, EvaluationStatus
from evaluation.domain.value_objects import Grade
from evaluation.infrastructure.models import EvaluationModel


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
        confirmed_by=model.confirmed_by_id,
        confirmed_at=model.confirmed_at,
        employee_name=model.employee.person.name,
        evaluator_name=model.evaluator.person.name,
    )
