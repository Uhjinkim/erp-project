from collections.abc import Callable
from datetime import datetime

from board.application.dto import CreateCommentCommand, UpdateCommentCommand
from board.application.ports import WorkforceGateway
from board.domain.entities import Comment, ensure_reply_depth_allowed
from board.domain.exceptions import (
    CommentNotFoundError,
    InactiveEmployeeError,
    PostNotFoundError,
)
from board.domain.repositories import CommentRepository, PostRepository


class CommentService:
    def __init__(
        self,
        comments: CommentRepository,
        posts: PostRepository,
        workforce: WorkforceGateway,
        clock: Callable[[], datetime],
    ) -> None:
        self.comments = comments
        self.posts = posts
        self.workforce = workforce
        self.clock = clock

    def create_comment(self, command: CreateCommentCommand) -> Comment:
        self._ensure_active(command.writer_employee_no)
        self._ensure_post_visible(command.post_id)

        parent = None
        if command.parent_comment_id is not None:
            parent = self._get_visible(command.parent_comment_id)
            if parent.post_id != command.post_id:
                raise CommentNotFoundError("해당 게시글의 댓글이 아닙니다.")
            ensure_reply_depth_allowed(parent)

        comment = Comment(
            comment_id=None,
            post_id=command.post_id,
            writer_employee_no=command.writer_employee_no,
            parent_comment_id=command.parent_comment_id,
            content=command.content,
            created_at=self.clock(),
        )
        return self.comments.add(comment)

    def update_comment(self, command: UpdateCommentCommand) -> Comment:
        comment = self._get_visible(command.comment_id)
        comment.edit(command.actor_employee_no, command.actor_is_admin, command.content)
        comment.updated_at = self.clock()
        self.comments.save(comment)
        return comment

    def delete_comment(self, comment_id: int, actor_employee_no: int, actor_is_admin: bool) -> None:
        comment = self._get_visible(comment_id)
        comment.soft_delete(actor_employee_no, actor_is_admin, self.clock())
        self.comments.save(comment)

    def list_comments(self, post_id: int, viewer_employee_no: int) -> list[Comment]:
        self._ensure_active(viewer_employee_no)
        self._ensure_post_visible(post_id)
        return self.comments.list_for_post(post_id)

    def _ensure_post_visible(self, post_id: int) -> None:
        post = self.posts.get(post_id)
        if post.deleted_at is not None:
            raise PostNotFoundError("게시글을 찾을 수 없습니다.")

    def _get_visible(self, comment_id: int) -> Comment:
        comment = self.comments.get(comment_id)
        if comment.deleted_at is not None:
            raise CommentNotFoundError("댓글을 찾을 수 없습니다.")
        return comment

    def _ensure_active(self, employee_no: int) -> None:
        if not self.workforce.is_active_employee(employee_no):
            raise InactiveEmployeeError("재직 중인 사원만 게시판을 사용할 수 있습니다.")
