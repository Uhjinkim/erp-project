from abc import ABC, abstractmethod
from datetime import date

from evaluation.domain.entities import EvaluationTarget


class WorkforceGateway(ABC):
    @abstractmethod
    def is_active_employee(self, employee_no: int) -> bool: ...

    @abstractmethod
    def is_hr_manager(self, employee_no: int) -> bool: ...

    @abstractmethod
    def evaluation_target(self, employee_no: int, as_of: date) -> EvaluationTarget | None:
        """Department and position the employee held on `as_of`."""
