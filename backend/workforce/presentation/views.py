from django.db.models import Q, QuerySet
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from workforce.application.services import assign_employee_role, revoke_employee_role
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)
from workforce.presentation.permissions import IsHRManager, IsHRManagerOrReadOnly
from workforce.presentation.serializers import (
    DepartmentSerializer,
    EmployeeRoleSerializer,
    EmployeeSerializer,
    PersonSerializer,
    PositionSerializer,
    RoleSerializer,
)


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all().order_by("person_id")
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated, IsHRManager]


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated, IsHRManagerOrReadOnly]
    lookup_field = "employee_no"
    lookup_url_kwarg = "emp_no"

    def get_queryset(self) -> QuerySet[Employee]:
        queryset = Employee.objects.select_related("person", "department", "position")
        search = self.request.query_params.get("search", "").strip()
        department = self.request.query_params.get("dept_no", "").strip()
        status_value = self.request.query_params.get("tenure_status", "").strip()
        if search:
            search_query = Q(person__name__icontains=search) | Q(email__icontains=search)
            if search.isdigit():
                search_query |= Q(employee_no=int(search))
            queryset = queryset.filter(search_query)
        if department:
            queryset = queryset.filter(department_id=department)
        if status_value:
            queryset = queryset.filter(tenure_status=status_value)
        return queryset.order_by("employee_no")

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="roles",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def roles(self, request: Request, emp_no: int | None = None) -> Response:
        employee = self.get_object()
        if request.method == "GET":
            assignments = employee.role_assignments.select_related("role").all()
            return Response(EmployeeRoleSerializer(assignments, many=True).data)

        serializer = EmployeeRoleSerializer(
            data={**request.data, "emp_no": employee.employee_no}
        )
        serializer.is_valid(raise_exception=True)
        try:
            assignment_id = assign_employee_role(
                employee.employee_no,
                serializer.validated_data["role"].role_code,
                DjangoWorkforceQueryGateway(),
            )
        except WorkforceRuleViolation as exc:
            detail = {exc.field: exc.message} if exc.field else exc.message
            raise serializers.ValidationError(detail) from exc
        assignment = EmployeeRole.objects.select_related("employee", "role").get(
            employee_role_id=assignment_id
        )
        return Response(
            EmployeeRoleSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"roles/(?P<assignment_id>\d+)/revoke",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def revoke_role(
        self,
        request: Request,
        emp_no: int | None = None,
        assignment_id: int | None = None,
    ) -> Response:
        employee = self.get_object()
        try:
            revoke_employee_role(
                employee.employee_no,
                int(assignment_id),
                DjangoWorkforceQueryGateway(),
            )
        except WorkforceRuleViolation as exc:
            return Response({"detail": exc.message}, status=404)
        assignment = employee.role_assignments.get(employee_role_id=assignment_id)
        return Response(EmployeeRoleSerializer(assignment).data)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.select_related("parent", "head").all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated, IsHRManagerOrReadOnly]


class PositionViewSet(viewsets.ModelViewSet):
    queryset = Position.objects.all()
    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated, IsHRManagerOrReadOnly]


class RoleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
