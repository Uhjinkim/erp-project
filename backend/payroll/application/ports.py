from abc import ABC, abstractmethod
from datetime import date


class WorkforceGateway(ABC):
    @abstractmethod
    def employee_exists(self, employee_no: int) -> bool: ...

    @abstractmethod
    def is_payroll_manager(self, employee_no: int) -> bool: ...


class HolidayGateway(ABC):
    @abstractmethod
    def holidays_in(self, year: int, month: int) -> frozenset[date]: ...
