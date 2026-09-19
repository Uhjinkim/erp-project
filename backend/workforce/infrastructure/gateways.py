from django.db.models import Q
from django.utils import timezone

from workforce.domain.policies import EmployeeCandidate
from workforce.infrastructure.models import Employee, EmployeeRole


class DjangoWorkforceQueryGateway:
    def has_active_role(self, employee_no: int, role_code: str) -> bool:
        now = timezone.now()
        return (
            EmployeeRole.objects.filter(
                employee_id=employee_no,
                role_id=role_code,
                assigned_at__lte=now,
            )
            .filter(Q(revoked_at__isnull=True) | Q(revoked_at__gt=now))
            .exists()
        )

    def department_head(self, employee_no: int) -> EmployeeCandidate | None:
        employee = Employee.objects.select_related("department__head").filter(
            employee_no=employee_no
        ).first()
        if employee is None or employee.department is None or employee.department.head is None:
            return None
        head = employee.department.head
        return EmployeeCandidate(head.employee_no, head.is_active_employee)

    def active_role_holders(self, role_code: str, *, limit: int) -> list[EmployeeCandidate]:
        now = timezone.now()
        employees = (
            Employee.objects.filter(
                role_assignments__role_id=role_code,
                role_assignments__assigned_at__lte=now,
            )
            .filter(
                Q(role_assignments__revoked_at__isnull=True)
                | Q(role_assignments__revoked_at__gt=now)
            )
            .distinct()
            .order_by("employee_no")[:limit]
        )
        return [EmployeeCandidate(item.employee_no, item.is_active_employee) for item in employees]

    def employee_is_active(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def has_active_assignment(self, employee_no: int, role_code: str) -> bool:
        return self.has_active_role(employee_no, role_code)

    def active_role_holder_count(self, role_code: str) -> int:
        now = timezone.now()
        return (
            EmployeeRole.objects.filter(role_id=role_code, assigned_at__lte=now)
            .filter(Q(revoked_at__isnull=True) | Q(revoked_at__gt=now))
            .values("employee_id")
            .distinct()
            .count()
        )

    def assign_role(self, employee_no: int, role_code: str) -> int:
        assignment = EmployeeRole.objects.create(
            employee_id=employee_no,
            role_id=role_code,
            assigned_at=timezone.now(),
        )
        return assignment.employee_role_id

    def revoke_role(self, employee_no: int, assignment_id: int) -> bool:
        assignment = EmployeeRole.objects.filter(
            employee_id=employee_no,
            employee_role_id=assignment_id,
            revoked_at__isnull=True,
        ).first()
        if assignment is None:
            return False
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=["revoked_at"])
        return True
