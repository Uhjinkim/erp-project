from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from workforce.application.services import HR_MANAGER_ROLE, employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway


def request_employee_no(request: Request) -> int | None:
    employee = getattr(request.user, "employee", None)
    return employee.employee_no if employee is not None else None


class IsHRManager(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True
        employee_no = request_employee_no(request)
        return employee_no is not None and employee_has_role(
            employee_no,
            HR_MANAGER_ROLE,
            DjangoWorkforceQueryGateway(),
        )


class IsHRManagerOrReadOnly(IsHRManager):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in SAFE_METHODS or super().has_permission(request, view)
