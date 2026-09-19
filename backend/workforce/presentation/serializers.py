from rest_framework import serializers

from workforce.domain.policies import validate_employment_dates
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = ["person_id", "name", "birth_date", "gender"]


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = ["position_code", "position_name", "sort_order"]


class DepartmentSerializer(serializers.ModelSerializer):
    parent_dept_no = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=Department.objects.all(),
        allow_null=True,
        required=False,
    )
    head_emp_no = serializers.PrimaryKeyRelatedField(
        source="head",
        queryset=Employee.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Department
        fields = ["dept_no", "dept_name", "parent_dept_no", "head_emp_no"]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        department_no = attrs.get("dept_no") or getattr(self.instance, "dept_no", None)
        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        seen = {department_no}
        while parent is not None:
            if parent.dept_no in seen:
                raise serializers.ValidationError(
                    {"parent_dept_no": "부서 계층은 순환할 수 없습니다."}
                )
            seen.add(parent.dept_no)
            parent = parent.parent

        head = attrs.get("head", getattr(self.instance, "head", None))
        if head is not None and not head.is_active_employee:
            raise serializers.ValidationError(
                {"head_emp_no": "재직 중인 사원만 부서장이 될 수 있습니다."}
            )
        if head is not None and department_no is not None and head.department_id != department_no:
            raise serializers.ValidationError(
                {"head_emp_no": "해당 부서에 소속된 사원만 부서장이 될 수 있습니다."}
            )
        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    emp_no = serializers.IntegerField(source="employee_no")
    name = serializers.CharField(source="person.name", read_only=True)
    person_id = serializers.PrimaryKeyRelatedField(source="person", queryset=Person.objects.all())
    dept_no = serializers.PrimaryKeyRelatedField(
        source="department", queryset=Department.objects.all(), allow_null=True, required=False
    )
    position_code = serializers.PrimaryKeyRelatedField(
        source="position", queryset=Position.objects.all(), allow_null=True, required=False
    )

    class Meta:
        model = Employee
        fields = [
            "emp_no",
            "person_id",
            "name",
            "dept_no",
            "position_code",
            "tenure_status",
            "email",
            "phone",
            "extension_no",
            "hire_date",
            "term_date",
        ]

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        hire_date = attrs.get("hire_date", getattr(self.instance, "hire_date", None))
        term_date = attrs.get("term_date", getattr(self.instance, "term_date", None))
        tenure_status = attrs.get(
            "tenure_status", getattr(self.instance, "tenure_status", None)
        )
        if hire_date and tenure_status:
            errors = validate_employment_dates(
                tenure_status=str(tenure_status),
                hire_date=hire_date,
                term_date=term_date,
            )
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    def validate_email(self, value: str | None) -> str | None:
        return value.strip().lower() if value else value


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["role_code", "role_name"]


class EmployeeRoleSerializer(serializers.ModelSerializer):
    emp_no = serializers.PrimaryKeyRelatedField(source="employee", queryset=Employee.objects.all())
    role_code = serializers.PrimaryKeyRelatedField(source="role", queryset=Role.objects.all())

    class Meta:
        model = EmployeeRole
        fields = ["employee_role_id", "emp_no", "role_code", "assigned_at", "revoked_at"]
        read_only_fields = ["employee_role_id", "assigned_at", "revoked_at"]
