from dataclasses import dataclass
from decimal import Decimal

from evaluation.domain.entities import Evaluation


@dataclass(frozen=True)
class CreateEvaluationCommand:
    evaluator_no: int
    employee_no: int
    eval_year: str
    score: Decimal
    comments: str = ""


@dataclass(frozen=True)
class ReviseEvaluationCommand:
    eval_id: int
    actor_no: int
    score: Decimal
    comments: str = ""


def evaluation_to_dict(evaluation: Evaluation) -> dict[str, object]:
    return {
        "eval_id": evaluation.eval_id,
        "emp_no": evaluation.employee_no,
        "employee_name": evaluation.employee_name,
        "eval_year": evaluation.eval_year,
        "snapshot_dept_no": evaluation.snapshot_department_no,
        "snapshot_pos_code": evaluation.snapshot_position_code,
        "evaluator_no": evaluation.evaluator_no,
        "evaluator_name": evaluation.evaluator_name,
        "score": f"{evaluation.score:.2f}",
        "grade": evaluation.grade.value,
        "comments": evaluation.comments,
        "eval_status": evaluation.status.value,
        "confirmed_by": evaluation.confirmed_by,
        "confirmed_at": evaluation.confirmed_at,
        "updated_at": evaluation.updated_at,
    }
