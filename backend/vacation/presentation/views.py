from functools import cached_property

from django.utils import timezone
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from vacation.application.dto import (
    RequestVacationCommand,
    ResubmitVacationCommand,
    history_to_dict,
    request_to_dict,
    type_to_dict,
)
from vacation.application.service import VacationService
from vacation.domain.exceptions import (
    VacationError,
    VacationPermissionError,
    VacationRequestNotFoundError,
    VacationTypeNotFoundError,
)
from vacation.infrastructure.development_gateways import (
    SettingsLeaveBalanceGateway,
    SettingsWorkforceGateway,
)
from vacation.infrastructure.repositories import DjangoVacationUnitOfWork
from vacation.presentation.serializers import ReasonSerializer, VacationRequestInputSerializer


class VacationAPIView(APIView):
    @cached_property
    def service(self) -> VacationService:
        return VacationService(
            unit_of_work_factory=DjangoVacationUnitOfWork,
            workforce=SettingsWorkforceGateway(),
            balances=SettingsLeaveBalanceGateway(),
            clock=timezone.now,
        )

    def employee_no(self, request: Request) -> int:
        value = request.headers.get("X-Employee-No")
        if value is None:
            raise VacationPermissionError("X-Employee-No 헤더가 필요합니다.")
        try:
            return int(value)
        except ValueError as exc:
            raise VacationPermissionError("X-Employee-No 헤더는 사원번호여야 합니다.") from exc

    def error_response(self, error: VacationError) -> Response:
        response_status = status.HTTP_400_BAD_REQUEST
        if isinstance(error, VacationPermissionError):
            response_status = status.HTTP_403_FORBIDDEN
        elif isinstance(error, (VacationRequestNotFoundError, VacationTypeNotFoundError)):
            response_status = status.HTTP_404_NOT_FOUND
        return Response({"code": error.code, "detail": str(error)}, status=response_status)


class VacationTypeListView(VacationAPIView):
    def get(self, request: Request) -> Response:
        try:
            self.employee_no(request)
            return Response([type_to_dict(item) for item in self.service.list_types()])
        except VacationError as error:
            return self.error_response(error)


class VacationRequestListCreateView(VacationAPIView):
    def get(self, request: Request) -> Response:
        try:
            employee_no = self.employee_no(request)
            return Response([request_to_dict(item) for item in self.service.list_mine(employee_no)])
        except VacationError as error:
            return self.error_response(error)

    def post(self, request: Request) -> Response:
        serializer = VacationRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            item = self.service.request_vacation(
                RequestVacationCommand(
                    employee_no=self.employee_no(request),
                    type_id=data["type_id"],
                    start=data["start_datetime"],
                    end=data["end_datetime"],
                    use_days=data["use_days"],
                    reason=data.get("reason") or None,
                )
            )
            return Response(request_to_dict(item), status=status.HTTP_201_CREATED)
        except VacationError as error:
            return self.error_response(error)


class ApprovalListView(VacationAPIView):
    def get(self, request: Request) -> Response:
        try:
            employee_no = self.employee_no(request)
            return Response(
                [request_to_dict(item) for item in self.service.list_approvals(employee_no)]
            )
        except VacationError as error:
            return self.error_response(error)


class EmptyActionView(VacationAPIView):
    action = ""

    def post(self, request: Request, request_id: int) -> Response:
        try:
            employee_no = self.employee_no(request)
            item = getattr(self.service, self.action)(request_id, employee_no)
            return Response(request_to_dict(item))
        except VacationError as error:
            return self.error_response(error)


class CancelVacationView(EmptyActionView):
    action = "cancel"


class ApproveVacationView(EmptyActionView):
    action = "approve"


class ReasonActionView(VacationAPIView):
    action = ""

    def post(self, request: Request, request_id: int) -> Response:
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = getattr(self.service, self.action)(
                request_id, self.employee_no(request), serializer.validated_data["reason"]
            )
            return Response(request_to_dict(item))
        except VacationError as error:
            return self.error_response(error)


class RejectVacationView(ReasonActionView):
    action = "reject"


class RecallVacationView(ReasonActionView):
    action = "recall"


class ResubmitVacationView(VacationAPIView):
    def put(self, request: Request, request_id: int) -> Response:
        serializer = VacationRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            item = self.service.resubmit(
                ResubmitVacationCommand(
                    request_id=request_id,
                    employee_no=self.employee_no(request),
                    type_id=data["type_id"],
                    start=data["start_datetime"],
                    end=data["end_datetime"],
                    use_days=data["use_days"],
                    reason=data.get("reason") or None,
                )
            )
            return Response(request_to_dict(item))
        except VacationError as error:
            return self.error_response(error)


class VacationHistoryView(VacationAPIView):
    def get(self, request: Request, request_id: int) -> Response:
        try:
            entries = self.service.history(request_id, self.employee_no(request))
            return Response([history_to_dict(item) for item in entries])
        except VacationError as error:
            return self.error_response(error)
