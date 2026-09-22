from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from board.domain.exceptions import BoardPermissionError
from board.domain.value_objects import PostContent, PostTitle


class PostType(StrEnum):
    GENERAL = "일반"
    NOTICE = "공지"


class NoticeCategory(StrEnum):
    MANAGEMENT = "경영"
    HR = "인사"
    PAYROLL = "급여"
    DEPARTMENT = "부서"


@dataclass
class Post:
    post_id: int | None
    author_employee_no: int
    post_type: PostType
    notice_category: NoticeCategory | None
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

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
        if actor_employee_no != self.author_employee_no:
            raise BoardPermissionError("작성자 본인 또는 시스템관리자만 처리할 수 있습니다.")
