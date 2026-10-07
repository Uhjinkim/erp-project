from collections.abc import Callable
from functools import cached_property

from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from evaluation.application.dto import (
    CreateEvaluationCommand,
    ReassignEvaluationCommand,
    ReviseEvaluationCommand,
    evaluation_to_dict,
    history_to_dict,
)
from evaluation.application.service import EvaluationService
from evaluation.domain.entities import Evaluation
from evaluation.domain.exceptions import (
    DuplicateEvaluationError,
    EvaluationConflictError,
    EvaluationError,
    EvaluationNotFoundError,
    EvaluationPermissionError,
    EvaluationStateError,
    InactiveEmployeeError,
)
from evaluation.infrastructure.repositories import DjangoEvaluationUnitOfWork
from evaluation.infrastructure.workforce_gateways import DjangoWorkforceGateway
from evaluation.presentation.serializers import (
    EvaluationCreateSerializer,
    EvaluationListQuerySerializer,
    EvaluationUpdateSerializer,
    OptionalReasonSerializer,
    ReasonSerializer,
    ReassignSerializer,
)
from workforce.presentation.permissions import request_employee_no


class EvaluationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self) -> EvaluationService:
        return EvaluationService(
            unit_of_work_factory=DjangoEvaluationUnitOfWork,
            workforce=DjangoWorkforceGateway(),
            clock=timezone.now,
            today=timezone.localdate,
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
        elif isinstance(error, EvaluationNotFoundError):
            response_status = status.HTTP_404_NOT_FOUND
        elif isinstance(
            error, (DuplicateEvaluationError, EvaluationStateError, EvaluationConflictError)
        ):
            response_status = status.HTTP_409_CONFLICT
        return Response({"code": error.code, "detail": str(error)}, status=response_status)

    def run(self, action: Callable[[], Evaluation], success_status: int = 200) -> Response:
        try:
            return Response(evaluation_to_dict(action()), status=success_status)
        except EvaluationError as error:
            return self.error_response(error)

    @staticmethod
    def validated(serializer_class: type[serializers.Serializer], request: Request) -> dict:
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return dict(serializer.validated_data)


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
        data = self.validated(EvaluationCreateSerializer, request)
        return self.run(
            lambda: self.service.create_evaluation(
                CreateEvaluationCommand(
                    evaluator_no=self.employee_no(request),
                    employee_no=data["emp_no"],
                    eval_year=data["eval_year"],
                    score=data["score"],
                    comments=data["comments"],
                )
            ),
            status.HTTP_201_CREATED,
        )


class EvaluationDetailView(EvaluationAPIView):
    def get(self, request: Request, eval_id: int) -> Response:
        return self.run(lambda: self.service.get_evaluation(eval_id, self.employee_no(request)))

    def patch(self, request: Request, eval_id: int) -> Response:
        data = self.validated(EvaluationUpdateSerializer, request)
        return self.run(
            lambda: self.service.revise_evaluation(
                ReviseEvaluationCommand(
                    eval_id=eval_id,
                    actor_no=self.employee_no(request),
                    score=data["score"],
                    comments=data.get("comments"),
                )
            )
        )


class EvaluationHistoryView(EvaluationAPIView):
    def get(self, request: Request, eval_id: int) -> Response:
        try:
            entries = self.service.list_history(eval_id, self.employee_no(request))
            return Response([history_to_dict(entry) for entry in entries])
        except EvaluationError as error:
            return self.error_response(error)


class EvaluationSubmitView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        return self.run(
            lambda: self.service.submit_evaluation(eval_id, self.employee_no(request))
        )


class EvaluationReturnView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        data = self.validated(ReasonSerializer, request)
        return self.run(
            lambda: self.service.return_evaluation(
                eval_id, self.employee_no(request), data["reason"]
            )
        )


class EvaluationReassignView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        data = self.validated(ReassignSerializer, request)
        return self.run(
            lambda: self.service.reassign_evaluation(
                ReassignEvaluationCommand(
                    eval_id=eval_id,
                    actor_no=self.employee_no(request),
                    new_evaluator_no=data["evaluator_no"],
                    reason=data["reason"],
                )
            )
        )


class EvaluationConfirmView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        return self.run(
            lambda: self.service.confirm_evaluation(eval_id, self.employee_no(request))
        )


class EvaluationCancelConfirmationView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        data = self.validated(ReasonSerializer, request)
        return self.run(
            lambda: self.service.cancel_confirmation(
                eval_id, self.employee_no(request), data["reason"]
            )
        )


class EvaluationExcludeView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        data = self.validated(ReasonSerializer, request)
        return self.run(
            lambda: self.service.exclude_evaluation(
                eval_id, self.employee_no(request), data["reason"]
            )
        )


class EvaluationCancelExclusionView(EvaluationAPIView):
    def post(self, request: Request, eval_id: int) -> Response:
        data = self.validated(OptionalReasonSerializer, request)
        return self.run(
            lambda: self.service.cancel_exclusion(
                eval_id, self.employee_no(request), data["reason"]
            )
        )
