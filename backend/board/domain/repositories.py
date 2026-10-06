from abc import ABC, abstractmethod

from board.domain.entities import Comment, Post


class PostRepository(ABC):
    @abstractmethod
    def add(self, post: Post) -> Post: ...

    @abstractmethod
    def get(self, post_id: int, *, for_update: bool = False) -> Post: ...

    @abstractmethod
    def save(self, post: Post) -> None: ...

    @abstractmethod
    def list_active(self) -> list[Post]: ...


class CommentRepository(ABC):
    @abstractmethod
    def add(self, comment: Comment) -> Comment: ...

    @abstractmethod
    def get(self, comment_id: int, *, for_update: bool = False) -> Comment: ...

    @abstractmethod
    def save(self, comment: Comment) -> None: ...

    @abstractmethod
    def list_for_post(self, post_id: int) -> list[Comment]: ...
