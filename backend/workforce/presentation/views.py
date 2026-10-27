from collections.abc import Callable

from django.db.models import Q, QuerySet
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from workforce.application.history import (
    CancellationCommand,
    CorrectionCommand,
    EmploymentHistoryService,
    TransferCommand,
    TransferResult,
)
from workforce.application.lifecycle import EmployeeNotFound, EmploymentLifecycleService
from workforce.application.onboarding import (
    EmploymentCommand,
    NewHireAccount,
    NewHireRegistrationService,
    RegisteredNewHire,
    RegisterNewHireCommand,
    RegistrationRetryExhausted,
    RehireCommand,
)
from workforce.application.personal_info import (
    Actor,
    PersonalInfoService,
    ProcessingNotAllowed,
    RequestNotFound,
)
from workforce.application.services import (
    HR_MANAGER_ROLE,
    assign_employee_role,
    employee_has_role,
    revoke_employee_role,
)
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.history import HistoryChange
from workforce.domain.lifecycle import RetiredEmployeeCriteria
from workforce.domain.personal_info import ApprovalRequiredValues, ChangeRequestStatus
from workforce.infrastructure.accounts import DjangoAccountGateway
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.history import DjangoEmploymentHistoryRepository
from workforce.infrastructure.lifecycle import DjangoEmploymentLifecycleRepository
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)
from workforce.infrastructure.onboarding import DjangoNewHireUnitOfWork
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
    HistoryCancellationSerializer,
    HistoryChangeSerializer,
    HistoryCorrectionSerializer,
    HistoryEntrySerializer,
    NewHireRegistrationSerializer,
    PersonSerializer,
    PositionSerializer,
    RegisteredNewHireSerializer,
    RehireSerializer,
    RetiredEmployeeQuerySerializer,
    RetiredEmployeeSerializer,
    RoleSerializer,
    TerminationSerializer,
    TransferResultSerializer,
    TransferSerializer,
)


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects.all().order_by("person_id")
    serializer_class = PersonSerializer
    permission_classes = [IsAuthenticated, IsHRManager]

    @action(detail=True, methods=["post"])
    def rehire(self, request: Request, pk: str | None = None) -> Response:
        """FN-HR-009: 퇴사한 Person에 새 사번으로 고용을 추가한다(HR-006)."""
        serializer = RehireSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = employment_command_values(serializer.validated_data)
        command = RehireCommand(person_id=int(pk), **data)
        return run_registration(command, lambda service: service.rehire(command))


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

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request: Request) -> Response:
        """FN-HR-001 본인 인사 정보 조회. 본인 수정은 수정 요청(HR-002)으로만 한다."""
        employee_no = request_employee_no(request)
        if employee_no is None:
            return Response(
                {"detail": "계정에 연결된 사원 정보가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        employee = self.get_queryset().filter(employee_no=employee_no).first()
        if employee is None:
            return Response(
                {"detail": "계정에 연결된 사원 정보가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(EmployeeDetailSerializer(employee).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="terminated",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def terminated(self, request: Request) -> Response:
        """FN-HR-008: 퇴사자 조회. HR-005에 따라 인사관리자만 조회한다."""
        query = RetiredEmployeeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        try:
            retired = lifecycle_service().list_retired(
                RetiredEmployeeCriteria(**query.validated_data)
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(RetiredEmployeeSerializer(retired, many=True).data)

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def terminate(self, request: Request, emp_no: str | None = None) -> Response:
        """FN-HR-007: 퇴사 처리. 상태·퇴사일만 바꾸고 다른 기록은 보존한다(HR-005)."""
        if not str(emp_no).isdigit():
            return Response(
                {"detail": "사원을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = TerminationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            lifecycle_service().terminate(int(emp_no), serializer.validated_data["term_date"])
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(EmployeeDetailSerializer(self.get_queryset().get(employee_no=emp_no)).data)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="history",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def history(self, request: Request, emp_no: str | None = None) -> Response:
        """FN-HR-010 인사이력 조회(GET)와 발령 등록(POST). 인사관리자만 사용한다."""
        if request.method == "GET":
            return history_response(emp_no, lambda service, no: service.history(no))
        serializer = TransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return history_response(
            emp_no,
            lambda service, no: service.transfer(
                TransferCommand(
                    employee_no=no,
                    changed_by=request_employee_no(request),
                    **serializer.validated_data,
                )
            ),
            created=True,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"history/(?P<history_id>\d+)/correct",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def correct_history(
        self, request: Request, emp_no: str | None = None, history_id: str | None = None
    ) -> Response:
        """FN-HR-010 진행 중인 최근 이력 정정. 사유 필수, 정정 전·후 값을 기록한다."""
        serializer = HistoryCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return history_response(
            emp_no,
            lambda service, no: service.correct(
                CorrectionCommand(
                    employee_no=no,
                    history_id=int(history_id),
                    changed_by=request_employee_no(request),
                    **serializer.validated_data,
                )
            ),
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"history/(?P<history_id>\d+)/cancel",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def cancel_history(
        self, request: Request, emp_no: str | None = None, history_id: str | None = None
    ) -> Response:
        """FN-HR-010 최근 발령 취소. 직전 이력을 다시 진행 중으로 되돌린다."""
        serializer = HistoryCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return history_response(
            emp_no,
            lambda service, no: service.cancel(
                CancellationCommand(
                    employee_no=no,
                    history_id=int(history_id),
                    reason=serializer.validated_data["reason"],
                    changed_by=request_employee_no(request),
                )
            ),
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="history/changes",
        permission_classes=[IsAuthenticated, IsHRManager],
    )
    def history_changes(self, request: Request, emp_no: str | None = None) -> Response:
        """FN-HR-010 발령·정정·취소 기록 조회."""
        return history_response(emp_no, lambda service, no: service.changes(no))

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
    return PersonalInfoService(
        DjangoPersonalInfoRepository(), DjangoWorkforceQueryGateway(), timezone.now
    )


def request_actor(request: Request) -> Actor:
    employee_no = request_employee_no(request)
    return Actor(
        employee_no=employee_no,
        is_hr_manager=employee_no is not None
        and employee_has_role(employee_no, HR_MANAGER_ROLE, DjangoWorkforceQueryGateway()),
        is_superuser=request.user.is_superuser,
    )


def rule_violation_response(exc: WorkforceRuleViolation) -> Response:
    if isinstance(exc, RequestNotFound | EmployeeNotFound):
        return Response({"detail": exc.message}, status=status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ProcessingNotAllowed):
        return Response({"detail": exc.message}, status=status.HTTP_403_FORBIDDEN)
    body = {"detail": exc.message}
    if exc.field:
        body["field"] = exc.field
    return Response(body, status=status.HTTP_400_BAD_REQUEST)


class PersonalInfoChangeRequestViewSet(viewsets.ViewSet):
    """HR-002/HR-003: 개인정보 수정 요청(FN-HR-003~005, FN-HR-011).

    승인·반려 처리자는 승인 시점의 조직 정보로 애플리케이션 계층이 판정한다.
    """

    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"\d+"

    def list(self, request: Request) -> Response:
        status_value = request.query_params.get("status", "").strip()
        try:
            status_filter = ChangeRequestStatus(status_value) if status_value else None
        except ValueError:
            return Response(
                {"detail": "알 수 없는 요청 상태입니다."}, status=status.HTTP_400_BAD_REQUEST
            )
        service = personal_info_service()
        actor = request_actor(request)
        requests = service.list_requests(
            actor,
            status=status_filter,
            processable_only=request.query_params.get("processable") == "true",
            mine_only=request.query_params.get("mine") == "true",
        )
        return Response(self._serialize(service, actor, requests, many=True))

    def create(self, request: Request) -> Response:
        employee_no = request_employee_no(request)
        if employee_no is None:
            return Response(
                {"detail": "계정에 연결된 사원 정보가 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ChangeRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = personal_info_service()
        try:
            change_request = service.submit_change_request(
                employee_no, ApprovalRequiredValues(**serializer.validated_data)
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(
            self._serialize(service, request_actor(request), change_request),
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        service = personal_info_service()
        actor = request_actor(request)
        try:
            change_request = service.get(int(pk), actor)
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(self._serialize(service, actor, change_request))

    @action(detail=True, methods=["post"])
    def approve(self, request: Request, pk: str | None = None) -> Response:
        service = personal_info_service()
        actor = request_actor(request)
        try:
            change_request = service.approve(int(pk), actor)
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(self._serialize(service, actor, change_request))

    @action(detail=True, methods=["post"])
    def reject(self, request: Request, pk: str | None = None) -> Response:
        serializer = ChangeRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = personal_info_service()
        actor = request_actor(request)
        try:
            change_request = service.reject(
                int(pk), actor, serializer.validated_data.get("reason")
            )
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(self._serialize(service, actor, change_request))

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        service = personal_info_service()
        actor = request_actor(request)
        try:
            change_request = service.cancel(int(pk), actor)
        except WorkforceRuleViolation as exc:
            return rule_violation_response(exc)
        return Response(self._serialize(service, actor, change_request))

    @staticmethod
    def _serialize(
        service: PersonalInfoService,
        actor: Actor,
        data: object,
        *,
        many: bool = False,
    ) -> object:
        items = data if many else [data]
        processable = {
            item.request_id for item in items if service.can_process(item, actor)
        }
        return ChangeRequestSerializer(
            data, many=many, context={"processable_ids": processable}
        ).data


def employment_command_values(validated: dict[str, object]) -> dict[str, object]:
    data = dict(validated)
    account = data.pop("account", None)
    data["role_codes"] = tuple(data["role_codes"])
    data["account"] = NewHireAccount(**account) if account else None
    return data


def run_registration(
    command: EmploymentCommand,
    register: Callable[[NewHireRegistrationService], RegisteredNewHire],
) -> Response:
    service = NewHireRegistrationService(
        DjangoNewHireUnitOfWork(), DjangoAccountGateway(), DjangoWorkforceQueryGateway()
    )
    try:
        result = register(service)
    except RegistrationRetryExhausted as exc:
        return Response({"detail": exc.message}, status=status.HTTP_409_CONFLICT)
    except WorkforceRuleViolation as exc:
        return rule_violation_response(exc)
    return Response(
        RegisteredNewHireSerializer({"command": command, "result": result}).data,
        status=status.HTTP_201_CREATED,
    )


def history_response(
    emp_no: str | None,
    run: Callable[[EmploymentHistoryService, int], object],
    *,
    created: bool = False,
) -> Response:
    if not str(emp_no).isdigit():
        return Response({"detail": "사원을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    service = EmploymentHistoryService(DjangoEmploymentHistoryRepository(), timezone.localdate)
    try:
        result = run(service, int(emp_no))
    except WorkforceRuleViolation as exc:
        return rule_violation_response(exc)
    if isinstance(result, TransferResult):
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(TransferResultSerializer(result).data, status=status_code)
    if result and isinstance(result[0], HistoryChange):
        return Response(HistoryChangeSerializer(result, many=True).data)
    return Response(HistoryEntrySerializer(result, many=True).data)


def lifecycle_service() -> EmploymentLifecycleService:
    repository = DjangoEmploymentLifecycleRepository()
    return EmploymentLifecycleService(repository, repository, timezone.localdate)


class NewHireRegistrationView(APIView):
    """FN-HR-006: 인사관리자의 신규 입사자 통합 등록(사원·최초 인사이력·역할·계정)."""

    permission_classes = [IsAuthenticated, IsHRManager]

    def post(self, request: Request) -> Response:
        serializer = NewHireRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        command = RegisterNewHireCommand(**employment_command_values(serializer.validated_data))
        return run_registration(command, lambda service: service.register(command))
