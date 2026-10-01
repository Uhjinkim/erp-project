from datetime import UTC, datetime

import pytest

from board.application.comment_service import CommentService
from board.application.dto import (
    CreateCommentCommand,
    CreatePostCommand,
    UpdateCommentCommand,
    UpdatePostCommand,
)
from board.application.ports import WorkforceGateway
from board.application.service import BoardService
from board.domain.entities import Comment, NoticeCategory, Post, PostType
from board.domain.exceptions import (
    BoardPermissionError,
    CommentNotFoundError,
    InactiveEmployeeError,
    InvalidPostContentError,
    NestedReplyNotAllowedError,
    NoticeCategoryNotAllowedError,
    PostNotFoundError,
)
from board.domain.repositories import CommentRepository, PostRepository

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


class FakeComments(CommentRepository):
    def __init__(self) -> None:
        self.items: dict[int, Comment] = {}

    def add(self, comment: Comment) -> Comment:
        comment.comment_id = len(self.items) + 1
        self.items[comment.comment_id] = comment
        return comment

    def get(self, comment_id: int, *, for_update: bool = False) -> Comment:
        try:
            return self.items[comment_id]
        except KeyError as exc:
            raise CommentNotFoundError("댓글을 찾을 수 없습니다.") from exc

    def save(self, comment: Comment) -> None:
        assert comment.comment_id is not None
        self.items[comment.comment_id] = comment

    def list_for_post(self, post_id: int) -> list[Comment]:
        return [
            item for item in self.items.values()
            if item.post_id == post_id and item.deleted_at is None
        ]


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


def make_comment_service(
    active_employees: set[int], posts: PostRepository
) -> CommentService:
    return CommentService(
        comments=FakeComments(),
        posts=posts,
        workforce=FakeWorkforce(active_employees),
        clock=lambda: NOW,
    )


def test_active_employee_can_write_general_post() -> None:
    service = make_service({1001})
    post = service.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="공지", content="내용"
        )
    )
    assert post.post_type == PostType.GENERAL
    assert post.notice_category is None


def test_inactive_employee_cannot_write_post() -> None:
    service = make_service(set())
    with pytest.raises(InactiveEmployeeError):
        service.create_post(
            CreatePostCommand(
                writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
            )
        )


def test_employee_without_notice_role_cannot_write_notice() -> None:
    service = make_service({1001}, {1001: set()})
    with pytest.raises(NoticeCategoryNotAllowedError):
        service.create_post(
            CreatePostCommand(
                writer_employee_no=1001,
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
            writer_employee_no=1001,
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
                writer_employee_no=1001,
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
                writer_employee_no=1001,
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
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
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
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    with pytest.raises(BoardPermissionError):
        service.delete_post(post.post_id, 2002, False)


def test_admin_can_delete_others_post_and_it_disappears_from_list() -> None:
    service = make_service({1001})
    post = service.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    service.delete_post(post.post_id, 9999, True)
    assert service.list_posts(1001) == []
    with pytest.raises(PostNotFoundError):
        service.get_post(post.post_id, 1001)


def test_active_employee_can_comment_on_post() -> None:
    posts = FakePosts()
    board = BoardService(repository=posts, workforce=FakeWorkforce({1001}), clock=lambda: NOW)
    post = board.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    comments = make_comment_service({1001, 2002}, posts)
    comment = comments.create_comment(
        CreateCommentCommand(post_id=post.post_id, writer_employee_no=2002, content="댓글입니다")
    )
    assert comment.content == "댓글입니다"
    assert comment.parent_comment_id is None


def test_reply_to_comment_is_allowed() -> None:
    posts = FakePosts()
    board = BoardService(repository=posts, workforce=FakeWorkforce({1001}), clock=lambda: NOW)
    post = board.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    comments = make_comment_service({1001, 2002}, posts)
    top_level = comments.create_comment(
        CreateCommentCommand(post_id=post.post_id, writer_employee_no=1001, content="댓글")
    )
    reply = comments.create_comment(
        CreateCommentCommand(
            post_id=post.post_id,
            writer_employee_no=2002,
            content="답글",
            parent_comment_id=top_level.comment_id,
        )
    )
    assert reply.parent_comment_id == top_level.comment_id


def test_reply_to_a_reply_is_rejected_by_service() -> None:
    posts = FakePosts()
    board = BoardService(repository=posts, workforce=FakeWorkforce({1001}), clock=lambda: NOW)
    post = board.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    comments = make_comment_service({1001}, posts)
    top_level = comments.create_comment(
        CreateCommentCommand(post_id=post.post_id, writer_employee_no=1001, content="댓글")
    )
    reply = comments.create_comment(
        CreateCommentCommand(
            post_id=post.post_id,
            writer_employee_no=1001,
            content="답글",
            parent_comment_id=top_level.comment_id,
        )
    )
    with pytest.raises(NestedReplyNotAllowedError):
        comments.create_comment(
            CreateCommentCommand(
                post_id=post.post_id,
                writer_employee_no=1001,
                content="답글의 답글",
                parent_comment_id=reply.comment_id,
            )
        )


def test_commenting_on_missing_post_is_rejected() -> None:
    comments = make_comment_service({1001}, FakePosts())
    with pytest.raises(PostNotFoundError):
        comments.create_comment(
            CreateCommentCommand(post_id=999, writer_employee_no=1001, content="댓글")
        )


def test_other_employee_cannot_edit_or_delete_comment() -> None:
    posts = FakePosts()
    board = BoardService(repository=posts, workforce=FakeWorkforce({1001}), clock=lambda: NOW)
    post = board.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    comments = make_comment_service({1001, 2002}, posts)
    comment = comments.create_comment(
        CreateCommentCommand(post_id=post.post_id, writer_employee_no=1001, content="댓글")
    )
    with pytest.raises(BoardPermissionError):
        comments.update_comment(
            UpdateCommentCommand(
                comment_id=comment.comment_id,
                actor_employee_no=2002,
                actor_is_admin=False,
                content="수정 시도",
            )
        )
    with pytest.raises(BoardPermissionError):
        comments.delete_comment(comment.comment_id, 2002, False)


def test_deleted_comment_disappears_from_list() -> None:
    posts = FakePosts()
    board = BoardService(repository=posts, workforce=FakeWorkforce({1001}), clock=lambda: NOW)
    post = board.create_post(
        CreatePostCommand(
            writer_employee_no=1001, post_type=PostType.GENERAL, title="제목", content="내용"
        )
    )
    comments = make_comment_service({1001}, posts)
    comment = comments.create_comment(
        CreateCommentCommand(post_id=post.post_id, writer_employee_no=1001, content="댓글")
    )
    comments.delete_comment(comment.comment_id, 1001, False)
    assert comments.list_comments(post.post_id, 1001) == []
