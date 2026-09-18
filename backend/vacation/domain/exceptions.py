class VacationError(Exception):
    code = "vacation_error"


class InvalidVacationPeriodError(VacationError):
    code = "invalid_period"


class InvalidUseDaysError(VacationError):
    code = "invalid_use_days"


class InvalidStatusTransitionError(VacationError):
    code = "invalid_status_transition"


class VacationPermissionError(VacationError):
    code = "permission_denied"


class InsufficientLeaveDaysError(VacationError):
    code = "insufficient_leave_days"


class InactiveEmployeeError(VacationError):
    code = "inactive_employee"


class ApproverNotFoundError(VacationError):
    code = "approver_not_found"


class VacationRequestNotFoundError(VacationError):
    code = "request_not_found"


class VacationTypeNotFoundError(VacationError):
    code = "type_not_found"
