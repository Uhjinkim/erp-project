from typing import Protocol

from django.conf import settings
from rest_framework.request import Request

from vacation.domain.exceptions import VacationPermissionError


class EmployeeIdentity(Protocol):
    def employee_no(self, request: Request) -> int: ...


class DevelopmentHeaderIdentity:
    """Development-only identity supplied by the frontend employee picker."""

    def employee_no(self, request: Request) -> int:
        value = request.headers.get("X-Employee-No")
        if value is None:
            raise VacationPermissionError("X-Employee-No 헤더가 필요합니다.")
        try:
            return int(value)
        except ValueError as exc:
            raise VacationPermissionError("X-Employee-No 헤더는 사원번호여야 합니다.") from exc


class AuthenticatedEmployeeIdentity:
    """Production identity contract for the future employee/auth integration."""

    def employee_no(self, request: Request) -> int:
        user = request.user
        if not user.is_authenticated:
            raise VacationPermissionError("인증된 사용자만 휴가 기능을 사용할 수 있습니다.")

        employee = getattr(user, "employee", None)
        if employee is None:
            raise VacationPermissionError("인증 사용자와 연결된 사원번호가 없습니다.")
        return int(employee.employee_no)


def get_employee_identity() -> EmployeeIdentity:
    if settings.VACATION_INTEGRATION_MODE == "development":
        return DevelopmentHeaderIdentity()
    return AuthenticatedEmployeeIdentity()
