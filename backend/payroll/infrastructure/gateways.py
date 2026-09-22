from datetime import date

from payroll.application.ports import HolidayGateway, WorkforceGateway
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


class DjangoHolidayGateway(HolidayGateway):
    def holidays_in(self, year: int, month: int) -> frozenset[date]:
        return frozenset(
            PublicHolidayModel.objects.filter(
                holiday_date__year=year, holiday_date__month=month
            ).values_list("holiday_date", flat=True)
        )
