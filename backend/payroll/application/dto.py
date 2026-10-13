from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from payroll.application.ports import PayrollTargetEmployee
from payroll.domain.entities import (
    PayrollComponentType,
    PayrollHistory,
    PayrollItem,
    PayrollStatement,
)
from payroll.domain.policies import payslip_rank


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
    items: list[PayrollItemInput] = field(default_factory=list)
    # None means the settlement-date policy decides (매월 25일, 휴일이면 직전 평일).
    payment_date: date | None = None


@dataclass(frozen=True)
class UpdateItemsCommand:
    actor_employee_no: int
    statement_id: int
    items: list[PayrollItemInput]
    payment_date: date | None = None


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
        "items": [
            item_to_dict(item)
            for item in sorted(statement.items, key=lambda item: payslip_rank(item.component_code))
        ],
        "total_earnings": statement.total_earnings,
        "total_deductions": statement.total_deductions,
        "net_pay": statement.net_pay,
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


def history_to_dict(history: PayrollHistory, actor_name: str | None) -> dict[str, object]:
    return {
        "history_id": history.history_id,
        "statement_id": history.statement_id,
        "action": history.action.value,
        "actor_employee_no": history.actor_employee_no,
        "actor_name": actor_name,
        "reason": history.reason,
        "changed_at": history.changed_at,
    }


def history_to_summary_dict(history: PayrollHistory) -> dict[str, object]:
    return {
        "history_id": history.history_id,
        "statement_id": history.statement_id,
        "action": history.action.value,
        "changed_at": history.changed_at,
    }


def component_to_dict(component: PayrollComponentType) -> dict[str, object]:
    return {
        "code": component.code,
        "name": component.name,
        "category": component.category.value,
        "is_active": component.is_active,
    }


def target_employee_to_dict(employee: PayrollTargetEmployee) -> dict[str, object]:
    return {
        "emp_no": employee.employee_no,
        "name": employee.name,
        "dept_no": employee.dept_no,
        "dept_name": employee.dept_name,
        "position_name": employee.position_name,
        "is_active": employee.is_active,
    }
