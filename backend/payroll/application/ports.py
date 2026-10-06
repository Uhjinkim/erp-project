from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmployeeDisplay:
    employee_no: int
    name: str
    position_name: str | None


class WorkforceGateway(ABC):
    @abstractmethod
    def employee_exists(self, employee_no: int) -> bool: ...

    @abstractmethod
    def is_payroll_manager(self, employee_no: int) -> bool: ...

    @abstractmethod
    def employee_displays(self, employee_nos: set[int]) -> dict[int, EmployeeDisplay]: ...


class HolidayGateway(ABC):
    @abstractmethod
    def holidays_in(self, year: int, month: int) -> frozenset[date]: ...
