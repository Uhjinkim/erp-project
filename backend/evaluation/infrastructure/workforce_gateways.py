from datetime import date

from django.db.models import Q

from evaluation.application.ports import WorkforceGateway
from evaluation.domain.entities import EvaluationTarget, EvaluatorCandidate
from workforce.application.services import HR_MANAGER_ROLE, employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Department, Employee, EmploymentHistory


class DjangoWorkforceGateway(WorkforceGateway):
    def is_active_employee(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def is_hr_manager(self, employee_no: int) -> bool:
        return employee_has_role(employee_no, HR_MANAGER_ROLE, DjangoWorkforceQueryGateway())

    def is_department_head(self, employee_no: int) -> bool:
        return Department.objects.filter(head_id=employee_no).exists()

    def evaluator_candidates(self) -> list[EvaluatorCandidate]:
        departments = Department.objects.select_related("head__person").filter(
            head__isnull=False
        )
        return [
            EvaluatorCandidate(
                employee_no=department.head.employee_no,
                name=department.head.person.name,
                department_no=department.dept_no,
                department_name=department.dept_name,
            )
            for department in departments
            if department.head.is_active_employee
        ]

    def evaluation_target_pool(self, evaluator_no: int, as_of: date) -> list[EvaluationTarget]:
        headed = list(
            Department.objects.filter(head_id=evaluator_no).values_list("dept_no", flat=True)
        )
        if not headed:
            return []
        employee_nos = set(
            Employee.objects.filter(department_id__in=headed).values_list(
                "employee_no", flat=True
            )
        )
        # Past years use the year-end department, so include members of that date too.
        employee_nos.update(
            self._history_on(as_of)
            .filter(department_id__in=headed)
            .values_list("employee_id", flat=True)
        )
        employee_nos.update(
            Department.objects.filter(parent_id__in=headed, head__isnull=False).values_list(
                "head_id", flat=True
            )
        )
        employees = (
            Employee.objects.select_related("person")
            .filter(employee_no__in=employee_nos)
            .order_by("employee_no")
        )
        # A fixed number of queries however large the pool: the shared DB sits behind an
        # SSH tunnel, where one round trip per employee timed the picker out.
        return self._targets(list(employees), as_of)

    def evaluation_target(self, employee_no: int, as_of: date) -> EvaluationTarget | None:
        employee = (
            Employee.objects.select_related("person").filter(employee_no=employee_no).first()
        )
        if employee is None:
            return None
        return self._targets([employee], as_of)[0]

    def _targets(self, employees: list[Employee], as_of: date) -> list[EvaluationTarget]:
        assignments = self._assignments_on(employees, as_of)
        department_nos = {dept_no for dept_no, _ in assignments.values() if dept_no is not None}
        departments = {
            department.dept_no: department
            for department in Department.objects.select_related("parent").filter(
                dept_no__in=department_nos
            )
        }
        targets = []
        for employee in employees:
            department_no, position_code = assignments[employee.employee_no]
            department = departments.get(department_no) if department_no is not None else None
            parent = department.parent if department is not None else None
            targets.append(
                EvaluationTarget(
                    employee_no=employee.employee_no,
                    # 휴직자 remain evaluable; only 퇴사 removes an employee from new evaluations.
                    is_employed=employee.tenure_status != Employee.TenureStatus.TERMINATED
                    and employee.term_date is None,
                    hire_date=employee.hire_date,
                    name=employee.person.name,
                    department_no=department_no,
                    position_code=position_code,
                    # Department heads have no history, so these are the departments' current
                    # heads.
                    department_head_no=department.head_id if department is not None else None,
                    parent_department_head_no=parent.head_id if parent is not None else None,
                )
            )
        return targets

    @staticmethod
    def _history_on(as_of: date):
        return EmploymentHistory.objects.filter(start_date__lte=as_of).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=as_of)
        )

    def _assignments_on(
        self, employees: list[Employee], as_of: date
    ) -> dict[int, tuple[int | None, str | None]]:
        """Department and position from emp_history on `as_of`, per employee.

        Falls back to the current assignment when no history row covers the date, because
        the history table is not yet maintained for every employee.
        """
        assignments: dict[int, tuple[int | None, str | None]] = {
            employee.employee_no: (employee.department_id, employee.position_id)
            for employee in employees
        }
        covered: set[int] = set()
        # Newest row first, so the first row seen per employee is the one that applies.
        for history in self._history_on(as_of).filter(
            employee_id__in=assignments
        ).order_by("employee_id", "-start_date", "-history_id"):
            if history.employee_id in covered:
                continue
            covered.add(history.employee_id)
            assignments[history.employee_id] = (history.department_id, history.position_id)
        return assignments
