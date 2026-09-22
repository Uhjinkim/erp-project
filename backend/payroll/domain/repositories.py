from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager

from payroll.domain.entities import PayrollComponentType, PayrollHistory, PayrollStatement
from payroll.domain.value_objects import PayPeriod


class PayrollStatementRepository(ABC):
    @abstractmethod
    def add(self, statement: PayrollStatement) -> PayrollStatement: ...

    @abstractmethod
    def get(self, statement_id: int, *, for_update: bool = False) -> PayrollStatement: ...

    @abstractmethod
    def save(self, statement: PayrollStatement) -> None: ...

    @abstractmethod
    def find_by_employee_and_period(
        self, employee_no: int, period: PayPeriod
    ) -> PayrollStatement | None: ...

    @abstractmethod
    def list_for_employee(self, employee_no: int) -> list[PayrollStatement]: ...

    @abstractmethod
    def list_all(self) -> list[PayrollStatement]: ...


class PayrollHistoryRepository(ABC):
    @abstractmethod
    def add(self, history: PayrollHistory) -> None: ...

    @abstractmethod
    def list_for_statement(self, statement_id: int) -> list[PayrollHistory]: ...


class PayrollComponentRepository(ABC):
    @abstractmethod
    def get(self, code: str) -> PayrollComponentType: ...

    @abstractmethod
    def list_active(self) -> list[PayrollComponentType]: ...


class PayrollUnitOfWork(AbstractContextManager["PayrollUnitOfWork"], ABC):
    statements: PayrollStatementRepository
    histories: PayrollHistoryRepository
    components: PayrollComponentRepository

    @abstractmethod
    def __enter__(self) -> "PayrollUnitOfWork": ...

    @abstractmethod
    def __exit__(self, *args: object) -> bool | None: ...

    def __iter__(self) -> Iterator[object]:
        return iter(())
