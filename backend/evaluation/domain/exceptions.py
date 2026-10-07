class EvaluationError(Exception):
    code = "evaluation_error"


class InvalidEvaluationError(EvaluationError):
    code = "invalid_evaluation"


class EvaluationYearNotAllowedError(InvalidEvaluationError):
    code = "eval_year_not_allowed"


class EvaluationPermissionError(EvaluationError):
    code = "permission_denied"


class SelfEvaluationError(EvaluationPermissionError):
    code = "self_evaluation_not_allowed"


class HRManagerEvaluatorError(EvaluationPermissionError):
    code = "hr_manager_cannot_evaluate"


class ConfirmationNotAllowedError(EvaluationPermissionError):
    code = "confirmation_not_allowed"


class InactiveEmployeeError(EvaluationError):
    code = "inactive_employee"


class EvaluationNotFoundError(EvaluationError):
    code = "evaluation_not_found"


class DuplicateEvaluationError(EvaluationError):
    code = "duplicate_evaluation"


class EvaluationStateError(EvaluationError):
    code = "invalid_evaluation_state"


class EvaluationConflictError(EvaluationError):
    code = "evaluation_conflict"
