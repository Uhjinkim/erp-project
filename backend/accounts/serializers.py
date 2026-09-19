from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from workforce.application.services import HR_MANAGER_ROLE, employee_has_role
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Employee


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs: dict[str, str]) -> dict[str, object]:
        request = self.context["request"]
        email = attrs["email"].strip().lower()
        user = authenticate(request=request, email=email, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_active:
            raise serializers.ValidationError("비활성화된 계정입니다.")
        if user.employee is not None and not user.employee.is_active_employee:
            raise serializers.ValidationError("재직 중인 사원만 로그인할 수 있습니다.")
        attrs["user"] = user
        return attrs


class CurrentUserSerializer(serializers.ModelSerializer):
    employee = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "is_staff", "is_superuser", "employee", "roles"]

    def get_employee(self, user: User) -> dict[str, object] | None:
        employee: Employee | None = user.employee
        if employee is None:
            return None
        return {
            "emp_no": employee.employee_no,
            "name": employee.person.name,
            "dept_no": employee.department_id,
            "dept_name": employee.department.dept_name if employee.department else None,
            "position_code": employee.position_id,
            "position_name": employee.position.position_name if employee.position else None,
            "tenure_status": employee.tenure_status,
        }

    def get_roles(self, user: User) -> list[str]:
        if user.employee_id is None:
            return []
        now = timezone.now()
        return list(
            user.employee.role_assignments.filter(assigned_at__lte=now)
            .filter(Q(revoked_at__isnull=True) | Q(revoked_at__gt=now))
            .order_by("role_id")
            .values_list("role_id", flat=True)
        )


class AccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    emp_no = serializers.PrimaryKeyRelatedField(
        source="employee",
        queryset=Employee.objects.all(),
        allow_null=True,
        required=False,
    )
    is_hr_manager = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "password", "emp_no", "is_active", "is_hr_manager"]
        read_only_fields = ["id", "is_hr_manager"]

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def create(self, validated_data: dict[str, object]) -> User:
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance: User, validated_data: dict[str, object]) -> User:
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance

    def get_is_hr_manager(self, user: User) -> bool:
        return user.employee_id is not None and employee_has_role(
            user.employee_id,
            HR_MANAGER_ROLE,
            DjangoWorkforceQueryGateway(),
        )
