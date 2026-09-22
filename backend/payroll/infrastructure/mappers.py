from payroll.domain.entities import (
    ComponentCategory,
    PayrollAction,
    PayrollComponentType,
    PayrollHistory,
    PayrollItem,
    PayrollStatement,
    PayrollStatus,
)
from payroll.domain.value_objects import PayPeriod
from payroll.infrastructure.models import (
    PayrollComponentTypeModel,
    PayrollHistoryModel,
    PayrollItemModel,
    PayrollStatementModel,
)


def component_to_entity(model: PayrollComponentTypeModel) -> PayrollComponentType:
    return PayrollComponentType(
        code=model.code,
        name=model.name,
        category=ComponentCategory(model.category),
        is_active=model.is_active,
    )


def item_to_entity(model: PayrollItemModel) -> PayrollItem:
    return PayrollItem(
        item_id=model.item_id,
        component_code=model.component_id,
        category=ComponentCategory(model.category),
        amount=model.amount,
    )


def statement_to_entity(
    model: PayrollStatementModel, items: list[PayrollItemModel]
) -> PayrollStatement:
    return PayrollStatement(
        statement_id=model.statement_id,
        employee_no=model.employee_id,
        period=PayPeriod(model.period),
        payment_date=model.payment_date,
        status=PayrollStatus(model.status),
        created_by=model.created_by,
        items=[item_to_entity(item) for item in items],
        confirmed_by=model.confirmed_by,
        confirmed_at=model.confirmed_at,
    )


def history_to_entity(model: PayrollHistoryModel) -> PayrollHistory:
    return PayrollHistory(
        history_id=model.history_id,
        statement_id=model.statement_id,
        action=PayrollAction(model.action),
        actor_employee_no=model.actor_employee_no,
        changed_at=model.changed_at,
        reason=model.reason,
        change_summary=model.change_summary,
    )
