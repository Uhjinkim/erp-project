from contextlib import AbstractContextManager
from datetime import date

from django.db import transaction

from workforce.domain.lifecycle import EmploymentState, RetiredEmployee, RetiredEmployeeCriteria
from workforce.infrastructure.models import Employee


class DjangoEmploymentLifecycleRepository:
    def transaction(self) -> AbstractContextManager[None]:
        return transaction.atomic()

    def lock_employment(self, employee_no: int) -> EmploymentState | None:
        row = (
            Employee.objects.select_for_update()
            .filter(employee_no=employee_no)
            .values_list("employee_no", "tenure_status", "hire_date", "term_date")
            .first()
        )
        return EmploymentState(*row) if row is not None else None

    def terminate(self, employee_no: int, term_date: date) -> None:
        employee = Employee.objects.get(employee_no=employee_no)
        employee.tenure_status = Employee.TenureStatus.TERMINATED
        employee.term_date = term_date
        # save()의 post_save signal이 연결 계정을 비활성화한다(HR-004).
        employee.save(update_fields=["tenure_status", "term_date"])

    def retired_employees(self, criteria: RetiredEmployeeCriteria) -> list[RetiredEmployee]:
        queryset = Employee.objects.select_related("person", "department", "position").filter(
            tenure_status=Employee.TenureStatus.TERMINATED
        )
        if criteria.name:
            queryset = queryset.filter(person__name__icontains=criteria.name)
        if criteria.dept_no is not None:
            queryset = queryset.filter(department_id=criteria.dept_no)
        if criteria.employee_no is not None:
            queryset = queryset.filter(employee_no=criteria.employee_no)
        if criteria.term_date_from is not None:
            queryset = queryset.filter(term_date__gte=criteria.term_date_from)
        if criteria.term_date_to is not None:
            queryset = queryset.filter(term_date__lte=criteria.term_date_to)
        return [
            RetiredEmployee(
                employee_no=employee.employee_no,
                person_id=employee.person_id,
                name=employee.person.name,
                dept_no=employee.department_id,
                dept_name=employee.department.dept_name if employee.department else None,
                position_code=employee.position_id,
                position_name=employee.position.position_name if employee.position else None,
                email=employee.email,
                hire_date=employee.hire_date,
                term_date=employee.term_date,
            )
            for employee in queryset.order_by("-term_date", "employee_no")
        ]
