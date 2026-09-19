from decimal import Decimal

from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway
from vacation.infrastructure.models import LeaveBalanceModel, LeaveTypeModel
from workforce.application.services import (
    HR_MANAGER_ROLE,
    employee_has_role,
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


class DjangoLeaveBalanceGateway(LeaveBalanceGateway):
    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        vacation_type = LeaveTypeModel.objects.filter(type_id=type_id).first()
        if vacation_type is not None and vacation_type.deduct_days == 0:
            return None

        balance = LeaveBalanceModel.objects.filter(
            employee_id=employee_no,
            vacation_type_id=type_id,
        ).first()
        # Missing balance data must fail closed for deducting leave types.
        return balance.remaining_days if balance is not None else Decimal("0")
