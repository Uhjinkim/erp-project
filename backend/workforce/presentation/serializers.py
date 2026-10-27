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

    def validate_emp_no(self, value: int) -> int:
        # HR-007: 사번은 불변 PK이므로 수정 요청으로 바꿀 수 없다.
        if self.instance is not None and value != self.instance.employee_no:
            raise serializers.ValidationError("사번은 변경할 수 없습니다.")
        return value

    def validate_email(self, value: str | None) -> str | None:
        value = value.strip().lower() if value else value
        # HR-002/HR-003: 등록 이후 사내 이메일은 수정 요청·승인 절차로만 바꾼다.
        if self.instance is not None and value != self.instance.email:
            raise serializers.ValidationError(
                "사내 이메일은 개인정보 수정 요청과 승인 절차로만 변경할 수 있습니다."
            )
        return value


class EmployeeDetailSerializer(serializers.ModelSerializer):
    """FN-HR-001 인사 정보 조회 응답. 급여계좌(bank_code, account_no)를 포함한다."""

    emp_no = serializers.IntegerField(source="employee_no", read_only=True)
    person_id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(source="person.name", read_only=True)
    birth_date = serializers.DateField(source="person.birth_date", read_only=True)
    gender = serializers.CharField(source="person.gender", read_only=True)
    dept_no = serializers.IntegerField(source="department_id", read_only=True)
    dept_name = serializers.CharField(
        source="department.dept_name", read_only=True, default=None
    )
    position_code = serializers.CharField(source="position_id", read_only=True)
    position_name = serializers.CharField(
        source="position.position_name", read_only=True, default=None
    )

    class Meta:
        model = Employee
        fields = [
            "emp_no",
            "person_id",
            "name",
            "birth_date",
            "gender",
            "dept_no",
            "dept_name",
            "position_code",
            "position_name",
            "tenure_status",
            "email",
            "phone",
            "extension_no",
            "address",
            "bank_code",
            "account_no",
            "hire_date",
            "term_date",
        ]
        read_only_fields = fields


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


class ChangeRequestCreateSerializer(serializers.Serializer):
    """FN-HR-003 요청 형식. 생략하거나 null인 항목은 수정하지 않는다.

    연락처·주소를 빈 문자열로 보내면 미등록으로 지우는 요청이다.
    """

    phone = serializers.CharField(
        max_length=20, required=False, allow_null=True, allow_blank=True, trim_whitespace=True
    )
    address = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True, trim_whitespace=True
    )
    email = serializers.EmailField(max_length=100, required=False, allow_null=True)
    bank_code = serializers.CharField(max_length=20, required=False, allow_null=True)
    account_no = serializers.CharField(max_length=100, required=False, allow_null=True)

    def validate_email(self, value: str | None) -> str | None:
        return value.strip().lower() if value else None

    def validate_bank_code(self, value: str | None) -> str | None:
        return value.strip() or None if value else None

    def validate_account_no(self, value: str | None) -> str | None:
        return value.strip() or None if value else None


class ChangeRequestRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ApprovalRequiredValuesSerializer(serializers.Serializer):
    phone = serializers.CharField(allow_null=True, allow_blank=True)
    address = serializers.CharField(allow_null=True, allow_blank=True)
    email = serializers.CharField(allow_null=True)
    bank_code = serializers.CharField(allow_null=True)
    account_no = serializers.CharField(allow_null=True)


class ChangeRequestSerializer(serializers.Serializer):
    """FN-HR-005 결과·이력 응답."""

    request_id = serializers.IntegerField()
    emp_no = serializers.IntegerField(source="employee_no")
    status = serializers.CharField()
    previous = ApprovalRequiredValuesSerializer()
    requested = serializers.SerializerMethodField()
    changed_fields = serializers.SerializerMethodField()
    requested_at = serializers.DateTimeField()
    processed_by = serializers.IntegerField(allow_null=True)
    processed_at = serializers.DateTimeField(allow_null=True)
    reject_reason = serializers.CharField(allow_null=True)
    can_process = serializers.SerializerMethodField()

    def get_requested(self, request: object) -> dict[str, object]:
        # 계좌번호 원문은 대기 요청을 처리할 수 있는 사용자에게만 보여 준다.
        values = request.requested if self.get_can_process(request) else request.requested.masked()
        return ApprovalRequiredValuesSerializer(values).data

    def get_changed_fields(self, request: object) -> list[str]:
        return request.requested.changed_fields()

    def get_can_process(self, request: object) -> bool:
        return request.request_id in self.context.get("processable_ids", set())


class NewHireAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)


class NewHireRegistrationSerializer(serializers.Serializer):
    """FN-HR-006 요청 형식. 사번은 서버가 발급하므로 받지 않는다(HR-007)."""

    name = serializers.CharField(max_length=50)
    birth_date = serializers.DateField()
    gender = serializers.ChoiceField(choices=["M", "F"])
    email = serializers.EmailField(max_length=100)
    hire_date = serializers.DateField()
    dept_no = serializers.IntegerField()
    position_code = serializers.CharField(max_length=20)
    phone = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    extension_no = serializers.CharField(
        max_length=20, required=False, allow_null=True, allow_blank=True
    )
    address = serializers.CharField(
        max_length=255, required=False, allow_null=True, allow_blank=True
    )
    base_salary = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    role_codes = serializers.ListField(
        child=serializers.CharField(max_length=30), required=False, default=list
    )
    account = NewHireAccountSerializer(required=False, allow_null=True)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if "emp_no" in self.initial_data:
            raise serializers.ValidationError({"emp_no": "사번은 서버에서 자동 발급합니다."})
        return attrs

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_phone(self, value: str | None) -> str | None:
        return value.strip() or None if value else None

    def validate_extension_no(self, value: str | None) -> str | None:
        return value.strip() or None if value else None

    def validate_address(self, value: str | None) -> str | None:
        return value.strip() or None if value else None


