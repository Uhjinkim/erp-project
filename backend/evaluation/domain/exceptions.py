class EvaluationError(Exception):
    code = "evaluation_error"


class InvalidEvaluationError(EvaluationError):
    code = "invalid_evaluation"


class EvaluationPermissionError(EvaluationError):
    code = "permission_denied"


class SelfEvaluationError(EvaluationPermissionError):
    code = "self_evaluation_not_allowed"


class InactiveEmployeeError(EvaluationError):
    code = "inactive_employee"


class EvaluationNotFoundError(EvaluationError):
    code = "evaluation_not_found"


class DuplicateEvaluationError(EvaluationError):
    code = "duplicate_evaluation"


class EvaluationStateError(EvaluationError):
    code = "invalid_evaluation_state"
