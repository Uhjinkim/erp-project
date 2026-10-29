from board.application.ports import WorkforceGateway
from board.domain.entities import NoticeCategory
from workforce.application.services import (
    HR_MANAGER_ROLE,
    MANAGEMENT_OFFICER_ROLE,
    PAYROLL_MANAGER_ROLE,
    active_employee_roles,
)
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Employee


class DjangoWorkforceGateway(WorkforceGateway):
    def is_active_employee(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def eligible_notice_categories(self, employee_no: int) -> set[NoticeCategory]:
        roles = active_employee_roles(employee_no, DjangoWorkforceQueryGateway())
        categories: set[NoticeCategory] = set()
        if MANAGEMENT_OFFICER_ROLE in roles:
            categories.add(NoticeCategory.MANAGEMENT)
        if HR_MANAGER_ROLE in roles:
            categories.add(NoticeCategory.HR)
        if PAYROLL_MANAGER_ROLE in roles:
            categories.add(NoticeCategory.PAYROLL)
        return categories

    def is_board_moderator(self, employee_no: int) -> bool:
        return DjangoWorkforceQueryGateway().has_active_role(employee_no, MANAGEMENT_OFFICER_ROLE)
