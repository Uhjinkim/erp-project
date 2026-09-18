from vacation.domain.entities import VacationHistory, VacationRequest, VacationStatus, VacationType
from vacation.domain.value_objects import UseDays, VacationPeriod
from vacation.infrastructure.models import (
    LeaveRequestHistoryModel,
    LeaveRequestModel,
    LeaveTypeModel,
)


def request_to_entity(model: LeaveRequestModel) -> VacationRequest:
    return VacationRequest(
        request_id=model.request_id,
        employee_no=model.employee_no,
        type_id=model.vacation_type_id,
        period=VacationPeriod(model.start_datetime, model.end_datetime),
        use_days=UseDays(model.use_days),
        status=VacationStatus(model.status),
        approver_no=model.approver_no,
        approved_at=model.approved_at,
        reject_reason=model.reject_reason,
        request_reason=model.request_reason,
    )


def history_to_entity(model: LeaveRequestHistoryModel) -> VacationHistory:
    return VacationHistory(
        history_id=model.history_id,
        request_id=model.request_id,
        from_status=VacationStatus(model.from_status) if model.from_status else None,
        to_status=VacationStatus(model.to_status),
        actor_employee_no=model.actor_employee_no,
        reason=model.reason,
        changed_at=model.changed_at,
    )


def type_to_entity(model: LeaveTypeModel) -> VacationType:
    return VacationType(
        type_id=model.type_id,
        type_name=model.type_name,
        is_paid=model.is_paid,
        deduct_days=model.deduct_days,
    )
