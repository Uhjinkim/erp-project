class PayrollError(Exception):
    code = "payroll_error"


class InvalidPayPeriodError(PayrollError):
    code = "invalid_period"


class InvalidPayrollAmountError(PayrollError):
    code = "invalid_amount"


class InvalidPayrollTransitionError(PayrollError):
    code = "invalid_status_transition"


class EmptyPayrollItemsError(PayrollError):
    code = "empty_items"


class PayrollPermissionError(PayrollError):
    code = "permission_denied"


class PayrollStatementNotFoundError(PayrollError):
    code = "statement_not_found"


class DuplicatePayrollStatementError(PayrollError):
    code = "duplicate_statement"


class PayrollComponentNotFoundError(PayrollError):
    code = "component_not_found"


class InactiveEmployeeError(PayrollError):
    code = "inactive_employee"
