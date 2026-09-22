class BoardError(Exception):
    code = "board_error"


class InvalidPostContentError(BoardError):
    code = "invalid_post_content"


class BoardPermissionError(BoardError):
    code = "permission_denied"


class InactiveEmployeeError(BoardError):
    code = "inactive_employee"


class NoticeCategoryNotAllowedError(BoardError):
    code = "notice_category_not_allowed"


class PostNotFoundError(BoardError):
    code = "post_not_found"
