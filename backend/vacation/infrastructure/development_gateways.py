from decimal import Decimal

from django.conf import settings
from django.db.models import Sum

from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway
from vacation.domain.balance import balance_type_id
from vacation.domain.entities import VacationType
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

    def has_hr_managers(self) -> bool:
        return any(
            self.is_active_employee(int(number)) and self.is_hr_manager(int(number))
            for number in self._employees()
        )


class SettingsLeaveBalanceGateway(LeaveBalanceGateway):
    """Temporary adapter; None means that the type has no balance restriction."""

    def remaining_for_types(
        self, employee_no: int, types: list[VacationType]
    ) -> dict[str, Decimal | None]:
        configured = self._employee_balances(employee_no)
        restricted = {
            balance_type_id(item.type_id)
            for item in types
            if item.deduct_days != 0 and configured.get(balance_type_id(item.type_id)) is not None
        }
        usage_types = restricted | ({"HALF"} if "ANNUAL" in restricted else set())
        used = dict(LeaveRequestModel.objects.filter(
            employee_no=employee_no, vacation_type_id__in=usage_types,
            status=LeaveRequestModel.Status.APPROVED, balance_deducted=True,
        ).values("vacation_type_id").annotate(days=Sum("use_days"))
            .values_list("vacation_type_id", "days"))
        used_by_balance = {
            pool: sum(
                (days for type_id, days in used.items() if balance_type_id(type_id) == pool),
                Decimal("0"),
            )
            for pool in restricted
        }
        return {
            item.type_id: Decimal(str(configured[balance_type_id(item.type_id)]))
            - used_by_balance[balance_type_id(item.type_id)]
            if balance_type_id(item.type_id) in restricted else None
            for item in types
        }

    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        balances = self._employee_balances(employee_no)
        pool = balance_type_id(type_id)
        value = balances.get(pool)
        if value is None:
            return None
        usage_types = [pool, "HALF"] if pool == "ANNUAL" else [pool]
        used = LeaveRequestModel.objects.filter(
            employee_no=employee_no, vacation_type_id__in=usage_types,
            status=LeaveRequestModel.Status.APPROVED, balance_deducted=True,
        ).aggregate(days=Sum("use_days"))["days"] or Decimal("0")
        return Decimal(str(value)) - used

    def deduct(self, employee_no: int, type_id: str, days: Decimal) -> bool:
        # Settings are immutable demo allowances. Serialize approvals using a DB
        # row and derive usage from committed requests so rollback needs no cache undo.
        vacation_type = LeaveTypeModel.objects.get(type_id=type_id)
        if vacation_type.deduct_days == 0:
            return False
        LeaveTypeModel.objects.select_for_update().get(type_id=balance_type_id(type_id))
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
        LeaveTypeModel.objects.select_for_update().get(type_id=balance_type_id(type_id))

    def _employee_balances(self, employee_no: int) -> dict[str, object]:
        employee = settings.VACATION_DEVELOPMENT_EMPLOYEES.get(str(employee_no), {})
        value = employee.get("balances", {})
        return value if isinstance(value, dict) else {}
