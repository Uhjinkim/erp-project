from decimal import Decimal

from django.conf import settings

from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway


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
        return Decimal(str(value)) if value is not None else None

    def _employee_balances(self, employee_no: int) -> dict[str, object]:
        employee = settings.VACATION_DEVELOPMENT_EMPLOYEES.get(str(employee_no), {})
        value = employee.get("balances", {})
        return value if isinstance(value, dict) else {}
