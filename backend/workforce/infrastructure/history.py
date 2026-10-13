from contextlib import AbstractContextManager
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from workforce.domain.history import HistoryChange, HistoryEntry, TransferTarget
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmploymentHistory,
    EmploymentHistoryChange,
    Position,
)


def entry_to_json(entry: HistoryEntry | None) -> dict[str, object] | None:
    if entry is None:
        return None
    return {
        "start_date": entry.start_date.isoformat(),
        "end_date": entry.end_date.isoformat() if entry.end_date else None,
        "dept_no": entry.dept_no,
        "position_code": entry.position_code,
        "base_salary": str(entry.base_salary),
    }


def entry_from_json(history_id: int, values: dict[str, object] | None) -> HistoryEntry | None:
    if values is None:
        return None
    end_date = values.get("end_date")
    return HistoryEntry(
        history_id=history_id,
        start_date=date.fromisoformat(str(values["start_date"])),
        end_date=date.fromisoformat(str(end_date)) if end_date else None,
        dept_no=int(values["dept_no"]),
        position_code=str(values["position_code"]),
        base_salary=Decimal(str(values["base_salary"])),
    )


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

    def close_history(self, history_id: int, end_date: date | None) -> None:
        EmploymentHistory.objects.filter(history_id=history_id).update(end_date=end_date)

    def update_history(self, entry: HistoryEntry) -> None:
        EmploymentHistory.objects.filter(history_id=entry.history_id).update(
            start_date=entry.start_date,
            end_date=entry.end_date,
            department_id=entry.dept_no,
            position_id=entry.position_code,
            base_salary=entry.base_salary,
        )

    def delete_history(self, history_id: int) -> None:
        EmploymentHistory.objects.filter(history_id=history_id).delete()

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

    def restore_department_heads(self, employee_no: int, dept_nos: list[int]) -> list[int]:
        vacant = Department.objects.filter(dept_no__in=dept_nos, head__isnull=True)
        restored = list(vacant.values_list("dept_no", flat=True))
        Department.objects.filter(dept_no__in=restored).update(head_id=employee_no)
        return restored

    def released_heads_for(self, employee_no: int, history_id: int) -> list[int]:
        released: list[int] = []
        for dept_nos in EmploymentHistoryChange.objects.filter(
            employee_id=employee_no, history_id=history_id
        ).values_list("released_head_dept_nos", flat=True):
            released.extend(dept_no for dept_no in dept_nos if dept_no not in released)
        return released

    def record_change(self, change: HistoryChange) -> None:
        EmploymentHistoryChange.objects.create(
            employee_id=change.employee_no,
            history_id=change.history_id,
            action=change.action,
            before_values=entry_to_json(change.before),
            after_values=entry_to_json(change.after),
            released_head_dept_nos=list(change.released_head_dept_nos),
            restored_head_dept_nos=list(change.restored_head_dept_nos),
            reason=change.reason,
            changed_by_id=change.changed_by,
            changed_at=timezone.now(),
        )

    def changes(self, employee_no: int) -> list[HistoryChange]:
        return [
            HistoryChange(
                employee_no=row.employee_id,
                history_id=row.history_id,
                action=row.action,
                before=entry_from_json(row.history_id, row.before_values),
                after=entry_from_json(row.history_id, row.after_values),
                reason=row.reason,
                changed_by=row.changed_by_id,
                released_head_dept_nos=tuple(row.released_head_dept_nos),
                restored_head_dept_nos=tuple(row.restored_head_dept_nos),
                changed_at=row.changed_at,
            )
            for row in EmploymentHistoryChange.objects.filter(employee_id=employee_no)
        ]
