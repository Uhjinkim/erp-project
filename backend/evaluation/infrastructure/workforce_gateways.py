from evaluation.application.ports import WorkforceGateway
from evaluation.domain.entities import EvaluationTarget
from workforce.application.services import HR_MANAGER_ROLE, employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Employee


class DjangoWorkforceGateway(WorkforceGateway):
    def is_active_employee(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def is_hr_manager(self, employee_no: int) -> bool:
        return employee_has_role(employee_no, HR_MANAGER_ROLE, DjangoWorkforceQueryGateway())

    def evaluation_target(self, employee_no: int) -> EvaluationTarget | None:
        employee = (
            Employee.objects.select_related("department")
            .filter(employee_no=employee_no)
            .first()
        )
        if employee is None:
            return None
        department = employee.department
        return EvaluationTarget(
            employee_no=employee.employee_no,
            is_active=employee.is_active_employee,
            department_no=employee.department_id,
            position_code=employee.position_id,
            department_head_no=department.head_id if department is not None else None,
        )
