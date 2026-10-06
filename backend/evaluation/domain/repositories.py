from abc import ABC, abstractmethod

from evaluation.domain.entities import Evaluation


class EvaluationRepository(ABC):
    @abstractmethod
    def add(self, evaluation: Evaluation) -> Evaluation: ...

    @abstractmethod
    def get(self, eval_id: int) -> Evaluation: ...

    @abstractmethod
    def save_draft(self, evaluation: Evaluation) -> Evaluation:
        """Persist changes only while the stored row is still a draft."""

    @abstractmethod
    def exists_for(self, employee_no: int, eval_year: str) -> bool: ...

    @abstractmethod
    def list_all(self, eval_year: str | None = None) -> list[Evaluation]: ...

    @abstractmethod
    def list_visible_to(self, viewer_no: int, eval_year: str | None = None) -> list[Evaluation]:
        """Evaluations the viewer wrote plus their own confirmed evaluations."""
