from abc import ABC, abstractmethod
from decimal import Decimal


class WorkforceGateway(ABC):
    @abstractmethod
    def is_active_employee(self, employee_no: int) -> bool: ...

    @abstractmethod
    def resolve_vacation_approver(self, employee_no: int) -> int | None: ...

    @abstractmethod
    def is_hr_manager(self, employee_no: int) -> bool: ...


class LeaveBalanceGateway(ABC):
    @abstractmethod
    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        """Return None when this leave type does not require a balance check."""
