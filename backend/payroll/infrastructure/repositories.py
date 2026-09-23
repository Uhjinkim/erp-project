from collections import defaultdict

from django.db import transaction

from payroll.domain.entities import PayrollHistory, PayrollStatement
from payroll.domain.exceptions import PayrollComponentNotFoundError, PayrollStatementNotFoundError
from payroll.domain.repositories import (
    PayrollComponentRepository,
    PayrollHistoryRepository,
    PayrollStatementRepository,
    PayrollUnitOfWork,
)
from payroll.domain.value_objects import PayPeriod
from payroll.infrastructure.mappers import (
    component_to_entity,
    history_to_entity,
    period_to_string,
    statement_to_entity,
)
from payroll.infrastructure.models import (
    PayrollComponentTypeModel,
    PayrollDetailModel,
    PayrollHistoryModel,
    PayrollStatementModel,
)


class DjangoPayrollStatementRepository(PayrollStatementRepository):
    def add(self, statement: PayrollStatement) -> PayrollStatement:
        model = PayrollStatementModel.objects.create(
            employee_id=statement.employee_no,
            period=period_to_string(statement.period),
            payment_date=statement.payment_date,
            status=statement.status.value,
            total_earnings=statement.total_earnings,
            total_deductions=statement.total_deductions,
            net_pay=statement.net_pay,
            confirmed_by_id=statement.confirmed_by,
            confirmed_at=statement.confirmed_at,
        )
        PayrollDetailModel.objects.bulk_create(
            PayrollDetailModel(
                statement_id=model.statement_id,
                component_id=item.component_code,
                amount=item.amount,
            )
            for item in statement.items
        )
        items = list(
            PayrollDetailModel.objects.filter(statement_id=model.statement_id).select_related(
                "component"
            )
        )
        return statement_to_entity(model, items)

    def get(self, statement_id: int, *, for_update: bool = False) -> PayrollStatement:
        query = PayrollStatementModel.objects
        if for_update:
            query = query.select_for_update()
        try:
            model = query.get(statement_id=statement_id)
        except PayrollStatementModel.DoesNotExist as exc:
            raise PayrollStatementNotFoundError("급여 정산을 찾을 수 없습니다.") from exc
        items = list(
            PayrollDetailModel.objects.filter(statement_id=statement_id).select_related("component")
        )
        return statement_to_entity(model, items)

    def save(self, statement: PayrollStatement) -> None:
        updated = PayrollStatementModel.objects.filter(statement_id=statement.statement_id).update(
            status=statement.status.value,
            total_earnings=statement.total_earnings,
            total_deductions=statement.total_deductions,
            net_pay=statement.net_pay,
            confirmed_by_id=statement.confirmed_by,
            confirmed_at=statement.confirmed_at,
        )
        if not updated:
            raise PayrollStatementNotFoundError("급여 정산을 찾을 수 없습니다.")
        PayrollDetailModel.objects.filter(statement_id=statement.statement_id).delete()
        PayrollDetailModel.objects.bulk_create(
            PayrollDetailModel(
                statement_id=statement.statement_id,
                component_id=item.component_code,
                amount=item.amount,
            )
            for item in statement.items
        )

    def find_by_employee_and_period(
        self, employee_no: int, period: PayPeriod
    ) -> PayrollStatement | None:
        model = PayrollStatementModel.objects.filter(
            employee_id=employee_no, period=period_to_string(period)
        ).first()
        if model is None:
            return None
        items = list(
            PayrollDetailModel.objects.filter(statement_id=model.statement_id).select_related(
                "component"
            )
        )
        return statement_to_entity(model, items)

    def list_for_employee(self, employee_no: int) -> list[PayrollStatement]:
        return self._to_entities(PayrollStatementModel.objects.filter(employee_id=employee_no))

    def list_all(self) -> list[PayrollStatement]:
        return self._to_entities(PayrollStatementModel.objects.all())

    def _to_entities(self, queryset) -> list[PayrollStatement]:
        models = list(queryset)
        items_by_statement: dict[int, list[PayrollDetailModel]] = defaultdict(list)
        statement_ids = [model.statement_id for model in models]
        details = PayrollDetailModel.objects.filter(statement_id__in=statement_ids).select_related(
            "component"
        )
        for item in details:
            items_by_statement[item.statement_id].append(item)
        return [
            statement_to_entity(model, items_by_statement.get(model.statement_id, []))
            for model in models
        ]


class DjangoPayrollHistoryRepository(PayrollHistoryRepository):
    def add(self, history: PayrollHistory) -> None:
        PayrollHistoryModel.objects.create(
            statement_id=history.statement_id,
            action=history.action.value,
            actor_employee_id=history.actor_employee_no,
            reason=history.reason,
            changed_at=history.changed_at,
        )

    def list_for_statement(self, statement_id: int) -> list[PayrollHistory]:
        return [
            history_to_entity(model)
            for model in PayrollHistoryModel.objects.filter(statement_id=statement_id)
        ]


class DjangoPayrollComponentRepository(PayrollComponentRepository):
    def get(self, code: str):
        try:
            return component_to_entity(PayrollComponentTypeModel.objects.get(code=code))
        except PayrollComponentTypeModel.DoesNotExist as exc:
            raise PayrollComponentNotFoundError(f"구성항목을 찾을 수 없습니다: {code}") from exc

    def list_active(self):
        return [
            component_to_entity(model)
            for model in PayrollComponentTypeModel.objects.filter(is_active=True)
        ]


class DjangoPayrollUnitOfWork(PayrollUnitOfWork):
    def __enter__(self):
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        self.statements = DjangoPayrollStatementRepository()
        self.histories = DjangoPayrollHistoryRepository()
        self.components = DjangoPayrollComponentRepository()
        return self

    def __exit__(self, *args: object):
        return self._atomic.__exit__(*args)
