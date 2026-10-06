from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from workforce.application.personal_info import PersonalInfoService, RequestNotFound
from workforce.application.services import assign_employee_role, revoke_employee_role
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.personal_info import ApprovalRequiredValues, ChangeRequestStatus
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)
from workforce.infrastructure.personal_info import DjangoPersonalInfoRepository
from workforce.presentation.permissions import (
    IsHRManager,
    IsHRManagerOrReadOnly,
    IsSelfOrHRManager,
    request_employee_no,
)
from workforce.presentation.serializers import (
    ChangeRequestCreateSerializer,
    ChangeRequestRejectSerializer,
    ChangeRequestSerializer,
    DepartmentSerializer,
    EmployeeDetailSerializer,
    EmployeeRoleSerializer,
    EmployeeSerializer,
    OwnContactUpdateSerializer,
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

    def get_permissions(self) -> list[BasePermission]:
        # HR-001: 목록은 인사관리자만, 상세는 본인 또는 인사관리자만 조회한다.
        if self.action == "list":
            return [IsAuthenticated(), IsHRManager()]
        if self.action == "retrieve":
            return [IsAuthenticated(), IsSelfOrHRManager()]
        return super().get_permissions()

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        if self.action in {"retrieve", "me"}:
            return EmployeeDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self) -> QuerySet[Employee]:
        queryset = Employee.objects.select_related("person", "department", "position")
        if self.action != "list":
            return queryset
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

    @action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def me(self, request: Request) -> Response:
        """FN-HR-001 본인 인사 정보 조회, FN-HR-002 연락처·주소 직접 수정."""
        employee_no = request_employee_no(request)
        if employee_no is None:
            return Response(
                {"detail": "계정에 연결된 사원 정보가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if request.method == "PATCH":
            serializer = OwnContactUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            # 허용되지 않은 항목도 넘겨 HR-002 도메인 정책이 거절 사유를 결정하게 한다.
            unknown = {
                key: request.data[key] for key in request.data if key not in serializer.fields
            }
            try:
                personal_info_service().update_own_contact(
                    employee_no, {**serializer.validated_data, **unknown}
                )
            except WorkforceRuleViolation as exc:
                return rule_violation_response(exc)
        employee = self.get_queryset().filter(employee_no=employee_no).first()
        if employee is None:
            return Response(
                {"detail": "계정에 연결된 사원 정보가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(EmployeeDetailSerializer(employee).data)

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


def personal_info_service() -> PersonalInfoService:
    return PersonalInfoService(DjangoPersonalInfoRepository(), timezone.now)


def rule_violation_response(exc: WorkforceRuleViolation) -> Response:
    if isinstance(exc, RequestNotFound):
        return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
    body = {"detail": exc.message}
    if exc.field:
        body["field"] = exc.field
    return Response(body, status=status.HTTP_400_BAD_REQUEST)


class PersonalInfoChangeRequestViewSet(viewsets.ViewSet):
    """HR-003: 사내 이메일·급여계좌 변경 요청(FN-HR-003~005, FN-HR-011)."""

    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"\d+"

    def get_permissions(self) -> list[BasePermission]:
        # FN-HR-004: 승인·반려는 인사관리자만 처리한다.
        if self.action in {"approve", "reject"}:
            return [IsAuthenticated(), IsHRManager()]
        return super().get_permissions()

    def list(self, request: Request) -> Response:
        status_value = request.query_params.get("status", "").strip()
        try:
            status_filter = ChangeRequestStatus(status_value) if status_value else None
        except ValueError:
            return Response(
                {"detail": "알 수 없는 요청 상태입니다."}, status=status.HTTP_400_BAD_REQUEST
            )
        requests = personal_info_service().list_requests(
            viewer_employee_no=request_employee_no(request),
            viewer_is_hr_manager=self._is_hr_manager(request),
            status=status_filter,
        )
        return Response(ChangeRequestSerializer(requests, many=True).data)

    def create(self, request: Request) -> Response:
        employee_no = request_employee_no(request)
        if employee_no is None:
            return Response(
                {"detail": "계정에 연결된 사원 정보가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ChangeRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_request = personal_info_service().submit_change_request(
                employee_no, ApprovalRequiredValues(**serializer.validated_data)
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(
            ChangeRequestSerializer(change_request).data, status=status.HTTP_201_CREATED
        )

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        try:
            change_request = personal_info_service().get(
                int(pk),
                viewer_employee_no=request_employee_no(request),
                viewer_is_hr_manager=self._is_hr_manager(request),
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(ChangeRequestSerializer(change_request).data)

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        try:
            change_request = personal_info_service().approve(
                int(pk), request_employee_no(request)
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(ChangeRequestSerializer(change_request).data)

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        serializer = ChangeRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_request = personal_info_service().reject(
                int(pk),
                request_employee_no(request),
                serializer.validated_data.get("reason"),
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(ChangeRequestSerializer(change_request).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        try:
            change_request = personal_info_service().cancel(
                int(pk), request_employee_no(request)
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(ChangeRequestSerializer(change_request).data)

    def _is_hr_manager(self, request: Request) -> bool:
        return IsHRManager().has_permission(request, self)
