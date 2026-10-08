from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from board.domain.exceptions import BoardPermissionError, NestedReplyNotAllowedError
from board.domain.value_objects import CommentContent, PostContent, PostTitle


class PostType(StrEnum):
    GENERAL = "일반"
    NOTICE = "공지"


class NoticeCategory(StrEnum):
    MANAGEMENT = "MANAGEMENT"
    HR = "HR"
    PAYROLL = "PAYROLL"
    DEPARTMENT = "DEPARTMENT"


@dataclass
class Post:
    post_id: int | None
    writer_employee_no: int
    post_type: PostType
    notice_category: NoticeCategory | None
    title: str
    content: str
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    writer_name: str | None = None

    def __post_init__(self) -> None:
        PostTitle(self.title)
        PostContent(self.content)
        if self.post_type == PostType.NOTICE and self.notice_category is None:
            raise ValueError("공지는 업무 분류가 필요합니다.")
        if self.post_type == PostType.GENERAL and self.notice_category is not None:
            raise ValueError("일반 게시글은 업무 분류를 가질 수 없습니다.")

    def edit(self, actor_employee_no: int, actor_is_admin: bool, title: str, content: str) -> None:
        self._require_editor(actor_employee_no, actor_is_admin)
        PostTitle(title)
        PostContent(content)
        self.title = title
        self.content = content

    def soft_delete(
        self, actor_employee_no: int, actor_is_admin: bool, deleted_at: datetime
    ) -> None:
        self._require_editor(actor_employee_no, actor_is_admin)
        self.deleted_at = deleted_at

    def _require_editor(self, actor_employee_no: int, actor_is_admin: bool) -> None:
        if actor_is_admin:
            return
        if actor_employee_no != self.writer_employee_no:
            raise BoardPermissionError("작성자 본인 또는 시스템관리자만 처리할 수 있습니다.")


@dataclass
class Comment:
    comment_id: int | None
    post_id: int
    writer_employee_no: int
    parent_comment_id: int | None
    content: str
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    writer_name: str | None = None

    def __post_init__(self) -> None:
        CommentContent(self.content)

    def edit(self, actor_employee_no: int, actor_is_admin: bool, content: str) -> None:
        self._require_editor(actor_employee_no, actor_is_admin)
        CommentContent(content)
        self.content = content

    def soft_delete(
        self, actor_employee_no: int, actor_is_admin: bool, deleted_at: datetime
    ) -> None:
        self._require_editor(actor_employee_no, actor_is_admin)
        self.deleted_at = deleted_at

    def _require_editor(self, actor_employee_no: int, actor_is_admin: bool) -> None:
        if actor_is_admin:
            return
        if actor_employee_no != self.writer_employee_no:
            raise BoardPermissionError("작성자 본인 또는 시스템관리자만 처리할 수 있습니다.")


def ensure_reply_depth_allowed(parent: Comment | None) -> None:
    if parent is not None and parent.parent_comment_id is not None:
        raise NestedReplyNotAllowedError("답글에는 다시 답글을 달 수 없습니다.")
