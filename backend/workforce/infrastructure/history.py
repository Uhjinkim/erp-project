from contextlib import AbstractContextManager
from datetime import date

from django.db import transaction

from workforce.domain.history import HistoryEntry, TransferTarget
from workforce.infrastructure.models import Department, Employee, EmploymentHistory, Position


class DjangoEmploymentHistoryRepository:
    def transaction(self) -> AbstractContextManager[None]:
        return transaction.atomic()

    def employee_exists(self, employee_no: int) -> bool:
        return Employee.objects.filter(employee_no=employee_no).exists()

    def lock_transfer_target(self, employee_no: int) -> TransferTarget | None:
        row = (
            Employee.objects.select_for_update()
            .filter(employee_no=employee_no)
            .values_list(
                "employee_no", "tenure_status", "hire_date", "department_id", "position_id"
            )
            .first()
        )
        return TransferTarget(*row) if row is not None else None

    def history(self, employee_no: int) -> list[HistoryEntry]:
        rows = (
            EmploymentHistory.objects.select_related("department", "position")
            .filter(employee_id=employee_no)
            .order_by("-start_date", "-history_id")
        )
        return [
            HistoryEntry(
                history_id=row.history_id,
                start_date=row.start_date,
                end_date=row.end_date,
                dept_no=row.department_id,
                position_code=row.position_id,
                base_salary=row.base_salary,
                dept_name=row.department.dept_name,
                position_name=row.position.position_name,
            )
            for row in rows
        ]

    def department_exists(self, dept_no: int) -> bool:
        return Department.objects.filter(dept_no=dept_no).exists()

    def position_exists(self, position_code: str) -> bool:
        return Position.objects.filter(position_code=position_code).exists()

    def close_history(self, history_id: int, end_date: date) -> None:
        EmploymentHistory.objects.filter(history_id=history_id).update(end_date=end_date)

    def add_history(self, employee_no: int, entry: HistoryEntry) -> int:
        return EmploymentHistory.objects.create(
            employee_id=employee_no,
            start_date=entry.start_date,
            end_date=entry.end_date,
            department_id=entry.dept_no,
            position_id=entry.position_code,
            base_salary=entry.base_salary,
        ).history_id

    def update_current_assignment(
        self, employee_no: int, *, dept_no: int, position_code: str
    ) -> None:
        Employee.objects.filter(employee_no=employee_no).update(
            department_id=dept_no, position_id=position_code
        )

    def release_department_heads(self, employee_no: int, *, keep_dept_no: int) -> list[int]:
        headed = Department.objects.filter(head_id=employee_no).exclude(dept_no=keep_dept_no)
        released = list(headed.values_list("dept_no", flat=True))
        headed.update(head=None)
        return released
