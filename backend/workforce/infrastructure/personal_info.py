from contextlib import AbstractContextManager

from django.db import transaction

from workforce.domain.personal_info import (
    ApprovalRequiredValues,
    ChangeRequestStatus,
    PersonalInfoChangeRequest,
)
from workforce.infrastructure.models import Employee
from workforce.infrastructure.models import (
    PersonalInfoChangeRequest as PersonalInfoChangeRequestModel,
)


class DjangoPersonalInfoRepository:
    def transaction(self) -> AbstractContextManager[None]:
        return transaction.atomic()

    def lock_employee(self, employee_no: int) -> None:
        list(Employee.objects.select_for_update().filter(employee_no=employee_no).values("pk"))

    def is_active_employee(self, employee_no: int) -> bool:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        return employee is not None and employee.is_active_employee

    def current_values(self, employee_no: int) -> ApprovalRequiredValues | None:
        employee = Employee.objects.filter(employee_no=employee_no).first()
        if employee is None:
            return None
        return ApprovalRequiredValues(
            email=employee.email,
            bank_code=employee.bank_code,
            account_no=employee.account_no,
        )

    def email_in_use(self, email: str, *, exclude_employee_no: int) -> bool:
        from accounts.models import User

        # 사내 이메일은 로그인 ID로도 쓰이므로 다른 사원 이메일과 다른 계정 로그인 이메일을
        # 모두 검사한다.
        return (
            Employee.objects.filter(email__iexact=email)
            .exclude(employee_no=exclude_employee_no)
            .exists()
            or User.objects.filter(email__iexact=email)
            .exclude(employee_id=exclude_employee_no)
            .exists()
        )

    def has_pending_request(self, employee_no: int) -> bool:
        return PersonalInfoChangeRequestModel.objects.filter(
            employee_id=employee_no,
            status=ChangeRequestStatus.PENDING,
        ).exists()

    def update_contact(self, employee_no: int, changes: dict[str, str | None]) -> None:
        Employee.objects.filter(employee_no=employee_no).update(**changes)

    def apply_values(self, employee_no: int, values: ApprovalRequiredValues) -> None:
        changes = {name: getattr(values, name) for name in values.changed_fields()}
        employee = Employee.objects.select_for_update().get(employee_no=employee_no)
        for name, value in changes.items():
            setattr(employee, name, value)
        employee.save(update_fields=list(changes))

    def update_login_email(self, employee_no: int, email: str) -> None:
        from accounts.models import User

        User.objects.filter(employee_id=employee_no).update(email=email)

    def add_request(self, request: PersonalInfoChangeRequest) -> PersonalInfoChangeRequest:
        model = PersonalInfoChangeRequestModel(employee_id=request.employee_no)
        self._copy_to_model(request, model)
        model.save()
        request.request_id = model.request_id
        return request

    def get_request(
        self, request_id: int, *, for_update: bool = False
    ) -> PersonalInfoChangeRequest | None:
        queryset = PersonalInfoChangeRequestModel.objects.all()
        if for_update:
            queryset = queryset.select_for_update()
        model = queryset.filter(request_id=request_id).first()
        return self._to_domain(model) if model is not None else None

    def save_request(self, request: PersonalInfoChangeRequest) -> None:
        model = PersonalInfoChangeRequestModel.objects.get(request_id=request.request_id)
        self._copy_to_model(request, model)
        model.save()

    def list_requests(
        self, *, employee_no: int | None, status: ChangeRequestStatus | None
    ) -> list[PersonalInfoChangeRequest]:
        queryset = PersonalInfoChangeRequestModel.objects.all()
        if employee_no is not None:
            queryset = queryset.filter(employee_id=employee_no)
        if status is not None:
            queryset = queryset.filter(status=status)
        return [self._to_domain(model) for model in queryset]

    @staticmethod
    def _copy_to_model(
        request: PersonalInfoChangeRequest,
        model: PersonalInfoChangeRequestModel,
    ) -> None:
        model.previous_email = request.previous.email
        model.previous_bank_code = request.previous.bank_code
        model.previous_account_no = request.previous.account_no
        model.requested_email = request.requested.email
        model.requested_bank_code = request.requested.bank_code
        model.requested_account_no = request.requested.account_no
        model.status = request.status
        model.requested_at = request.requested_at
        model.processed_by_id = request.processed_by
        model.processed_at = request.processed_at
        model.reject_reason = request.reject_reason

    @staticmethod
    def _to_domain(model: PersonalInfoChangeRequestModel) -> PersonalInfoChangeRequest:
        return PersonalInfoChangeRequest(
            request_id=model.request_id,
            employee_no=model.employee_id,
            previous=ApprovalRequiredValues(
                email=model.previous_email,
                bank_code=model.previous_bank_code,
                account_no=model.previous_account_no,
            ),
            requested=ApprovalRequiredValues(
                email=model.requested_email,
                bank_code=model.requested_bank_code,
                account_no=model.requested_account_no,
            ),
            status=ChangeRequestStatus(model.status),
            requested_at=model.requested_at,
            processed_by=model.processed_by_id,
            processed_at=model.processed_at,
            reject_reason=model.reject_reason,
        )
