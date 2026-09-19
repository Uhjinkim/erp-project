from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.serializers import AccountSerializer, CurrentUserSerializer, LoginSerializer
from workforce.presentation.permissions import IsHRManager


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"detail": "CSRF 쿠키가 설정되었습니다."})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        request.session.set_expiry(8 * 60 * 60)
        return Response(CurrentUserSerializer(user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = User.objects.select_related(
            "employee__person",
            "employee__department",
            "employee__position",
        ).get(pk=request.user.pk)
        return Response(CurrentUserSerializer(user).data)


class AccountViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("employee").order_by("email")
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, IsHRManager]
