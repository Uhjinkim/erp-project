from collections.abc import Callable
from datetime import datetime

from board.application.dto import CreatePostCommand, UpdatePostCommand
from board.application.ports import WorkforceGateway
from board.domain.entities import Post, PostType
from board.domain.exceptions import (
    InactiveEmployeeError,
    InvalidPostContentError,
    NoticeCategoryNotAllowedError,
    PostNotFoundError,
)
from board.domain.repositories import PostRepository


class BoardService:
    def __init__(
        self,
        repository: PostRepository,
        workforce: WorkforceGateway,
        clock: Callable[[], datetime],
    ) -> None:
        self.repository = repository
        self.workforce = workforce
        self.clock = clock

    def create_post(self, command: CreatePostCommand) -> Post:
        self._ensure_active(command.author_employee_no)
        notice_category = command.notice_category
        if command.post_type == PostType.NOTICE:
            eligible = self.workforce.eligible_notice_categories(command.author_employee_no)
            if notice_category is None or notice_category not in eligible:
                raise NoticeCategoryNotAllowedError(
                    "해당 업무 분류의 공지를 작성할 권한이 없습니다."
                )
        elif notice_category is not None:
            raise InvalidPostContentError("일반 게시글은 업무 분류를 가질 수 없습니다.")

        now = self.clock()
        post = Post(
            post_id=None,
            author_employee_no=command.author_employee_no,
            post_type=command.post_type,
            notice_category=notice_category,
            title=command.title,
            content=command.content,
            created_at=now,
            updated_at=now,
        )
        return self.repository.add(post)

    def update_post(self, command: UpdatePostCommand) -> Post:
        post = self._get_visible(command.post_id)
        post.edit(command.actor_employee_no, command.actor_is_admin, command.title, command.content)
        post.updated_at = self.clock()
        self.repository.save(post)
        return post

    def delete_post(self, post_id: int, actor_employee_no: int, actor_is_admin: bool) -> None:
        post = self._get_visible(post_id)
        post.soft_delete(actor_employee_no, actor_is_admin, self.clock())
        self.repository.save(post)

    def list_posts(self, viewer_employee_no: int) -> list[Post]:
        self._ensure_active(viewer_employee_no)
        return self.repository.list_active()

    def get_post(self, post_id: int, viewer_employee_no: int) -> Post:
        self._ensure_active(viewer_employee_no)
        return self._get_visible(post_id)

    def _get_visible(self, post_id: int) -> Post:
        post = self.repository.get(post_id)
        if post.deleted_at is not None:
            raise PostNotFoundError("게시글을 찾을 수 없습니다.")
        return post

    def _ensure_active(self, employee_no: int) -> None:
        if not self.workforce.is_active_employee(employee_no):
            raise InactiveEmployeeError("재직 중인 사원만 게시판을 사용할 수 있습니다.")
