from django.db.models import Exists, OuterRef

from accounts.models import User
from workforce.infrastructure.models import Department, Employee


def hydrate_session_employee(user: User) -> Employee | None:
    """세션 요청 안에서 재직 검사와 프로필 직렬화가 같은 조회를 사용한다."""
    if user.employee_id is None:
        return None
    employee = (
        Employee.objects.select_related("person", "department", "position")
        .annotate(_is_department_head=Exists(Department.objects.filter(head_id=OuterRef("pk"))))
        .get(pk=user.employee_id)
    )
    user.employee = employee
    return employee
