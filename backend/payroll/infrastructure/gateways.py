from datetime import date

from payroll.application.ports import (
    EmployeeDisplay,
    HolidayGateway,
    PayrollTargetEmployee,
    WorkforceGateway,
)
from payroll.infrastructure.models import PublicHolidayModel
from workforce.application.services import employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Employee

PAYROLL_MANAGER_ROLE = "PAYROLL_MANAGER"


class DjangoWorkforceGateway(WorkforceGateway):
    def employee_exists(self, employee_no: int) -> bool:
        return Employee.objects.filter(employee_no=employee_no).exists()

    def is_payroll_manager(self, employee_no: int) -> bool:
        return employee_has_role(employee_no, PAYROLL_MANAGER_ROLE, DjangoWorkforceQueryGateway())

    def employee_displays(self, employee_nos: set[int]) -> dict[int, EmployeeDisplay]:
        employees = Employee.objects.select_related("person", "position").filter(
            employee_no__in=employee_nos
        )
        return {
            employee.employee_no: EmployeeDisplay(
                employee_no=employee.employee_no,
                name=employee.person.name,
                position_name=employee.position.position_name if employee.position else None,
            )
            for employee in employees
        }

    def list_payroll_targets(self) -> list[PayrollTargetEmployee]:
        employees = Employee.objects.select_related("person", "department", "position").order_by(
            "employee_no"
        )
        return [
            PayrollTargetEmployee(
                employee_no=employee.employee_no,
                name=employee.person.name,
                dept_no=employee.department_id,
                dept_name=employee.department.dept_name if employee.department else None,
                position_name=employee.position.position_name if employee.position else None,
                is_active=employee.is_active_employee,
            )
            for employee in employees
        ]


class DjangoHolidayGateway(HolidayGateway):
    def holidays_in(self, year: int, month: int) -> frozenset[date]:
        return frozenset(
            PublicHolidayModel.objects.filter(
                holiday_date__year=year, holiday_date__month=month
            ).values_list("holiday_date", flat=True)
        )
