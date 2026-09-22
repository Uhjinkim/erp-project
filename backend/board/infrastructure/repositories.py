from board.domain.entities import Post
from board.domain.exceptions import PostNotFoundError
from board.domain.repositories import PostRepository
from board.infrastructure.mappers import model_to_entity
from board.infrastructure.models import PostModel


class DjangoPostRepository(PostRepository):
    def add(self, post: Post) -> Post:
        model = PostModel.objects.create(
            author_employee_no=post.author_employee_no,
            post_type=post.post_type.value,
            notice_category=post.notice_category.value if post.notice_category else None,
            title=post.title,
            content=post.content,
            created_at=post.created_at,
            updated_at=post.updated_at,
            deleted_at=post.deleted_at,
        )
        return model_to_entity(model)

    def get(self, post_id: int, *, for_update: bool = False) -> Post:
        query = PostModel.objects
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
            for model in PostModel.objects.filter(deleted_at__isnull=True)
        ]
