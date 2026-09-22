from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from payroll.infrastructure.gateways import PAYROLL_MANAGER_ROLE
from workforce.application.services import employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.presentation.permissions import request_employee_no


class IsPayrollManager(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True
        employee_no = request_employee_no(request)
        return employee_no is not None and employee_has_role(
            employee_no,
            PAYROLL_MANAGER_ROLE,
            DjangoWorkforceQueryGateway(),
        )
