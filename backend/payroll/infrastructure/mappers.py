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
    PayrollDetailModel,
    PayrollHistoryModel,
    PayrollStatementModel,
)


def component_to_entity(model: PayrollComponentTypeModel) -> PayrollComponentType:
    return PayrollComponentType(
        code=model.code,
        name=model.name,
        category=ComponentCategory(model.category),
        is_active=model.is_active,
    )


def period_to_string(period: PayPeriod) -> str:
    return f"{period.year:04d}{period.month:02d}"


def string_to_period(value: str) -> PayPeriod:
    return PayPeriod.of(int(value[:4]), int(value[4:6]))


def item_to_entity(model: PayrollDetailModel) -> PayrollItem:
    return PayrollItem(
        item_id=model.detail_id,
        component_code=model.component_id,
        category=ComponentCategory(model.component.category),
        amount=model.amount,
    )


def statement_to_entity(
    model: PayrollStatementModel, items: list[PayrollDetailModel]
) -> PayrollStatement:
    return PayrollStatement(
        statement_id=model.statement_id,
        employee_no=model.employee_id,
        period=string_to_period(model.period),
        payment_date=model.payment_date,
        status=PayrollStatus(model.status),
        items=[item_to_entity(item) for item in items],
        confirmed_by=model.confirmed_by_id,
        confirmed_at=model.confirmed_at,
    )


def history_to_entity(model: PayrollHistoryModel) -> PayrollHistory:
    return PayrollHistory(
        history_id=model.history_id,
        statement_id=model.statement_id,
        action=PayrollAction(model.action),
        actor_employee_no=model.actor_employee_id,
        changed_at=model.changed_at,
        reason=model.reason,
    )
