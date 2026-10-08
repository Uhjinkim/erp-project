from dataclasses import dataclass

from board.domain.exceptions import InvalidCommentContentError, InvalidPostContentError

TITLE_MAX_LENGTH = 100
COMMENT_MAX_LENGTH = 1000


@dataclass(frozen=True)
class PostTitle:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidPostContentError("제목은 필수입니다.")
        if len(self.value) > TITLE_MAX_LENGTH:
            raise InvalidPostContentError(f"제목은 {TITLE_MAX_LENGTH}자를 초과할 수 없습니다.")


@dataclass(frozen=True)
class PostContent:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidPostContentError("내용은 필수입니다.")


@dataclass(frozen=True)
class CommentContent:
    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise InvalidCommentContentError("댓글 내용은 필수입니다.")
        if len(self.value) > COMMENT_MAX_LENGTH:
            raise InvalidCommentContentError(f"댓글은 {COMMENT_MAX_LENGTH}자를 초과할 수 없습니다.")
