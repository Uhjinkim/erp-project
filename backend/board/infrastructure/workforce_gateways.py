from board.application.ports import WorkforceGateway
from board.domain.entities import NoticeCategory
from workforce.application.services import (
    HR_MANAGER_ROLE,
    MANAGEMENT_OFFICER_ROLE,
    PAYROLL_MANAGER_ROLE,
)
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Department, Employee


class DjangoWorkforceGateway(WorkforceGateway):
    def is_active_employee(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def eligible_notice_categories(self, employee_no: int) -> set[NoticeCategory]:
        gateway = DjangoWorkforceQueryGateway()
        categories: set[NoticeCategory] = set()
        if gateway.has_active_role(employee_no, MANAGEMENT_OFFICER_ROLE):
            categories.add(NoticeCategory.MANAGEMENT)
        if gateway.has_active_role(employee_no, HR_MANAGER_ROLE):
            categories.add(NoticeCategory.HR)
        if gateway.has_active_role(employee_no, PAYROLL_MANAGER_ROLE):
            categories.add(NoticeCategory.PAYROLL)
        if Department.objects.filter(head_id=employee_no).exists():
            categories.add(NoticeCategory.DEPARTMENT)
        return categories
