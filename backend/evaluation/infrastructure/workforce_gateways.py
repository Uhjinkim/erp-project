from datetime import date

from django.db.models import Q

from evaluation.application.ports import WorkforceGateway
from evaluation.domain.entities import EvaluationTarget
from workforce.application.services import HR_MANAGER_ROLE, employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Department, Employee, EmploymentHistory


class DjangoWorkforceGateway(WorkforceGateway):
    def is_active_employee(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def is_hr_manager(self, employee_no: int) -> bool:
        return employee_has_role(employee_no, HR_MANAGER_ROLE, DjangoWorkforceQueryGateway())

    def evaluation_target(self, employee_no: int, as_of: date) -> EvaluationTarget | None:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        if employee is None:
            return None

        department_no, position_code = self._assignment_on(employee, as_of)
        department = (
            Department.objects.select_related("parent").filter(dept_no=department_no).first()
            if department_no is not None
            else None
        )
        parent = department.parent if department is not None else None
        return EvaluationTarget(
            employee_no=employee.employee_no,
            # 휴직자 remain evaluable; only 퇴사 removes an employee from new evaluations.
            is_employed=employee.tenure_status != Employee.TenureStatus.TERMINATED
            and employee.term_date is None,
            department_no=department_no,
            position_code=position_code,
            # Department heads have no history, so these are the departments' current heads.
            department_head_no=department.head_id if department is not None else None,
            parent_department_head_no=parent.head_id if parent is not None else None,
        )

    def _assignment_on(self, employee: Employee, as_of: date) -> tuple[int | None, str | None]:
        """Department and position from emp_history on `as_of`.

        Falls back to the current assignment when no history row covers the date, because
        the history table is not yet maintained for every employee.
        """
        history = (
            EmploymentHistory.objects.filter(employee=employee, start_date__lte=as_of)
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=as_of))
            .order_by("-start_date", "-history_id")
            .first()
        )
        if history is not None:
            return history.department_id, history.position_id
        return employee.department_id, employee.position_id
