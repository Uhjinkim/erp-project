from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from accounts.infrastructure.workforce_gateway import hydrate_session_employee


class ActiveEmployeeSessionAuthentication(SessionAuthentication):
    def authenticate(self, request: Request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, auth = result
        employee = hydrate_session_employee(user)
        if employee is not None and not employee.is_active_employee:
            raise AuthenticationFailed("재직 중인 사원만 서비스를 사용할 수 있습니다.")
        return user, auth
