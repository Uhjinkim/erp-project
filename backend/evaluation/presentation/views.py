from functools import cached_property

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from evaluation.application.dto import (
    CreateEvaluationCommand,
    ReviseEvaluationCommand,
    evaluation_to_dict,
)
from evaluation.application.service import EvaluationService
from evaluation.domain.exceptions import (
    DuplicateEvaluationError,
    EmployeeNotFoundError,
    EvaluationError,
    EvaluationNotFoundError,
    EvaluationPermissionError,
    EvaluationStateError,
    InactiveEmployeeError,
)
from evaluation.infrastructure.repositories import DjangoEvaluationRepository
from evaluation.infrastructure.workforce_gateways import DjangoWorkforceGateway
from evaluation.presentation.serializers import (
    EvaluationCreateSerializer,
    EvaluationListQuerySerializer,
    EvaluationUpdateSerializer,
)
from workforce.presentation.permissions import request_employee_no


class EvaluationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self) -> EvaluationService:
        return EvaluationService(
            repository=DjangoEvaluationRepository(),
            workforce=DjangoWorkforceGateway(),
            clock=timezone.now,
        )

    def employee_no(self, request: Request) -> int:
        employee_no = request_employee_no(request)
        if employee_no is None:
            raise EvaluationPermissionError("인증 사용자와 연결된 사원번호가 없습니다.")
        return employee_no

    def error_response(self, error: EvaluationError) -> Response:
        response_status = status.HTTP_400_BAD_REQUEST
        if isinstance(error, (EvaluationPermissionError, InactiveEmployeeError)):
            response_status = status.HTTP_403_FORBIDDEN
        elif isinstance(error, (EvaluationNotFoundError, EmployeeNotFoundError)):
            response_status = status.HTTP_404_NOT_FOUND
        elif isinstance(error, (DuplicateEvaluationError, EvaluationStateError)):
            response_status = status.HTTP_409_CONFLICT
        return Response({"code": error.code, "detail": str(error)}, status=response_status)


class EvaluationListCreateView(EvaluationAPIView):
    def get(self, request: Request) -> Response:
        query = EvaluationListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        try:
            evaluations = self.service.list_evaluations(
                self.employee_no(request),
                query.validated_data.get("year"),
            )
            return Response([evaluation_to_dict(item) for item in evaluations])
        except EvaluationError as error:
            return self.error_response(error)

    def post(self, request: Request) -> Response:
        serializer = EvaluationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            item = self.service.create_evaluation(
                CreateEvaluationCommand(
                    evaluator_no=self.employee_no(request),
                    employee_no=data["emp_no"],
                    eval_year=data["eval_year"],
                    score=data["score"],
                    comments=data["comments"],
                )
            )
            return Response(evaluation_to_dict(item), status=status.HTTP_201_CREATED)
        except EvaluationError as error:
            return self.error_response(error)


class EvaluationDetailView(EvaluationAPIView):
    def get(self, request: Request, eval_id: int) -> Response:
        try:
            item = self.service.get_evaluation(eval_id, self.employee_no(request))
            return Response(evaluation_to_dict(item))
        except EvaluationError as error:
            return self.error_response(error)

    def patch(self, request: Request, eval_id: int) -> Response:
        serializer = EvaluationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            item = self.service.revise_evaluation(
                ReviseEvaluationCommand(
                    eval_id=eval_id,
                    actor_no=self.employee_no(request),
                    score=data["score"],
                    comments=data["comments"],
                )
            )
            return Response(evaluation_to_dict(item))
        except EvaluationError as error:
            return self.error_response(error)


class EvaluationConfirmView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        try:
            item = self.service.confirm_evaluation(eval_id, self.employee_no(request))
            return Response(evaluation_to_dict(item))
        except EvaluationError as error:
            return self.error_response(error)
