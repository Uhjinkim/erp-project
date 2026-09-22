from dataclasses import dataclass

from board.domain.entities import NoticeCategory, Post, PostType


@dataclass(frozen=True)
class CreatePostCommand:
    author_employee_no: int
    post_type: PostType
    title: str
    content: str
    notice_category: NoticeCategory | None = None


@dataclass(frozen=True)
class UpdatePostCommand:
    post_id: int
    actor_employee_no: int
    actor_is_admin: bool
    title: str
    content: str


def post_to_dict(post: Post) -> dict[str, object]:
    return {
        "post_id": post.post_id,
        "author_employee_no": post.author_employee_no,
        "post_type": post.post_type.value,
        "notice_category": post.notice_category.value if post.notice_category else None,
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }
