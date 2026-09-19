"""Django model discovery entry point.

Concrete ORM models live in ``workforce.infrastructure.models``. Django imports this
module by convention, so it intentionally re-exports the infrastructure models.
"""

from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    EmploymentHistory,
    Person,
    Position,
    Role,
)

__all__ = [
    "Department",
    "Employee",
    "EmployeeRole",
    "EmploymentHistory",
    "Person",
    "Position",
    "Role",
]
