from dataclasses import dataclass
from decimal import Decimal

from payroll.domain.entities import (
    PayrollComponentType,
    PayrollHistory,
    PayrollItem,
    PayrollStatement,
)


@dataclass(frozen=True)
class PayrollItemInput:
    component_code: str
    amount: Decimal


@dataclass(frozen=True)
class CreateStatementCommand:
    actor_employee_no: int
    employee_no: int
    year: int
    month: int


@dataclass(frozen=True)
class UpdateItemsCommand:
    actor_employee_no: int
    statement_id: int
    items: list[PayrollItemInput]


@dataclass(frozen=True)
class ConfirmCommand:
    actor_employee_no: int
    statement_id: int


@dataclass(frozen=True)
class CancelConfirmationCommand:
    actor_employee_no: int
    statement_id: int
    reason: str


def statement_to_dict(statement: PayrollStatement) -> dict[str, object]:
    return {
        "statement_id": statement.statement_id,
        "employee_no": statement.employee_no,
        "year": statement.period.year,
        "month": statement.period.month,
        "payment_date": statement.payment_date,
        "status": statement.status.value,
        "items": [item_to_dict(item) for item in statement.items],
        "total_earnings": statement.total_earnings,
        "total_deductions": statement.total_deductions,
        "net_pay": statement.net_pay,
        "created_by": statement.created_by,
        "confirmed_by": statement.confirmed_by,
        "confirmed_at": statement.confirmed_at,
    }


def item_to_dict(item: PayrollItem) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "component_code": item.component_code,
        "category": item.category.value,
        "amount": item.amount,
    }


def history_to_dict(history: PayrollHistory) -> dict[str, object]:
    return {
        "history_id": history.history_id,
        "statement_id": history.statement_id,
        "action": history.action.value,
        "actor_employee_no": history.actor_employee_no,
        "reason": history.reason,
        "change_summary": history.change_summary,
        "changed_at": history.changed_at,
    }


def component_to_dict(component: PayrollComponentType) -> dict[str, object]:
    return {
        "code": component.code,
        "name": component.name,
        "category": component.category.value,
        "is_active": component.is_active,
    }
