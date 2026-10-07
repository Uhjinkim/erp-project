from dataclasses import dataclass
from decimal import Decimal

from evaluation.domain.entities import Evaluation, EvaluationHistory


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
    comments: str | None = None


@dataclass(frozen=True)
class ReassignEvaluationCommand:
    eval_id: int
    actor_no: int
    new_evaluator_no: int
    reason: str


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
        "created_by": evaluation.created_by,
        "score": f"{evaluation.score:.2f}",
        "grade": evaluation.grade.value,
        "comments": evaluation.comments,
        "eval_status": evaluation.status.value,
        "confirmed_by": evaluation.confirmed_by,
        "confirmed_at": evaluation.confirmed_at,
        "updated_at": evaluation.updated_at,
    }


def history_to_dict(entry: EvaluationHistory) -> dict[str, object]:
    return {
        "history_id": entry.history_id,
        "eval_id": entry.eval_id,
        "action": entry.action.value,
        "from_status": entry.from_status.value if entry.from_status else None,
        "to_status": entry.to_status.value,
        "actor_no": entry.actor_no,
        "actor_name": entry.actor_name,
        "from_evaluator_no": entry.from_evaluator_no,
        "to_evaluator_no": entry.to_evaluator_no,
        "score": f"{entry.score:.2f}" if entry.score is not None else None,
        "reason": entry.reason,
        "changed_at": entry.changed_at,
    }
