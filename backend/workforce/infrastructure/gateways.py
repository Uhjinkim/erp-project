from django.db.models import Q
from django.utils import timezone

from workforce.domain.personal_info import ProcessorContext
from workforce.domain.policies import EmployeeCandidate, EmployeeProfile
from workforce.infrastructure.models import Department, Employee, EmployeeRole


class DjangoWorkforceQueryGateway:
    def __init__(self, *, employee: Employee | None = None) -> None:
        self._employee = employee

    def is_department_head(self, employee_no: int) -> bool:
        if self._employee is not None and self._employee.employee_no == employee_no:
            hint = getattr(self._employee, "_is_department_head", None)
            if hint is not None:
                return hint
        return Department.objects.filter(head_id=employee_no).exists()

    def employee_profile(self, employee_no: int) -> EmployeeProfile | None:
        employee = self._employee
        if employee is None or employee.employee_no != employee_no:
            employee = Employee.objects.select_related("person", "department", "position").filter(
                employee_no=employee_no
            ).first()
        if employee is None:
            return None
        return EmployeeProfile(
            employee_no=employee.employee_no,
            name=employee.person.name,
            birth_date=employee.person.birth_date,
            gender=employee.person.gender,
            dept_no=employee.department_id,
            dept_name=employee.department.dept_name if employee.department else None,
            position_code=employee.position_id,
            position_name=employee.position.position_name if employee.position else None,
            tenure_status=employee.tenure_status,
            email=employee.email,
            phone=employee.phone,
            extension_no=employee.extension_no,
            address=employee.address,
            bank_code=employee.bank_code,
            account_no=employee.account_no,
            hire_date=employee.hire_date,
            term_date=employee.term_date,
        )

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

    def active_role_codes(self, employee_no: int) -> set[str]:
        now = timezone.now()
        return set(
            EmployeeRole.objects.filter(employee_id=employee_no, assigned_at__lte=now)
            .filter(Q(revoked_at__isnull=True) | Q(revoked_at__gt=now))
            .values_list("role_id", flat=True)
        )

    def processor_contexts(self, employee_nos: set[int]) -> dict[int, ProcessorContext]:
        if not employee_nos:
            return {}
        employees = list(
            Employee.objects.filter(pk__in=employee_nos).select_related("department__head")
        )
        head_nos = {
            employee.department.head_id
            for employee in employees
            if employee.department is not None and employee.department.head_id is not None
        }
        now = timezone.now()
        # 하나의 시점을 사용해 미래 부여·회수된 역할을 모든 요청자에 동일하게 적용한다.
        hr_nos = set(
            EmployeeRole.objects.filter(
                employee_id__in=employee_nos | head_nos,
                role_id="HR_MANAGER",
                assigned_at__lte=now,
            )
            .filter(Q(revoked_at__isnull=True) | Q(revoked_at__gt=now))
            .values_list("employee_id", flat=True)
        )
        result = {}
        for employee in employees:
            head = employee.department.head if employee.department is not None else None
            result[employee.employee_no] = ProcessorContext(
                requester_is_hr_manager=employee.employee_no in hr_nos,
                department_head=EmployeeCandidate(head.employee_no, head.is_active_employee)
                if head is not None else None,
                department_head_is_hr_manager=head is not None and head.employee_no in hr_nos,
            )
        return result

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

    def parent_department_head(self, employee_no: int) -> EmployeeCandidate | None:
        employee = Employee.objects.select_related("department__parent__head").filter(
            employee_no=employee_no
        ).first()
        if employee is None or employee.department is None:
            return None
        parent = employee.department.parent
        if parent is None or parent.head is None:
            return None
        return EmployeeCandidate(parent.head.employee_no, parent.head.is_active_employee)

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
