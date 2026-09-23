from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from payroll.application.dto import (
    CancelConfirmationCommand,
    ConfirmCommand,
    CreateStatementCommand,
    PayrollItemInput,
    UpdateItemsCommand,
)
from payroll.application.ports import HolidayGateway, WorkforceGateway
from payroll.application.service import PayrollService
from payroll.domain.entities import (
    ComponentCategory,
    PayrollComponentType,
    PayrollHistory,
    PayrollStatement,
)
from payroll.domain.exceptions import (
    DuplicatePayrollStatementError,
    PayrollComponentNotFoundError,
    PayrollPermissionError,
)
from payroll.domain.repositories import (
    PayrollComponentRepository,
    PayrollHistoryRepository,
    PayrollStatementRepository,
    PayrollUnitOfWork,
)
from payroll.domain.value_objects import PayPeriod


class FakeStatements(PayrollStatementRepository):
    def __init__(self) -> None:
        self.items: dict[int, PayrollStatement] = {}

    def add(self, statement: PayrollStatement) -> PayrollStatement:
        statement.statement_id = len(self.items) + 1
        self.items[statement.statement_id] = statement
        return statement

    def get(self, statement_id: int, *, for_update: bool = False) -> PayrollStatement:
        return self.items[statement_id]

    def save(self, statement: PayrollStatement) -> None:
        assert statement.statement_id is not None
        self.items[statement.statement_id] = statement

    def find_by_employee_and_period(self, employee_no: int, period: PayPeriod):
        return next(
            (
                item
                for item in self.items.values()
                if item.employee_no == employee_no and item.period == period
            ),
            None,
        )

    def list_for_employee(self, employee_no: int) -> list[PayrollStatement]:
        return [item for item in self.items.values() if item.employee_no == employee_no]

    def list_all(self) -> list[PayrollStatement]:
        return list(self.items.values())


class FakeHistories(PayrollHistoryRepository):
    def __init__(self) -> None:
        self.items: list[PayrollHistory] = []

    def add(self, history: PayrollHistory) -> None:
        self.items.append(history)

    def list_for_statement(self, statement_id: int) -> list[PayrollHistory]:
        return [item for item in self.items if item.statement_id == statement_id]


class FakeComponents(PayrollComponentRepository):
    catalog = {
        "BASE_PAY": PayrollComponentType("BASE_PAY", "기본급", ComponentCategory.EARNING, True),
        "NATIONAL_PENSION": PayrollComponentType(
            "NATIONAL_PENSION", "국민연금", ComponentCategory.DEDUCTION, True
        ),
        "RETIRED_ITEM": PayrollComponentType(
            "RETIRED_ITEM", "폐지된 항목", ComponentCategory.EARNING, False
        ),
    }

    def get(self, code: str) -> PayrollComponentType:
        try:
            return self.catalog[code]
        except KeyError as exc:
            raise PayrollComponentNotFoundError(code) from exc

    def list_active(self) -> list[PayrollComponentType]:
        return [item for item in self.catalog.values() if item.is_active]


class FakeUnitOfWork(PayrollUnitOfWork):
    def __init__(self) -> None:
        self.statements = FakeStatements()
        self.histories = FakeHistories()
        self.components = FakeComponents()

    def __enter__(self):
        return self

    def __exit__(self, *args: object):
        return None


class FakeWorkforce(WorkforceGateway):
    def __init__(self, managers: set[int] | None = None) -> None:
        self.managers = managers or {9001}

    def employee_exists(self, employee_no: int) -> bool:
        return employee_no in {1001, 9001}

    def is_payroll_manager(self, employee_no: int) -> bool:
        return employee_no in self.managers


class FakeHolidays(HolidayGateway):
    def holidays_in(self, year: int, month: int) -> frozenset[date]:
        return frozenset()


def service(uow: FakeUnitOfWork, managers: set[int] | None = None) -> PayrollService:
    return PayrollService(
        unit_of_work_factory=lambda: uow,
        workforce=FakeWorkforce(managers),
        holidays=FakeHolidays(),
        clock=lambda: datetime(2026, 9, 20, tzinfo=UTC),
    )


def test_only_payroll_manager_can_create_a_statement() -> None:
    with pytest.raises(PayrollPermissionError):
        service(FakeUnitOfWork()).create_statement(
            CreateStatementCommand(actor_employee_no=1001, employee_no=1001, year=2026, month=9)
        )


def test_create_statement_rejects_duplicate_employee_and_period() -> None:
    uow = FakeUnitOfWork()
    payroll = service(uow)
    payroll.create_statement(
        CreateStatementCommand(actor_employee_no=9001, employee_no=1001, year=2026, month=9)
    )
    with pytest.raises(DuplicatePayrollStatementError):
        payroll.create_statement(
            CreateStatementCommand(actor_employee_no=9001, employee_no=1001, year=2026, month=9)
        )


def test_update_items_rejects_inactive_component() -> None:
    uow = FakeUnitOfWork()
    payroll = service(uow)
    created = payroll.create_statement(
        CreateStatementCommand(actor_employee_no=9001, employee_no=1001, year=2026, month=9)
    )
    with pytest.raises(PayrollComponentNotFoundError):
        payroll.update_items(
            UpdateItemsCommand(
                actor_employee_no=9001,
                statement_id=created.statement_id or 0,
                items=[PayrollItemInput(component_code="RETIRED_ITEM", amount=Decimal("1000"))],
            )
        )


def test_confirm_cancel_and_reconfirm_are_all_recorded_as_history() -> None:
    uow = FakeUnitOfWork()
    payroll = service(uow)
    created = payroll.create_statement(
        CreateStatementCommand(actor_employee_no=9001, employee_no=1001, year=2026, month=9)
    )
    statement_id = created.statement_id or 0
    payroll.update_items(
        UpdateItemsCommand(
            actor_employee_no=9001,
            statement_id=statement_id,
            items=[PayrollItemInput(component_code="BASE_PAY", amount=Decimal("3000000"))],
        )
    )
    payroll.confirm(ConfirmCommand(actor_employee_no=9001, statement_id=statement_id))
    payroll.cancel_confirmation(
        CancelConfirmationCommand(
            actor_employee_no=9001, statement_id=statement_id, reason="금액 정정"
        )
    )
    payroll.confirm(ConfirmCommand(actor_employee_no=9001, statement_id=statement_id))

    actions = [entry.action.value for entry in uow.histories.list_for_statement(statement_id)]
    assert actions == ["수정", "확정", "확정취소", "재확정"]


def test_employee_can_view_only_their_own_statement() -> None:
    uow = FakeUnitOfWork()
    payroll = service(uow)
    created = payroll.create_statement(
        CreateStatementCommand(actor_employee_no=9001, employee_no=1001, year=2026, month=9)
    )
    statement_id = created.statement_id or 0

    assert payroll.get(statement_id, 1001).employee_no == 1001
    with pytest.raises(PayrollPermissionError):
        payroll.get(statement_id, 1002)
    assert payroll.get(statement_id, 9001).employee_no == 1001
