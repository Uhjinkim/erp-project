from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from vacation.application.dto import RequestVacationCommand, ResubmitVacationCommand
from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway
from vacation.domain.entities import VacationHistory, VacationRequest, VacationStatus
from vacation.domain.exceptions import (
    ApproverNotFoundError,
    InactiveEmployeeError,
    InsufficientLeaveDaysError,
    VacationPermissionError,
)
from vacation.domain.repositories import VacationUnitOfWork
from vacation.domain.value_objects import UseDays, VacationPeriod


class VacationService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], VacationUnitOfWork],
        workforce: WorkforceGateway,
        balances: LeaveBalanceGateway,
        clock: Callable[[], datetime],
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.workforce = workforce
        self.balances = balances
        self.clock = clock

    def request_vacation(self, command: RequestVacationCommand) -> VacationRequest:
        self._ensure_active(command.employee_no)
        approver_no = self._resolve_approver(command.employee_no)
        use_days = UseDays(command.use_days)
        self._ensure_balance(command.employee_no, command.type_id, use_days.value)
        with self.unit_of_work_factory() as uow:
            uow.types.get(command.type_id)
            request = uow.requests.add(
                VacationRequest(
                    request_id=None,
                    employee_no=command.employee_no,
                    type_id=command.type_id,
                    period=VacationPeriod(command.start, command.end),
                    use_days=use_days,
                    status=VacationStatus.PENDING,
                    approver_no=approver_no,
                    request_reason=command.reason,
                )
            )
            self._record(uow, request, None, command.employee_no, command.reason)
            return request

    def list_mine(self, employee_no: int) -> list[VacationRequest]:
        self._ensure_active(employee_no)
        with self.unit_of_work_factory() as uow:
            return uow.requests.list_for_employee(employee_no)

    def list_approvals(self, employee_no: int) -> list[VacationRequest]:
        self._ensure_active(employee_no)
        with self.unit_of_work_factory() as uow:
            requests = uow.requests.list_for_approver(employee_no)
            if self.workforce.is_hr_manager(employee_no):
                return requests
            return [request for request in requests if request.approver_no == employee_no]

    def cancel(self, request_id: int, employee_no: int) -> VacationRequest:
        return self._transition(
            request_id, employee_no, None, lambda item: item.cancel(employee_no)
        )

    def approve(self, request_id: int, employee_no: int) -> VacationRequest:
        return self._transition(
            request_id,
            employee_no,
            None,
            lambda item: item.approve(employee_no, self.clock()),
        )

    def reject(self, request_id: int, employee_no: int, reason: str) -> VacationRequest:
        return self._transition(
            request_id, employee_no, reason, lambda item: item.reject(employee_no, reason)
        )

    def recall(self, request_id: int, employee_no: int, reason: str) -> VacationRequest:
        return self._transition(
            request_id, employee_no, reason, lambda item: item.recall(employee_no, reason)
        )

    def resubmit(self, command: ResubmitVacationCommand) -> VacationRequest:
        self._ensure_active(command.employee_no)
        approver_no = self._resolve_approver(command.employee_no)
        use_days = UseDays(command.use_days)
        self._ensure_balance(command.employee_no, command.type_id, use_days.value)
        with self.unit_of_work_factory() as uow:
            uow.types.get(command.type_id)
            request = uow.requests.get(command.request_id, for_update=True)
            previous = request.status
            request.resubmit(
                command.employee_no,
                command.type_id,
                VacationPeriod(command.start, command.end),
                use_days,
                approver_no,
                command.reason,
            )
            uow.requests.save(request)
            self._record(uow, request, previous, command.employee_no, command.reason)
            return request

    def history(self, request_id: int, employee_no: int) -> list[VacationHistory]:
        self._ensure_active(employee_no)
        with self.unit_of_work_factory() as uow:
            request = uow.requests.get(request_id)
            allowed = employee_no in {request.employee_no, request.approver_no}
            if not allowed and not self.workforce.is_hr_manager(employee_no):
                raise VacationPermissionError(
                    "신청자, 승인자 또는 인사관리자만 이력을 조회할 수 있습니다."
                )
            return uow.histories.list_for_request(request_id)

    def list_types(self) -> list[object]:
        with self.unit_of_work_factory() as uow:
            return uow.types.list_active()

    def _transition(
        self,
        request_id: int,
        employee_no: int,
        reason: str | None,
        operation: Callable[[VacationRequest], None],
    ) -> VacationRequest:
        self._ensure_active(employee_no)
        with self.unit_of_work_factory() as uow:
            request = uow.requests.get(request_id, for_update=True)
            previous = request.status
            operation(request)
            uow.requests.save(request)
            self._record(uow, request, previous, employee_no, reason)
            return request

    def _record(
        self,
        uow: VacationUnitOfWork,
        request: VacationRequest,
        previous: VacationStatus | None,
        actor: int,
        reason: str | None,
    ) -> None:
        if request.request_id is None:
            raise RuntimeError("저장된 휴가 신청에 ID가 없습니다.")
        uow.histories.add(
            VacationHistory(
                history_id=None,
                request_id=request.request_id,
                from_status=previous,
                to_status=request.status,
                actor_employee_no=actor,
                reason=reason,
                changed_at=self.clock(),
            )
        )

    def _ensure_active(self, employee_no: int) -> None:
        if not self.workforce.is_active_employee(employee_no):
            raise InactiveEmployeeError("재직 중인 사원만 휴가 기능을 사용할 수 있습니다.")

    def _resolve_approver(self, employee_no: int) -> int:
        approver = self.workforce.resolve_vacation_approver(employee_no)
        if approver is None:
            raise ApproverNotFoundError("휴가 승인자를 결정할 수 없습니다.")
        return approver

    def _ensure_balance(self, employee_no: int, type_id: str, requested: Decimal) -> None:
        remaining = self.balances.remaining_days(employee_no, type_id)
        if remaining is not None and requested > remaining:
            raise InsufficientLeaveDaysError(
                f"신청일수({requested})가 잔여일수({remaining})를 초과합니다."
            )