class RegisteredNewHireSerializer(serializers.Serializer):
    """FN-HR-006 응답. 초기 비밀번호는 응답에 포함하지 않는다."""

    emp_no = serializers.IntegerField(source="result.employee_no")
    person_id = serializers.IntegerField(source="result.person_id")
    history_id = serializers.IntegerField(source="result.history_id")
    name = serializers.CharField(source="result.name")
    email = serializers.EmailField(source="command.email")
    dept_no = serializers.IntegerField(source="command.dept_no")
    position_code = serializers.CharField(source="command.position_code")
    hire_date = serializers.DateField(source="command.hire_date")
    tenure_status = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    def get_tenure_status(self, data: object) -> str:
        return Employee.TenureStatus.ACTIVE.value

    def get_account(self, data: object) -> dict[str, object] | None:
        account_id = data["result"].account_id
        if account_id is None:
            return None
        return {"id": account_id, "email": data["command"].email}

    def get_roles(self, data: object) -> list[dict[str, object]]:
        return [
            {"employee_role_id": item.employee_role_id, "role_code": item.role_code}
            for item in data["result"].role_assignments
        ]


class RehireSerializer(NewHireRegistrationSerializer):
    """FN-HR-009 요청 형식. 인적사항은 보낼 때만 기존 Person을 갱신한다."""

    name = serializers.CharField(max_length=50, required=False)
    birth_date = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=["M", "F"], required=False)


class TerminationSerializer(serializers.Serializer):
    """FN-HR-007 요청 형식."""

    term_date = serializers.DateField()


class RetiredEmployeeQuerySerializer(serializers.Serializer):
    """FN-HR-008 조회 조건(쿼리 파라미터)."""

    name = serializers.CharField(required=False, allow_blank=True)
    dept_no = serializers.IntegerField(required=False)
    emp_no = serializers.IntegerField(required=False, source="employee_no")
    term_date_from = serializers.DateField(required=False)
    term_date_to = serializers.DateField(required=False)

    def validate_name(self, value: str) -> str | None:
        return value.strip() or None


class RetiredEmployeeSerializer(serializers.Serializer):
    """FN-HR-008 응답. 급여계좌 등 상세 개인정보는 사원 상세 API에서 조회한다."""

    emp_no = serializers.IntegerField(source="employee_no")
    person_id = serializers.IntegerField()
    name = serializers.CharField()
    dept_no = serializers.IntegerField(allow_null=True)
    dept_name = serializers.CharField(allow_null=True)
    position_code = serializers.CharField(allow_null=True)
    position_name = serializers.CharField(allow_null=True)
    email = serializers.CharField(allow_null=True)
    hire_date = serializers.DateField()
    term_date = serializers.DateField()


class TransferSerializer(serializers.Serializer):
    """FN-HR-010 발령 요청 형식."""

    start_date = serializers.DateField()
    dept_no = serializers.IntegerField()
    position_code = serializers.CharField(max_length=20)
    base_salary = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    previous_base_salary = serializers.DecimalField(
        max_digits=15, decimal_places=2, min_value=0, required=False, allow_null=True
    )
    reason = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )


class HistoryCorrectionSerializer(serializers.Serializer):
    """FN-HR-010 최근 이력 정정 요청. 정정 후 값 전체와 사유를 받는다."""

    start_date = serializers.DateField()
    dept_no = serializers.IntegerField()
    position_code = serializers.CharField(max_length=20)
    base_salary = serializers.DecimalField(max_digits=15, decimal_places=2, min_value=0)
    reason = serializers.CharField(max_length=500)


class HistoryCancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class HistoryEntrySerializer(serializers.Serializer):
    """FN-HR-010 인사이력 응답."""

    history_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    dept_no = serializers.IntegerField()
    dept_name = serializers.CharField(allow_null=True)
    position_code = serializers.CharField()
    position_name = serializers.CharField(allow_null=True)
    base_salary = serializers.DecimalField(max_digits=15, decimal_places=2)


class TransferResultSerializer(serializers.Serializer):
    history = HistoryEntrySerializer(many=True)
    released_head_dept_nos = serializers.ListField(child=serializers.IntegerField())
    restored_head_dept_nos = serializers.ListField(child=serializers.IntegerField())


class HistoryValuesSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField(allow_null=True)
    dept_no = serializers.IntegerField()
    position_code = serializers.CharField()
    base_salary = serializers.DecimalField(max_digits=15, decimal_places=2)


class HistoryChangeSerializer(serializers.Serializer):
    """FN-HR-010 발령·정정·취소 기록 응답."""

    history_id = serializers.IntegerField()
    action = serializers.CharField()
    before = HistoryValuesSerializer(allow_null=True)
    after = HistoryValuesSerializer(allow_null=True)
    reason = serializers.CharField(allow_null=True)
    changed_by = serializers.IntegerField(allow_null=True)
    changed_at = serializers.DateTimeField()
    released_head_dept_nos = serializers.ListField(child=serializers.IntegerField())
    restored_head_dept_nos = serializers.ListField(child=serializers.IntegerField())
