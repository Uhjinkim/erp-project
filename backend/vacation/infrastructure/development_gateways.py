from decimal import Decimal

from django.conf import settings
from django.db.models import Sum

from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway
from vacation.domain.exceptions import InsufficientLeaveDaysError
from vacation.infrastructure.models import LeaveRequestModel, LeaveTypeModel


class SettingsWorkforceGateway(WorkforceGateway):
    """Temporary adapter; replace it when the employee bounded context is implemented."""

    def _employees(self) -> dict[str, dict[str, object]]:
        return settings.VACATION_DEVELOPMENT_EMPLOYEES

    def is_active_employee(self, employee_no: int) -> bool:
        employee = self._employees().get(str(employee_no), {})
        return bool(employee.get("active", False))

    def resolve_vacation_approver(self, employee_no: int) -> int | None:
        value = self._employees().get(str(employee_no), {}).get("approver_no")
        return int(value) if value is not None else None

    def is_hr_manager(self, employee_no: int) -> bool:
        return "HR_MANAGER" in self._employees().get(str(employee_no), {}).get("roles", [])


class SettingsLeaveBalanceGateway(LeaveBalanceGateway):
    """Temporary adapter; None means that the type has no balance restriction."""

    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        balances = self._employee_balances(employee_no)
        value = balances.get(type_id)
        if value is None:
            return None
        used = LeaveRequestModel.objects.filter(
            employee_no=employee_no, vacation_type_id=type_id,
            status=LeaveRequestModel.Status.APPROVED, balance_deducted=True,
        ).aggregate(days=Sum("use_days"))["days"] or Decimal("0")
        return Decimal(str(value)) - used

    def deduct(self, employee_no: int, type_id: str, days: Decimal) -> bool:
        # Settings are immutable demo allowances. Serialize approvals using a DB
        # row and derive usage from committed requests so rollback needs no cache undo.
        vacation_type = LeaveTypeModel.objects.select_for_update().get(type_id=type_id)
        if vacation_type.deduct_days == 0:
            return False
        remaining = self.remaining_days(employee_no, type_id)
        if remaining is None:
            return False
        if days > remaining:
            raise InsufficientLeaveDaysError(
                f"신청일수({days})가 잔여일수({remaining})를 초과합니다."
            )
        return True

    def restore(self, employee_no: int, type_id: str, days: Decimal) -> None:
        # Saving the recalled status removes this request from the usage aggregate.
        LeaveTypeModel.objects.select_for_update().get(type_id=type_id)

    def _employee_balances(self, employee_no: int) -> dict[str, object]:
        employee = settings.VACATION_DEVELOPMENT_EMPLOYEES.get(str(employee_no), {})
        value = employee.get("balances", {})
        return value if isinstance(value, dict) else {}
