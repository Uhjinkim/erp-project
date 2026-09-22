from datetime import UTC, datetime

import pytest

from board.application.dto import CreatePostCommand, UpdatePostCommand
from board.application.ports import WorkforceGateway
from board.application.service import BoardService
from board.domain.entities import NoticeCategory, Post, PostType
from board.domain.exceptions import (
    BoardPermissionError,
    InactiveEmployeeError,
    InvalidPostContentError,
    NoticeCategoryNotAllowedError,
    PostNotFoundError,
)
from board.domain.repositories import PostRepository

NOW = datetime(2026, 9, 22, tzinfo=UTC)


class FakePosts(PostRepository):
    def __init__(self) -> None:
        self.items: dict[int, Post] = {}

    def add(self, post: Post) -> Post:
        post.post_id = len(self.items) + 1
        self.items[post.post_id] = post
        return post

    def get(self, post_id: int, *, for_update: bool = False) -> Post:
        try:
            return self.items[post_id]
        except KeyError as exc:
            raise PostNotFoundError("게시글을 찾을 수 없습니다.") from exc

    def save(self, post: Post) -> None:
        assert post.post_id is not None
        self.items[post.post_id] = post

    def list_active(self) -> list[Post]:
        return [item for item in self.items.values() if item.deleted_at is None]


class FakeWorkforce(WorkforceGateway):
    def __init__(
        self,
        active_employees: set[int],
        eligible: dict[int, set[NoticeCategory]] | None = None,
    ) -> None:
        self.active_employees = active_employees
        self.eligible = eligible or {}

    def is_active_employee(self, employee_no: int) -> bool:
        return employee_no in self.active_employees

    def eligible_notice_categories(self, employee_no: int) -> set[NoticeCategory]:
        return self.eligible.get(employee_no, set())


def make_service(
    active_employees: set[int],
    eligible: dict[int, set[NoticeCategory]] | None = None,
) -> BoardService:
    return BoardService(
        repository=FakePosts(),
        workforce=FakeWorkforce(active_employees, eligible),
        clock=lambda: NOW,
    )


def test_active_employee_can_write_general_post() -> None:
    service = make_service({1001})
    post = service.create_post(
        CreatePostCommand(
            author_employee_no=1001, post_type=PostType.GENERAL, title="공지", content="내용"
        )
    )
    assert post.post_type == PostType.GENERAL
    assert post.notice_category is None


def test_inactive_employee_cannot_write_post() -> None:
    service = make_service(set())
    with pytest.raises(InactiveEmployeeError):
        service.create_post(
            CreatePostCommand(
                author_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
            )
        )


def test_employee_without_notice_role_cannot_write_notice() -> None:
    service = make_service({1001}, {1001: set()})
    with pytest.raises(NoticeCategoryNotAllowedError):
        service.create_post(
            CreatePostCommand(
                author_employee_no=1001,
                post_type=PostType.NOTICE,
                title="제목",
                content="내용",
                notice_category=NoticeCategory.HR,
            )
        )


def test_payroll_manager_can_write_payroll_notice() -> None:
    service = make_service({1001}, {1001: {NoticeCategory.PAYROLL}})
    post = service.create_post(
        CreatePostCommand(
            author_employee_no=1001,
            post_type=PostType.NOTICE,
            title="급여 안내",
            content="내용",
            notice_category=NoticeCategory.PAYROLL,
        )
    )
    assert post.notice_category == NoticeCategory.PAYROLL


def test_cannot_write_notice_with_unauthorized_category() -> None:
    service = make_service({1001}, {1001: {NoticeCategory.PAYROLL}})
    with pytest.raises(NoticeCategoryNotAllowedError):
        service.create_post(
            CreatePostCommand(
                author_employee_no=1001,
                post_type=PostType.NOTICE,
                title="경영 공지",
                content="내용",
                notice_category=NoticeCategory.MANAGEMENT,
            )
        )


def test_general_post_rejects_notice_category() -> None:
    service = make_service({1001})
    with pytest.raises(InvalidPostContentError):
        service.create_post(
            CreatePostCommand(
                author_employee_no=1001,
                post_type=PostType.GENERAL,
                title="제목",
                content="내용",
                notice_category=NoticeCategory.HR,
            )
        )


def test_author_can_update_own_post() -> None:
    service = make_service({1001})
    post = service.create_post(
        CreatePostCommand(
            author_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    updated = service.update_post(
        UpdatePostCommand(
            post_id=post.post_id, actor_employee_no=1001, actor_is_admin=False,
            title="수정 제목", content="수정 내용",
        )
    )
    assert updated.title == "수정 제목"


def test_other_employee_cannot_delete_post() -> None:
    service = make_service({1001, 2002})
    post = service.create_post(
        CreatePostCommand(
            author_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    with pytest.raises(BoardPermissionError):
        service.delete_post(post.post_id, 2002, False)


def test_admin_can_delete_others_post_and_it_disappears_from_list() -> None:
    service = make_service({1001})
    post = service.create_post(
        CreatePostCommand(
            author_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    service.delete_post(post.post_id, 9999, True)
    assert service.list_posts(1001) == []
    with pytest.raises(PostNotFoundError):
        service.get_post(post.post_id, 1001)
