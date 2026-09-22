from datetime import UTC, datetime

import pytest

from board.domain.entities import NoticeCategory, Post, PostType
from board.domain.exceptions import BoardPermissionError, InvalidPostContentError
from board.domain.value_objects import PostTitle

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def make_post(**overrides: object) -> Post:
    defaults: dict[str, object] = {
        "post_id": 1,
        "author_employee_no": 1001,
        "post_type": PostType.GENERAL,
        "notice_category": None,
        "title": "제목",
        "content": "내용",
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Post(**defaults)


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
