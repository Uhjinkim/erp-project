from datetime import UTC, datetime

import pytest

from board.domain.entities import (
    Comment,
    NoticeCategory,
    Post,
    PostType,
    ensure_reply_depth_allowed,
)
from board.domain.exceptions import (
    BoardPermissionError,
    InvalidCommentContentError,
    InvalidPostContentError,
    NestedReplyNotAllowedError,
)
from board.domain.value_objects import CommentContent, PostTitle

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def make_post(**overrides: object) -> Post:
    defaults: dict[str, object] = {
        "post_id": 1,
        "writer_employee_no": 1001,
        "post_type": PostType.GENERAL,
        "notice_category": None,
        "title": "제목",
        "content": "내용",
        "created_at": NOW,
        "updated_at": None,
    }
    defaults.update(overrides)
    return Post(**defaults)


def make_comment(**overrides: object) -> Comment:
    defaults: dict[str, object] = {
        "comment_id": 1,
        "post_id": 1,
        "writer_employee_no": 1001,
        "parent_comment_id": None,
        "content": "댓글 내용",
        "created_at": NOW,
    }
    defaults.update(overrides)
    return Comment(**defaults)


def test_title_over_100_chars_is_rejected() -> None:
    with pytest.raises(InvalidPostContentError):
        PostTitle("가" * 101)


def test_blank_title_is_rejected() -> None:
    with pytest.raises(InvalidPostContentError):
        PostTitle("   ")


def test_notice_requires_category() -> None:
    with pytest.raises(ValueError):
        make_post(post_type=PostType.NOTICE, notice_category=None)


def test_general_post_cannot_have_category() -> None:
    with pytest.raises(ValueError):
        make_post(post_type=PostType.GENERAL, notice_category=NoticeCategory.HR)


def test_author_can_edit_own_post() -> None:
    post = make_post()
    post.edit(1001, False, "새 제목", "새 내용")
    assert post.title == "새 제목"
    assert post.content == "새 내용"


def test_other_employee_cannot_edit_post() -> None:
    post = make_post()
    with pytest.raises(BoardPermissionError):
        post.edit(9999, False, "새 제목", "새 내용")


def test_admin_can_edit_others_post() -> None:
    post = make_post()
    post.edit(9999, True, "새 제목", "새 내용")
    assert post.title == "새 제목"


def test_author_can_soft_delete_own_post() -> None:
    post = make_post()
    post.soft_delete(1001, False, NOW)
    assert post.deleted_at == NOW


def test_other_employee_cannot_delete_post() -> None:
    post = make_post()
    with pytest.raises(BoardPermissionError):
        post.soft_delete(9999, False, NOW)


def test_admin_can_delete_others_post() -> None:
    post = make_post()
    post.soft_delete(9999, True, NOW)
    assert post.deleted_at == NOW


def test_comment_over_1000_chars_is_rejected() -> None:
    with pytest.raises(InvalidCommentContentError):
        CommentContent("가" * 1001)


def test_blank_comment_is_rejected() -> None:
    with pytest.raises(InvalidCommentContentError):
        CommentContent("   ")


def test_author_can_edit_own_comment() -> None:
    comment = make_comment()
    comment.edit(1001, False, "수정된 댓글")
    assert comment.content == "수정된 댓글"


def test_other_employee_cannot_edit_comment() -> None:
    comment = make_comment()
    with pytest.raises(BoardPermissionError):
        comment.edit(9999, False, "수정된 댓글")


def test_other_employee_cannot_delete_comment() -> None:
    comment = make_comment()
    with pytest.raises(BoardPermissionError):
        comment.soft_delete(9999, False, NOW)


def test_reply_to_top_level_comment_is_allowed() -> None:
    top_level = make_comment(parent_comment_id=None)
    ensure_reply_depth_allowed(top_level)


def test_reply_to_a_reply_is_rejected() -> None:
    reply = make_comment(comment_id=2, parent_comment_id=1)
    with pytest.raises(NestedReplyNotAllowedError):
        ensure_reply_depth_allowed(reply)
