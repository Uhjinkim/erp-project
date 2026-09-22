from abc import ABC, abstractmethod

from board.domain.entities import Post


class PostRepository(ABC):
    @abstractmethod
    def add(self, post: Post) -> Post: ...

    @abstractmethod
    def get(self, post_id: int, *, for_update: bool = False) -> Post: ...

    @abstractmethod
    def save(self, post: Post) -> None: ...

    @abstractmethod
    def list_active(self) -> list[Post]: ...
