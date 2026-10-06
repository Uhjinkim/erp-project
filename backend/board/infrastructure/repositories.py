from board.domain.entities import Comment, Post
from board.domain.exceptions import CommentNotFoundError, PostNotFoundError
from board.domain.repositories import CommentRepository, PostRepository
from board.infrastructure.mappers import comment_model_to_entity, model_to_entity
from board.infrastructure.models import CommentModel, PostModel


class DjangoPostRepository(PostRepository):
    def add(self, post: Post) -> Post:
        model = PostModel.objects.create(
            writer_id=post.writer_employee_no,
            post_type=post.post_type.value,
            notice_category_id=post.notice_category.value if post.notice_category else None,
            title=post.title,
            content=post.content,
            created_at=post.created_at,
            updated_at=post.updated_at,
            deleted_at=post.deleted_at,
        )
        return model_to_entity(self._select_related().get(post_id=model.post_id))

    def get(self, post_id: int, *, for_update: bool = False) -> Post:
        query = self._select_related()
        if for_update:
            query = query.select_for_update()
        try:
            return model_to_entity(query.get(post_id=post_id))
        except PostModel.DoesNotExist as exc:
            raise PostNotFoundError("게시글을 찾을 수 없습니다.") from exc

    def save(self, post: Post) -> None:
        updated = PostModel.objects.filter(post_id=post.post_id).update(
            title=post.title,
            content=post.content,
            updated_at=post.updated_at,
            deleted_at=post.deleted_at,
        )
        if not updated:
            raise PostNotFoundError("게시글을 찾을 수 없습니다.")

    def list_active(self) -> list[Post]:
        return [
            model_to_entity(model)
            for model in self._select_related().filter(deleted_at__isnull=True)
        ]

    def _select_related(self):
        return PostModel.objects.select_related("writer__person")


class DjangoCommentRepository(CommentRepository):
    def add(self, comment: Comment) -> Comment:
        model = CommentModel.objects.create(
            post_id=comment.post_id,
            writer_id=comment.writer_employee_no,
            parent_id=comment.parent_comment_id,
            content=comment.content,
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            deleted_at=comment.deleted_at,
        )
        return comment_model_to_entity(self._select_related().get(comment_id=model.comment_id))

    def get(self, comment_id: int, *, for_update: bool = False) -> Comment:
        query = self._select_related()
        if for_update:
            query = query.select_for_update()
        try:
            return comment_model_to_entity(query.get(comment_id=comment_id))
        except CommentModel.DoesNotExist as exc:
            raise CommentNotFoundError("댓글을 찾을 수 없습니다.") from exc

    def save(self, comment: Comment) -> None:
        updated = CommentModel.objects.filter(comment_id=comment.comment_id).update(
            content=comment.content,
            updated_at=comment.updated_at,
            deleted_at=comment.deleted_at,
        )
        if not updated:
            raise CommentNotFoundError("댓글을 찾을 수 없습니다.")

    def list_for_post(self, post_id: int) -> list[Comment]:
        return [
            comment_model_to_entity(model)
            for model in self._select_related().filter(post_id=post_id, deleted_at__isnull=True)
        ]

    def _select_related(self):
        return CommentModel.objects.select_related("writer__person")
