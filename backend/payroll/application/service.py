from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from payroll.application.dto import (
    CancelConfirmationCommand,
    ConfirmCommand,
    CreateStatementCommand,
    PayrollItemInput,
    UpdateItemsCommand,
)
from payroll.application.ports import EmployeeDisplay, HolidayGateway, WorkforceGateway
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


def _format_won(amount: Decimal) -> str:
    return f"{int(amount):,}원"


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
        self._require_not_self(command.actor_employee_no, command.employee_no)
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
            items = [item for _, item in self._resolve_items(uow, command.items)]
            # The legacy `payroll_history` table's action CHECK constraint has no "생성" value,
            # so creation itself is not recorded there (only 확정/확정취소/재확정/수정 are) —
            # even when items are supplied up front, this is still the initial state, not an edit.
            return uow.statements.add(
                PayrollStatement(
                    statement_id=None,
                    employee_no=command.employee_no,
                    period=period,
                    payment_date=payment_date,
                    status=PayrollStatus.DRAFT,
                    items=items,
                )
            )

    def update_items(self, command: UpdateItemsCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(command.statement_id, for_update=True)
            self._require_not_self(command.actor_employee_no, statement.employee_no)
            resolved = self._resolve_items(uow, command.items)
            statement.replace_items([item for _, item in resolved])
            uow.statements.save(statement)
            self._record(
                uow,
                statement,
                PayrollAction.ITEMS_UPDATED,
                command.actor_employee_no,
                reason=self._items_summary(resolved),
            )
            return statement

    def confirm(self, command: ConfirmCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(command.statement_id, for_update=True)
            self._require_not_self(command.actor_employee_no, statement.employee_no)
            is_first_confirmation = statement.confirm(command.actor_employee_no, self.clock())
            uow.statements.save(statement)
            action = PayrollAction.CONFIRMED if is_first_confirmation else PayrollAction.RECONFIRMED
            self._record(
                uow,
                statement,
                action,
                command.actor_employee_no,
                reason=f"차인지급액 {_format_won(statement.net_pay)} 확정",
            )
            return statement

    def cancel_confirmation(self, command: CancelConfirmationCommand) -> PayrollStatement:
        self._require_manager(command.actor_employee_no)
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(command.statement_id, for_update=True)
            self._require_not_self(command.actor_employee_no, statement.employee_no)
            statement.cancel_confirmation(command.reason)
            uow.statements.save(statement)
            self._record(
                uow,
                statement,
                PayrollAction.CONFIRMATION_CANCELLED,
                command.actor_employee_no,
                reason=command.reason,
            )
            return statement

    def get(self, statement_id: int, requester_employee_no: int) -> PayrollStatement:
        with self.unit_of_work_factory() as uow:
            statement = uow.statements.get(statement_id)
            self._require_visible_to_requester(statement, requester_employee_no)
            return statement

    def list_mine(self, employee_no: int) -> list[PayrollStatement]:
        # Employees only see their own payroll once the payroll manager has confirmed it; a
        # draft still being prepared is not shown on the employee's own payroll page.
        with self.unit_of_work_factory() as uow:
            statements = uow.statements.list_for_employee(employee_no)
            return [
                statement for statement in statements if statement.status == PayrollStatus.CONFIRMED
            ]

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
            self._require_visible_to_requester(statement, requester_employee_no)
            return uow.histories.list_for_statement(statement_id)

    def list_components(self) -> list[PayrollComponentType]:
        with self.unit_of_work_factory() as uow:
            return uow.components.list_active()

    def can_view_history_details(self, requester_employee_no: int) -> bool:
        # Only payroll managers see who changed what and why; employees see action and date only.
        return self.workforce.is_payroll_manager(requester_employee_no)

    def employee_displays(self, employee_nos: set[int]) -> dict[int, EmployeeDisplay]:
        return self.workforce.employee_displays(employee_nos)

    def _resolve_items(
        self, uow: PayrollUnitOfWork, entries: list[PayrollItemInput]
    ) -> list[tuple[PayrollComponentType, PayrollItem]]:
        resolved = []
        for entry in entries:
            component = uow.components.get(entry.component_code)
            if not component.is_active:
                raise PayrollComponentNotFoundError(
                    f"비활성화된 구성항목입니다: {entry.component_code}"
                )
            item = PayrollItem(
                component_code=component.code,
                category=component.category,
                amount=entry.amount,
            )
            resolved.append((component, item))
        return resolved

    def _items_summary(self, resolved: list[tuple[PayrollComponentType, PayrollItem]]) -> str:
        # `payroll_history.reason` is varchar(255) in the shared database.
        summary = ", ".join(
            f"{component.name} {_format_won(item.amount)}" for component, item in resolved
        )
        return summary if len(summary) <= 255 else summary[:252] + "..."

    def _record(
        self,
        uow: PayrollUnitOfWork,
        statement: PayrollStatement,
        action: PayrollAction,
        actor: int,
        *,
        reason: str | None,
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
            )
        )

    def _require_manager(self, employee_no: int) -> None:
        if not self.workforce.is_payroll_manager(employee_no):
            raise PayrollPermissionError("급여담당자만 수행할 수 있습니다.")

    def _require_not_self(self, actor_employee_no: int, target_employee_no: int) -> None:
        # 담당자 확인(2026-10-06): 급여담당자가 여러 명이므로 본인 급여는 다른 급여담당자가
        # 생성·수정·확정·확정취소하도록 하고, 본인은 처리할 수 없다(자기거래 방지).
        if actor_employee_no == target_employee_no:
            raise PayrollPermissionError(
                "본인 급여는 생성·수정·확정할 수 없습니다. 다른 급여담당자에게 요청하세요."
            )

    def _require_visible_to_requester(
        self, statement: PayrollStatement, requester_employee_no: int
    ) -> None:
        if self.workforce.is_payroll_manager(requester_employee_no):
            return
        if requester_employee_no != statement.employee_no:
            raise PayrollPermissionError("본인 또는 급여담당자만 조회할 수 있습니다.")
        if statement.status != PayrollStatus.CONFIRMED:
            raise PayrollPermissionError("확정된 급여만 조회할 수 있습니다.")
