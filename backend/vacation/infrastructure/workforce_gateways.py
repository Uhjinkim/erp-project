from decimal import Decimal

from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway
from vacation.domain.balance import balance_type_id
from vacation.domain.entities import VacationType
from vacation.domain.exceptions import InsufficientLeaveDaysError
from vacation.infrastructure.models import LeaveBalanceModel, LeaveTypeModel
from workforce.application.services import (
    HR_MANAGER_ROLE,
    employee_has_role,
    has_vacation_hr_approvers,
    resolve_vacation_approver,
)
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Employee


class DjangoWorkforceGateway(WorkforceGateway):
    def _employee(self, employee_no: int) -> Employee | None:
        return (
            Employee.objects.select_related("department__head")
            .filter(employee_no=employee_no)
            .first()
        )

    def is_active_employee(self, employee_no: int) -> bool:
        employee = self._employee(employee_no)
        return employee is not None and employee.is_active_employee

    def resolve_vacation_approver(self, employee_no: int) -> int | None:
        employee = self._employee(employee_no)
        if employee is None or not employee.is_active_employee:
            return None
        return resolve_vacation_approver(employee_no, DjangoWorkforceQueryGateway())

    def is_hr_manager(self, employee_no: int) -> bool:
        return employee_has_role(employee_no, HR_MANAGER_ROLE, DjangoWorkforceQueryGateway())

    def has_hr_managers(self) -> bool:
        return has_vacation_hr_approvers(DjangoWorkforceQueryGateway())


class DjangoLeaveBalanceGateway(LeaveBalanceGateway):
    def remaining_for_types(
        self, employee_no: int, types: list[VacationType]
    ) -> dict[str, Decimal | None]:
        deductible = {balance_type_id(item.type_id) for item in types if item.deduct_days != 0}
        balances = dict(LeaveBalanceModel.objects.filter(
            employee_id=employee_no, vacation_type_id__in=deductible,
        ).values_list("vacation_type_id", "remaining_days"))
        return {
            item.type_id: balances.get(balance_type_id(item.type_id), Decimal("0"))
            if item.deduct_days != 0 else None
            for item in types
        }

    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        vacation_type = LeaveTypeModel.objects.filter(type_id=type_id).first()
        if vacation_type is not None and vacation_type.deduct_days == 0:
            return None

        balance = LeaveBalanceModel.objects.filter(
            employee_id=employee_no,
            vacation_type_id=balance_type_id(type_id),
        ).first()
        # Missing balance data must fail closed for deducting leave types.
        return balance.remaining_days if balance is not None else Decimal("0")

    def deduct(self, employee_no: int, type_id: str, days: Decimal) -> bool:
        if LeaveTypeModel.objects.get(type_id=type_id).deduct_days == 0:
            return False
        balance = LeaveBalanceModel.objects.select_for_update().filter(
            employee_id=employee_no, vacation_type_id=balance_type_id(type_id)
        ).first()
        remaining = balance.remaining_days if balance is not None else Decimal("0")
        if balance is None or days > remaining:
            raise InsufficientLeaveDaysError(
                f"신청일수({days})가 잔여일수({remaining})를 초과합니다."
            )
        balance.remaining_days -= days
        balance.save(update_fields=["remaining_days", "updated_at"])
        return True

    def restore(self, employee_no: int, type_id: str, days: Decimal) -> None:
        # A missing charged balance is an infrastructure failure, not permission to
        # silently lose the refund. Let the unit of work roll back the recall.
        balance = LeaveBalanceModel.objects.select_for_update().get(
            employee_id=employee_no, vacation_type_id=balance_type_id(type_id)
        )
        balance.remaining_days += days
        balance.save(update_fields=["remaining_days", "updated_at"])
