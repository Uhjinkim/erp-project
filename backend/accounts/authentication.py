from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request


class ActiveEmployeeSessionAuthentication(SessionAuthentication):
    def authenticate(self, request: Request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, auth = result
        employee = getattr(user, "employee", None)
        if employee is not None and not employee.is_active_employee:
            raise AuthenticationFailed("재직 중인 사원만 서비스를 사용할 수 있습니다.")
        return user, auth
