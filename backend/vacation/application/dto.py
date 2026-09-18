from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal

from vacation.domain.entities import VacationHistory, VacationRequest, VacationType


@dataclass(frozen=True)
class RequestVacationCommand:
    employee_no: int
    type_id: str
    start: datetime
    end: datetime
    use_days: Decimal
    reason: str | None = None


@dataclass(frozen=True)
class ResubmitVacationCommand:
    request_id: int
    employee_no: int
    type_id: str
    start: datetime
    end: datetime
    use_days: Decimal
    reason: str | None = None


def request_to_dict(request: VacationRequest) -> dict[str, object]:
    return {
        "request_id": request.request_id,
        "employee_no": request.employee_no,
        "type_id": request.type_id,
        "start_datetime": request.period.start,
        "end_datetime": request.period.end,
        "use_days": request.use_days.value,
        "status": request.status.value,
        "approver_no": request.approver_no,
        "approved_at": request.approved_at,
        "reject_reason": request.reject_reason,
        "request_reason": request.request_reason,
    }


def history_to_dict(history: VacationHistory) -> dict[str, object]:
    return {
        **asdict(history),
        "from_status": history.from_status.value if history.from_status else None,
        "to_status": history.to_status.value,
    }


def type_to_dict(vacation_type: VacationType) -> dict[str, object]:
    return {
        "type_id": vacation_type.type_id,
        "type_name": vacation_type.type_name,
        "is_paid": vacation_type.is_paid,
        "deduct_days": vacation_type.deduct_days,
    }
