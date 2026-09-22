from collections.abc import Callable
from datetime import datetime

from payroll.application.dto import (
    CancelConfirmationCommand,
    ConfirmCommand,
    CreateStatementCommand,
    PayrollItemInput,
    UpdateItemsCommand,
)
from payroll.application.ports import HolidayGateway, WorkforceGateway
from payroll.domain.entities import (
    PayrollAction,
    PayrollComponentType,
    PayrollHistory,
    PayrollItem,
    PayrollStatement,
    PayrollStatus,
)
from payroll.domain.exceptions import (
    DuplicatePayrollStatementError,
    InactiveEmployeeError,
    PayrollComponentNotFoundError,
    PayrollPermissionError,
)
from payroll.domain.policies import resolve_payment_date
from payroll.domain.repositories import PayrollUnitOfWork
from payroll.domain.value_objects import PayPeriod


class PayrollService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], PayrollUnitOfWork],
        workforce: WorkforceGateway,
        holidays: HolidayGateway,
        clock: Callable[[], datetime],
    ) -> None:
        self.unit_of_work_factory = unit_of_work_factory
        self.workforce = workforce
        self.holidays = holidays
        self.clock = clock

    def create_statement(self, command: CreateStatementCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        if not self.workforce.employee_exists(command.employee_no):
            raise InactiveEmployeeError("대상 사원을 찾을 수 없습니다.")
        period = PayPeriod.of(command.year, command.month)
        with self.unit_of_work_factory() as uow:
            if uow.statements.find_by_employee_and_period(command.employee_no, period) is not None:
                raise DuplicatePayrollStatementError(
                    "해당 사원의 해당 정산월 급여가 이미 존재합니다."
                )
            payment_date = resolve_payment_date(
                period, self.holidays.holidays_in(period.year, period.month)
            )
            statement = uow.statements.add(
                PayrollStatement(
                    statement_id=None,
                    employee_no=command.employee_no,
                    period=period,
                    payment_date=payment_date,
                    status=PayrollStatus.DRAFT,
                    created_by=command.actor_employee_no,
                )
            )
            self._record(
                uow,
                statement,
                PayrollAction.CREATED,
                command.actor_employee_no,
                reason=None,
                change_summary=f"{period.year}년 {period.month}월 급여 생성",
            )
            return statement

    def update_items(self, command: UpdateItemsCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(command.statement_id, for_update=True)
            items = [self._resolve_item(uow, entry) for entry in command.items]
            statement.replace_items(items)
            uow.statements.save(statement)
            self._record(
                uow,
                statement,
                PayrollAction.ITEMS_UPDATED,
                command.actor_employee_no,
                reason=None,
                change_summary=self._items_summary(items),
            )
            return statement

    def confirm(self, command: ConfirmCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(command.statement_id, for_update=True)
            is_first_confirmation = statement.confirm(command.actor_employee_no, self.clock())
            uow.statements.save(statement)
            action = PayrollAction.CONFIRMED if is_first_confirmation else PayrollAction.RECONFIRMED
            self._record(
                uow,
                statement,
                action,
                command.actor_employee_no,
                reason=None,
                change_summary=f"지급액 {statement.net_pay}원 확정",
            )
            return statement

    def cancel_confirmation(self, command: CancelConfirmationCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(command.statement_id, for_update=True)
            statement.cancel_confirmation(command.reason)
            uow.statements.save(statement)
            self._record(
                uow,
                statement,
                PayrollAction.CONFIRMATION_CANCELLED,
                command.actor_employee_no,
                reason=command.reason,
                change_summary=None,
            )
            return statement

    def get(self, statement_id: int, requester_employee_no: int) -> PayrollStatement:
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(statement_id)
            self._require_owner_or_manager(statement.employee_no, requester_employee_no)
            return statement

    def list_mine(self, employee_no: int) -> list[PayrollStatement]:
        with self.unit_of_work_factory() as uow:
            return uow.statements.list_for_employee(employee_no)

    def list_for_employee(
        self, target_employee_no: int | None, requester_employee_no: int
    ) -> list[PayrollStatement]:
        self._require_manager(requester_employee_no)
        with self.unit_of_work_factory() as uow:
            if target_employee_no is None:
                return uow.statements.list_all()
            return uow.statements.list_for_employee(target_employee_no)

    def history(self, statement_id: int, requester_employee_no: int) -> list[PayrollHistory]:
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(statement_id)
            self._require_owner_or_manager(statement.employee_no, requester_employee_no)
            return uow.histories.list_for_statement(statement_id)

    def list_components(self) -> list[PayrollComponentType]:
        with self.unit_of_work_factory() as uow:
            return uow.components.list_active()

    def _resolve_item(self, uow: PayrollUnitOfWork, entry: PayrollItemInput) -> PayrollItem:
        component = uow.components.get(entry.component_code)
        if not component.is_active:
            raise PayrollComponentNotFoundError(
                f"비활성화된 구성항목입니다: {entry.component_code}"
            )
        return PayrollItem(
            component_code=component.code,
            category=component.category,
            amount=entry.amount,
        )

    def _items_summary(self, items: list[PayrollItem]) -> str:
        return ", ".join(f"{item.component_code}={item.amount}" for item in items)

    def _record(
        self,
        uow: PayrollUnitOfWork,
        statement: PayrollStatement,
        action: PayrollAction,
        actor: int,
        *,
        reason: str | None,
        change_summary: str | None,
    ) -> None:
        if statement.statement_id is None:
            raise RuntimeError("저장된 급여에 ID가 없습니다.")
        uow.histories.add(
            PayrollHistory(
                history_id=None,
                statement_id=statement.statement_id,
                action=action,
                actor_employee_no=actor,
                changed_at=self.clock(),
                reason=reason,
                change_summary=change_summary,
            )
        )

    def _require_manager(self, employee_no: int) -> None:
        if not self.workforce.is_payroll_manager(employee_no):
            raise PayrollPermissionError("급여담당자만 수행할 수 있습니다.")

    def _require_owner_or_manager(self, owner_employee_no: int, requester_employee_no: int) -> None:
        if requester_employee_no == owner_employee_no:
            return
        if self.workforce.is_payroll_manager(requester_employee_no):
            return
        raise PayrollPermissionError("본인 또는 급여담당자만 조회할 수 있습니다.")
