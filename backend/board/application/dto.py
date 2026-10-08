from dataclasses import dataclass

from board.domain.entities import Comment, NoticeCategory, Post, PostType


@dataclass(frozen=True)
class CreatePostCommand:
    writer_employee_no: int
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


@dataclass(frozen=True)
class CreateCommentCommand:
    post_id: int
    writer_employee_no: int
    content: str
    parent_comment_id: int | None = None


@dataclass(frozen=True)
class UpdateCommentCommand:
    comment_id: int
    actor_employee_no: int
    actor_is_admin: bool
    content: str


def post_to_dict(post: Post) -> dict[str, object]:
    return {
        "post_id": post.post_id,
        "writer_employee_no": post.writer_employee_no,
        "writer_name": post.writer_name,
        "post_type": post.post_type.value,
        "notice_category": post.notice_category.value if post.notice_category else None,
        "title": post.title,
        "content": post.content,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


def comment_to_dict(comment: Comment) -> dict[str, object]:
    return {
        "comment_id": comment.comment_id,
        "post_id": comment.post_id,
        "writer_employee_no": comment.writer_employee_no,
        "writer_name": comment.writer_name,
        "parent_comment_id": comment.parent_comment_id,
        "content": comment.content,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }
