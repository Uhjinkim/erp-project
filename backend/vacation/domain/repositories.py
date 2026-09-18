from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager

from vacation.domain.entities import VacationHistory, VacationRequest, VacationType


class VacationRequestRepository(ABC):
    @abstractmethod
    def add(self, request: VacationRequest) -> VacationRequest: ...

    @abstractmethod
    def get(self, request_id: int, *, for_update: bool = False) -> VacationRequest: ...

    @abstractmethod
    def save(self, request: VacationRequest) -> None: ...

    @abstractmethod
    def list_for_employee(self, employee_no: int) -> list[VacationRequest]: ...

    @abstractmethod
    def list_for_approver(self, employee_no: int) -> list[VacationRequest]: ...


class VacationHistoryRepository(ABC):
    @abstractmethod
    def add(self, history: VacationHistory) -> None: ...

    @abstractmethod
    def list_for_request(self, request_id: int) -> list[VacationHistory]: ...


class VacationTypeRepository(ABC):
    @abstractmethod
    def get(self, type_id: str) -> VacationType: ...

    @abstractmethod
    def list_active(self) -> list[VacationType]: ...


class VacationUnitOfWork(AbstractContextManager["VacationUnitOfWork"], ABC):
    requests: VacationRequestRepository
    histories: VacationHistoryRepository
    types: VacationTypeRepository

    @abstractmethod
    def __enter__(self) -> "VacationUnitOfWork": ...

    @abstractmethod
    def __exit__(self, *args: object) -> bool | None: ...

    def __iter__(self) -> Iterator[object]:
        return iter(())
