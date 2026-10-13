from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from workforce.application.onboarding import AccountCreationFailed


class DjangoAccountGateway:
    """accounts 컨텍스트의 로그인 계정을 만드는 infrastructure gateway."""

    def email_in_use(self, email: str) -> bool:
        from accounts.models import User

        return User.objects.filter(email__iexact=email).exists()

    def create_account(self, *, email: str, password: str, employee_no: int) -> int:
        from accounts.models import User

        try:
            # 프로젝트 AUTH_PASSWORD_VALIDATORS를 적용한다.
            validate_password(password, User(email=email))
        except ValidationError as exc:
            raise AccountCreationFailed(
                " ".join(exc.messages), field="account.password"
            ) from exc
        # 고유 제약 충돌(IntegrityError)은 단위 작업이 RegistrationConflict로 바꾼다.
        return User.objects.create_user(
            email=email, password=password, employee_id=employee_no
        ).pk
