from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmployeeDisplay:
    employee_no: int
    name: str
    position_name: str | None


@dataclass(frozen=True)
class PayrollTargetEmployee:
    """Minimal employee data a payroll manager needs to pick whom to pay (no contact details)."""

    employee_no: int
    name: str
    dept_no: int | None
    dept_name: str | None
    position_name: str | None
    is_active: bool


class WorkforceGateway(ABC):
    @abstractmethod
    def employee_exists(self, employee_no: int) -> bool: ...

    @abstractmethod
    def is_payroll_manager(self, employee_no: int) -> bool: ...

    @abstractmethod
    def employee_displays(self, employee_nos: set[int]) -> dict[int, EmployeeDisplay]: ...

    @abstractmethod
    def list_payroll_targets(self) -> list[PayrollTargetEmployee]: ...


class HolidayGateway(ABC):
    @abstractmethod
    def holidays_in(self, year: int, month: int) -> frozenset[date]: ...
