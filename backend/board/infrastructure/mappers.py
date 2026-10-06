from board.domain.entities import Comment, NoticeCategory, Post, PostType
from board.infrastructure.models import CommentModel, PostModel


def model_to_entity(model: PostModel) -> Post:
    return Post(
        post_id=model.post_id,
        writer_employee_no=model.writer_id,
        post_type=PostType(model.post_type),
        notice_category=NoticeCategory(model.notice_category_id)
        if model.notice_category_id
        else None,
        title=model.title,
        content=model.content,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        writer_name=model.writer.person.name,
    )


def comment_model_to_entity(model: CommentModel) -> Comment:
    return Comment(
        comment_id=model.comment_id,
        post_id=model.post_id,
        writer_employee_no=model.writer_id,
        parent_comment_id=model.parent_id,
        content=model.content,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
        writer_name=model.writer.person.name,
    )
