from django.db import transaction

from vacation.domain.entities import VacationHistory, VacationRequest
from vacation.domain.exceptions import VacationRequestNotFoundError, VacationTypeNotFoundError
from vacation.domain.repositories import (
    VacationHistoryRepository,
    VacationRequestRepository,
    VacationTypeRepository,
    VacationUnitOfWork,
)
from vacation.infrastructure.mappers import history_to_entity, request_to_entity, type_to_entity
from vacation.infrastructure.models import (
    LeaveRequestHistoryModel,
    LeaveRequestModel,
    LeaveTypeModel,
)


class DjangoVacationRequestRepository(VacationRequestRepository):
    def add(self, request: VacationRequest) -> VacationRequest:
        model = LeaveRequestModel.objects.create(
            employee_no=request.employee_no,
            vacation_type_id=request.type_id,
            start_datetime=request.period.start,
            end_datetime=request.period.end,
            use_days=request.use_days.value,
            status=request.status.value,
            approver_no=request.approver_no,
            approved_at=request.approved_at,
            reject_reason=request.reject_reason,
            request_reason=request.request_reason,
        )
        return request_to_entity(model)

    def get(self, request_id: int, *, for_update: bool = False) -> VacationRequest:
        query = LeaveRequestModel.objects
        if for_update:
            query = query.select_for_update()
        try:
            return request_to_entity(query.get(request_id=request_id))
        except LeaveRequestModel.DoesNotExist as exc:
            raise VacationRequestNotFoundError("휴가 신청을 찾을 수 없습니다.") from exc

    def save(self, request: VacationRequest) -> None:
        updated = LeaveRequestModel.objects.filter(request_id=request.request_id).update(
            vacation_type_id=request.type_id,
            start_datetime=request.period.start,
            end_datetime=request.period.end,
            use_days=request.use_days.value,
            status=request.status.value,
            approver_no=request.approver_no,
            approved_at=request.approved_at,
            reject_reason=request.reject_reason,
            request_reason=request.request_reason,
        )
        if not updated:
            raise VacationRequestNotFoundError("휴가 신청을 찾을 수 없습니다.")

    def list_for_employee(self, employee_no: int) -> list[VacationRequest]:
        return [
            request_to_entity(model)
            for model in LeaveRequestModel.objects.filter(employee_no=employee_no)
        ]

    def list_for_approver(self, employee_no: int) -> list[VacationRequest]:
        return [
            request_to_entity(model)
            for model in LeaveRequestModel.objects.filter(approver_no=employee_no)
        ]


class DjangoVacationHistoryRepository(VacationHistoryRepository):
    def add(self, history: VacationHistory) -> None:
        LeaveRequestHistoryModel.objects.create(
            request_id=history.request_id,
            from_status=history.from_status.value if history.from_status else None,
            to_status=history.to_status.value,
            actor_employee_no=history.actor_employee_no,
            reason=history.reason,
            changed_at=history.changed_at,
        )

    def list_for_request(self, request_id: int) -> list[VacationHistory]:
        return [
            history_to_entity(model)
            for model in LeaveRequestHistoryModel.objects.filter(request_id=request_id)
        ]


class DjangoVacationTypeRepository(VacationTypeRepository):
    def get(self, type_id: str):
        try:
            return type_to_entity(LeaveTypeModel.objects.get(type_id=type_id))
        except LeaveTypeModel.DoesNotExist as exc:
            raise VacationTypeNotFoundError("휴가 유형을 찾을 수 없습니다.") from exc

    def list_active(self):
        return [type_to_entity(model) for model in LeaveTypeModel.objects.order_by("type_id")]


class DjangoVacationUnitOfWork(VacationUnitOfWork):
    def __enter__(self):
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self.requests = DjangoVacationRequestRepository()
        self.histories = DjangoVacationHistoryRepository()
        self.types = DjangoVacationTypeRepository()
        return self

    def __exit__(self, *args: object):
        return self._atomic.__exit__(*args)
