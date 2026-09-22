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
    statement_to_entity,
)
from payroll.infrastructure.models import (
    PayrollComponentTypeModel,
    PayrollHistoryModel,
    PayrollItemModel,
    PayrollStatementModel,
)


class DjangoPayrollStatementRepository(PayrollStatementRepository):
    def add(self, statement: PayrollStatement) -> PayrollStatement:
        model = PayrollStatementModel.objects.create(
            employee_id=statement.employee_no,
            period=statement.period.value,
            payment_date=statement.payment_date,
            status=statement.status.value,
            total_earnings=statement.total_earnings,
            total_deductions=statement.total_deductions,
            net_pay=statement.net_pay,
            created_by=statement.created_by,
            confirmed_by=statement.confirmed_by,
            confirmed_at=statement.confirmed_at,
        )
        return statement_to_entity(model, [])

    def get(self, statement_id: int, *, for_update: bool = False) -> PayrollStatement:
        query = PayrollStatementModel.objects
        if for_update:
            query = query.select_for_update()
        try:
            model = query.get(statement_id=statement_id)
        except PayrollStatementModel.DoesNotExist as exc:
            raise PayrollStatementNotFoundError("급여 정산을 찾을 수 없습니다.") from exc
        items = list(PayrollItemModel.objects.filter(statement_id=statement_id))
        return statement_to_entity(model, items)

    def save(self, statement: PayrollStatement) -> None:
        updated = PayrollStatementModel.objects.filter(statement_id=statement.statement_id).update(
            status=statement.status.value,
            total_earnings=statement.total_earnings,
            total_deductions=statement.total_deductions,
            net_pay=statement.net_pay,
            confirmed_by=statement.confirmed_by,
            confirmed_at=statement.confirmed_at,
        )
        if not updated:
            raise PayrollStatementNotFoundError("급여 정산을 찾을 수 없습니다.")
        PayrollItemModel.objects.filter(statement_id=statement.statement_id).delete()
        PayrollItemModel.objects.bulk_create(
            PayrollItemModel(
                statement_id=statement.statement_id,
                component_id=item.component_code,
                category=item.category.value,
                amount=item.amount,
            )
            for item in statement.items
        )

    def find_by_employee_and_period(
        self, employee_no: int, period: PayPeriod
    ) -> PayrollStatement | None:
        model = PayrollStatementModel.objects.filter(
            employee_id=employee_no, period=period.value
        ).first()
        if model is None:
            return None
        items = list(PayrollItemModel.objects.filter(statement_id=model.statement_id))
        return statement_to_entity(model, items)

    def list_for_employee(self, employee_no: int) -> list[PayrollStatement]:
        return self._to_entities(PayrollStatementModel.objects.filter(employee_id=employee_no))

    def list_all(self) -> list[PayrollStatement]:
        return self._to_entities(PayrollStatementModel.objects.all())

    def _to_entities(self, queryset) -> list[PayrollStatement]:
        models = list(queryset)
        items_by_statement: dict[int, list[PayrollItemModel]] = defaultdict(list)
        statement_ids = [model.statement_id for model in models]
        for item in PayrollItemModel.objects.filter(statement_id__in=statement_ids):
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
            actor_employee_no=history.actor_employee_no,
            reason=history.reason,
            change_summary=history.change_summary,
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
