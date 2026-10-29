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


@dataclass(frozen=True)
class Viewer:
    employee_no: int
    is_admin: bool
    is_moderator: bool


def _permissions(item: Post | Comment, viewer: Viewer) -> dict[str, bool]:
    return {
        "can_edit": item.can_be_edited_by(viewer.employee_no, viewer.is_admin),
        "can_delete": item.can_be_deleted_by(
            viewer.employee_no, viewer.is_admin, viewer.is_moderator
        ),
    }


def post_to_dict(post: Post, viewer: Viewer) -> dict[str, object]:
    return {
        **_permissions(post, viewer),
        "post_id": post.post_id,
        "writer_employee_no": post.writer_employee_no,
        "writer_name": post.writer_name,
        "post_type": post.post_type.value,
        "notice_category": post.notice_category.value if post.notice_category else None,
        "title": post.title,
        "content": post.content,
        "comment_count": post.comment_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


def comment_to_dict(comment: Comment, viewer: Viewer) -> dict[str, object]:
    return {
        **_permissions(comment, viewer),
        "comment_id": comment.comment_id,
        "post_id": comment.post_id,
        "writer_employee_no": comment.writer_employee_no,
        "writer_name": comment.writer_name,
        "parent_comment_id": comment.parent_comment_id,
        "content": comment.content,
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }
