from board.domain.entities import NoticeCategory, Post, PostType
from board.infrastructure.models import PostModel


def model_to_entity(model: PostModel) -> Post:
    return Post(
        post_id=model.post_id,
        author_employee_no=model.author_employee_no,
        post_type=PostType(model.post_type),
        notice_category=NoticeCategory(model.notice_category) if model.notice_category else None,
        title=model.title,
        content=model.content,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )
