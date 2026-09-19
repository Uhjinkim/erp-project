from django.contrib import admin

from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)

admin.site.register([Person, Position, Department, Employee, Role, EmployeeRole])
