from abc import ABC, abstractmethod

from board.domain.entities import NoticeCategory


class WorkforceGateway(ABC):
    @abstractmethod
    def is_active_employee(self, employee_no: int) -> bool: ...

    @abstractmethod
    def eligible_notice_categories(self, employee_no: int) -> set[NoticeCategory]: ...

    @abstractmethod
    def is_board_moderator(self, employee_no: int) -> bool:
        """True when the employee may soft-delete other people's posts and comments."""
