from functools import cached_property

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from payroll.application.dto import (
    CancelConfirmationCommand,
    ConfirmCommand,
    CreateStatementCommand,
    PayrollItemInput,
    UpdateItemsCommand,
    component_to_dict,
    history_to_dict,
    statement_to_dict,
)
from payroll.application.service import PayrollService
from payroll.domain.exceptions import (
    PayrollComponentNotFoundError,
    PayrollError,
    PayrollPermissionError,
    PayrollStatementNotFoundError,
)
from payroll.infrastructure.gateways import DjangoHolidayGateway, DjangoWorkforceGateway
from payroll.infrastructure.repositories import DjangoPayrollUnitOfWork
from payroll.presentation.permissions import IsPayrollManager
from payroll.presentation.serializers import (
    CreateStatementSerializer,
    ReasonSerializer,
    UpdateItemsSerializer,
)
from workforce.presentation.permissions import request_employee_no


class PayrollAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self) -> PayrollService:
        return PayrollService(
            unit_of_work_factory=DjangoPayrollUnitOfWork,
            workforce=DjangoWorkforceGateway(),
            holidays=DjangoHolidayGateway(),
            clock=timezone.now,
        )

    def employee_no(self, request: Request) -> int:
        employee_no = request_employee_no(request)
        if employee_no is None:
            raise PayrollPermissionError("요청 사용자와 연결된 사원번호가 없습니다.")
        return employee_no

    def error_response(self, error: PayrollError) -> Response:
        response_status = status.HTTP_400_BAD_REQUEST
        if isinstance(error, PayrollPermissionError):
            response_status = status.HTTP_403_FORBIDDEN
        elif isinstance(error, (PayrollStatementNotFoundError, PayrollComponentNotFoundError)):
            response_status = status.HTTP_404_NOT_FOUND
        return Response({"code": error.code, "detail": str(error)}, status=response_status)


class StatementListCreateView(PayrollAPIView):
    permission_classes_by_method = {"POST": [IsAuthenticated, IsPayrollManager]}

    def get_permissions(self):
        classes = self.permission_classes_by_method.get(
            self.request.method, self.permission_classes
        )
        return [permission() for permission in classes]

    def get(self, request: Request) -> Response:
        try:
            employee_no = self.employee_no(request)
            emp_no_param = request.query_params.get("emp_no")
            if emp_no_param is not None:
                if not emp_no_param.isdigit():
                    return Response(
                        {"code": "invalid_query", "detail": "emp_no는 숫자여야 합니다."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                items = self.service.list_for_employee(int(emp_no_param), employee_no)
            elif request.query_params.get("all") == "true":
                items = self.service.list_for_employee(None, employee_no)
            else:
                items = self.service.list_mine(employee_no)
            return Response([statement_to_dict(item) for item in items])
        except PayrollError as error:
            return self.error_response(error)

    def post(self, request: Request) -> Response:
        serializer = CreateStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            item = self.service.create_statement(
                CreateStatementCommand(
                    actor_employee_no=self.employee_no(request),
                    employee_no=data["emp_no"],
                    year=data["year"],
                    month=data["month"],
                )
            )
            return Response(statement_to_dict(item), status=status.HTTP_201_CREATED)
        except PayrollError as error:
            return self.error_response(error)


class StatementDetailView(PayrollAPIView):
    def get(self, request: Request, statement_id: int) -> Response:
        try:
            item = self.service.get(statement_id, self.employee_no(request))
            return Response(statement_to_dict(item))
        except PayrollError as error:
            return self.error_response(error)


class ItemsUpdateView(PayrollAPIView):
    permission_classes = [IsAuthenticated, IsPayrollManager]

    def put(self, request: Request, statement_id: int) -> Response:
        serializer = UpdateItemsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items = [
            PayrollItemInput(component_code=entry["component_code"], amount=entry["amount"])
            for entry in serializer.validated_data["items"]
        ]
        try:
            item = self.service.update_items(
                UpdateItemsCommand(
                    actor_employee_no=self.employee_no(request),
                    statement_id=statement_id,
                    items=items,
                )
            )
            return Response(statement_to_dict(item))
        except PayrollError as error:
            return self.error_response(error)


class ConfirmView(PayrollAPIView):
    permission_classes = [IsAuthenticated, IsPayrollManager]

    def post(self, request: Request, statement_id: int) -> Response:
        try:
            item = self.service.confirm(
                ConfirmCommand(
                    actor_employee_no=self.employee_no(request), statement_id=statement_id
                )
            )
            return Response(statement_to_dict(item))
        except PayrollError as error:
            return self.error_response(error)


class CancelConfirmationView(PayrollAPIView):
    permission_classes = [IsAuthenticated, IsPayrollManager]

    def post(self, request: Request, statement_id: int) -> Response:
        serializer = ReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item = self.service.cancel_confirmation(
                CancelConfirmationCommand(
                    actor_employee_no=self.employee_no(request),
                    statement_id=statement_id,
                    reason=serializer.validated_data["reason"],
                )
            )
            return Response(statement_to_dict(item))
        except PayrollError as error:
            return self.error_response(error)


class HistoryView(PayrollAPIView):
    def get(self, request: Request, statement_id: int) -> Response:
        try:
            entries = self.service.history(statement_id, self.employee_no(request))
            return Response([history_to_dict(item) for item in entries])
        except PayrollError as error:
            return self.error_response(error)


class ComponentListView(PayrollAPIView):
    def get(self, request: Request) -> Response:
        return Response([component_to_dict(item) for item in self.service.list_components()])
