from abc import ABC, abstractmethod
from decimal import Decimal

from vacation.domain.entities import VacationType


class WorkforceGateway(ABC):
    @abstractmethod
    def is_active_employee(self, employee_no: int) -> bool: ...

    @abstractmethod
    def resolve_vacation_approver(self, employee_no: int) -> int | None: ...

    @abstractmethod
    def is_hr_manager(self, employee_no: int) -> bool: ...

    @abstractmethod
    def has_hr_managers(self) -> bool: ...


class LeaveBalanceGateway(ABC):
    @abstractmethod
    def remaining_for_types(
        self, employee_no: int, types: list[VacationType]
    ) -> dict[str, Decimal | None]:
        """Read all requested balances in bulk without reserving days."""

    @abstractmethod
    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        """Return None when this leave type does not require a balance check."""

    @abstractmethod
    def deduct(self, employee_no: int, type_id: str, days: Decimal) -> bool:
        """Atomically check and deduct days within the caller's unit of work.

        Return whether a balance was charged; raise InsufficientLeaveDaysError on shortage.
        """

    @abstractmethod
    def restore(self, employee_no: int, type_id: str, days: Decimal) -> None:
        """Restore a previously charged balance within the caller's unit of work."""
