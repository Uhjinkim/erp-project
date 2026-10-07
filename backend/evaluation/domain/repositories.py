from abc import ABC, abstractmethod
from contextlib import AbstractContextManager

from evaluation.domain.entities import Evaluation, EvaluationHistory


class EvaluationRepository(ABC):
    @abstractmethod
    def add(self, evaluation: Evaluation) -> Evaluation:
        """Raise DuplicateEvaluationError when the employee already has one for the year."""

    @abstractmethod
    def get(self, eval_id: int) -> Evaluation: ...

    @abstractmethod
    def save(self, evaluation: Evaluation, expected: Evaluation) -> Evaluation:
        """Persist only if the stored row still matches `expected`.

        Raise EvaluationConflictError when someone else changed the evaluation first.
        """

    @abstractmethod
    def exists_for(self, employee_no: int, eval_year: str) -> bool: ...

    @abstractmethod
    def list_all(self, eval_year: str | None = None) -> list[Evaluation]: ...

    @abstractmethod
    def list_visible_to(self, viewer_no: int, eval_year: str | None = None) -> list[Evaluation]:
        """Evaluations the viewer currently evaluates plus their own confirmed evaluations."""


class EvaluationHistoryRepository(ABC):
    @abstractmethod
    def add(self, entry: EvaluationHistory) -> EvaluationHistory: ...

    @abstractmethod
    def list_for(self, eval_id: int) -> list[EvaluationHistory]:
        """Entries in chronological order."""


class EvaluationUnitOfWork(AbstractContextManager["EvaluationUnitOfWork"], ABC):
    evaluations: EvaluationRepository
    histories: EvaluationHistoryRepository

    @abstractmethod
    def __enter__(self) -> "EvaluationUnitOfWork": ...

    @abstractmethod
    def __exit__(self, *args: object) -> bool | None: ...
