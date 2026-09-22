from functools import cached_property

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from board.application.dto import CreatePostCommand, UpdatePostCommand, post_to_dict
from board.application.service import BoardService
from board.domain.entities import NoticeCategory, PostType
from board.domain.exceptions import (
    BoardError,
    BoardPermissionError,
    NoticeCategoryNotAllowedError,
    PostNotFoundError,
)
from board.infrastructure.repositories import DjangoPostRepository
from board.infrastructure.workforce_gateways import DjangoWorkforceGateway
from board.presentation.serializers import PostCreateSerializer, PostUpdateSerializer
from workforce.presentation.permissions import request_employee_no


class BoardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @cached_property
    def service(self) -> BoardService:
        return BoardService(
            repository=DjangoPostRepository(),
            workforce=DjangoWorkforceGateway(),
            clock=timezone.now,
        )

    def employee_no(self, request: Request) -> int:
        employee_no = request_employee_no(request)
        if employee_no is None:
            raise BoardPermissionError("인증 사용자와 연결된 사원번호가 없습니다.")
        return employee_no

    def is_admin(self, request: Request) -> bool:
        return bool(request.user.is_superuser)

    def error_response(self, error: BoardError) -> Response:
        response_status = status.HTTP_400_BAD_REQUEST
        if isinstance(error, (BoardPermissionError, NoticeCategoryNotAllowedError)):
            response_status = status.HTTP_403_FORBIDDEN
        elif isinstance(error, PostNotFoundError):
            response_status = status.HTTP_404_NOT_FOUND
        return Response({"code": error.code, "detail": str(error)}, status=response_status)


class PostListCreateView(BoardAPIView):
    def get(self, request: Request) -> Response:
        try:
            employee_no = self.employee_no(request)
            posts = self.service.list_posts(employee_no)
            return Response([post_to_dict(post) for post in posts])
        except BoardError as error:
            return self.error_response(error)

    def post(self, request: Request) -> Response:
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            employee_no = self.employee_no(request)
            notice_category = data.get("notice_category")
            item = self.service.create_post(
                CreatePostCommand(
                    author_employee_no=employee_no,
                    post_type=PostType(data["post_type"]),
                    title=data["title"],
                    content=data["content"],
                    notice_category=NoticeCategory(notice_category) if notice_category else None,
                )
            )
            return Response(post_to_dict(item), status=status.HTTP_201_CREATED)
        except BoardError as error:
            return self.error_response(error)


class PostDetailView(BoardAPIView):
    def get(self, request: Request, post_id: int) -> Response:
        try:
            employee_no = self.employee_no(request)
            item = self.service.get_post(post_id, employee_no)
            return Response(post_to_dict(item))
        except BoardError as error:
            return self.error_response(error)

    def patch(self, request: Request, post_id: int) -> Response:
        serializer = PostUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            employee_no = self.employee_no(request)
            item = self.service.update_post(
                UpdatePostCommand(
                    post_id=post_id,
                    actor_employee_no=employee_no,
                    actor_is_admin=self.is_admin(request),
                    title=data["title"],
                    content=data["content"],
                )
            )
            return Response(post_to_dict(item))
        except BoardError as error:
            return self.error_response(error)

    def delete(self, request: Request, post_id: int) -> Response:
        try:
            employee_no = self.employee_no(request)
            self.service.delete_post(post_id, employee_no, self.is_admin(request))
            return Response(status=status.HTTP_204_NO_CONTENT)
        except BoardError as error:
            return self.error_response(error)
