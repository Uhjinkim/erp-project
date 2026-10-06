from collections.abc import Callable
from datetime import datetime

from workforce.application.ports import PersonalInfoRepository
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.personal_info import (
    ApprovalRequiredValues,
    ChangeRequestStatus,
    PersonalInfoChangeRequest,
    validate_change_request_values,
    validate_self_editable_fields,
)


class RequestNotFound(WorkforceRuleViolation):
    pass


class PersonalInfoService:
    """HR-002/HR-003 개인정보 직접 수정과 승인형 변경 요청 유스케이스."""

    def __init__(
        self,
        repository: PersonalInfoRepository,
        clock: Callable[[], datetime],
    ) -> None:
        self.repository = repository
        self.clock = clock

    def update_own_contact(self, employee_no: int, changes: dict[str, str | None]) -> None:
        """FN-HR-002: 재직 사원이 본인 연락처·주소를 직접 수정한다."""
        validate_self_editable_fields(set(changes))
        self._ensure_active(employee_no)
        self.repository.update_contact(employee_no, changes)

    def submit_change_request(
        self,
        employee_no: int,
        requested: ApprovalRequiredValues,
    ) -> PersonalInfoChangeRequest:
        """FN-HR-003: 사내 이메일·급여계좌 변경을 대기 상태로 기록한다(실제 값은 미변경)."""
        self._ensure_active(employee_no)
        with self.repository.transaction():
            current = self.repository.current_values(employee_no)
            if current is None:
                raise WorkforceRuleViolation("사원 정보를 찾을 수 없습니다.")
            validate_change_request_values(current=current, requested=requested)
            self._ensure_email_available(requested.email, employee_no)
            if self.repository.has_pending_request(employee_no):
                raise WorkforceRuleViolation(
                    "처리 대기 중인 변경 요청이 있습니다. 기존 요청을 취소한 뒤 다시 요청하세요."
                )
            return self.repository.add_request(
                PersonalInfoChangeRequest(
                    request_id=None,
                    employee_no=employee_no,
                    previous=current,
                    requested=requested,
                    status=ChangeRequestStatus.PENDING,
                    requested_at=self.clock(),
                )
            )

    def approve(self, request_id: int, actor_employee_no: int | None) -> PersonalInfoChangeRequest:
        """FN-HR-004: 승인 시 요청값을 실제 인사정보에 반영한다."""
        with self.repository.transaction():
            request = self._get_for_update(request_id)
            request.approve(actor_employee_no, self.clock())
            self._ensure_email_available(request.requested.email, request.employee_no)
            self.repository.apply_values(request.employee_no, request.requested)
            self.repository.save_request(request)
            return request

    def reject(
        self,
        request_id: int,
        actor_employee_no: int | None,
        reason: str | None,
    ) -> PersonalInfoChangeRequest:
        """FN-HR-004: 반려 시 기존 값을 유지하고 처리 결과만 기록한다."""
        with self.repository.transaction():
            request = self._get_for_update(request_id)
            request.reject(actor_employee_no, self.clock(), reason)
            self.repository.save_request(request)
            return request

    def cancel(self, request_id: int, actor_employee_no: int | None) -> PersonalInfoChangeRequest:
        """FN-HR-011: 요청자가 대기 요청을 취소한다."""
        with self.repository.transaction():
            request = self._get_for_update(request_id)
            request.cancel(actor_employee_no, self.clock())
            self.repository.save_request(request)
            return request

    def get(
        self,
        request_id: int,
        *,
        viewer_employee_no: int | None,
        viewer_is_hr_manager: bool,
    ) -> PersonalInfoChangeRequest:
        """FN-HR-005: 요청자 본인 또는 인사관리자만 결과·이력을 조회한다."""
        request = self.repository.get_request(request_id)
        if request is None or not (
            viewer_is_hr_manager or request.employee_no == viewer_employee_no
        ):
            raise RequestNotFound("변경 요청을 찾을 수 없습니다.")
        return request

    def list_requests(
        self,
        *,
        viewer_employee_no: int | None,
        viewer_is_hr_manager: bool,
        status: ChangeRequestStatus | None = None,
    ) -> list[PersonalInfoChangeRequest]:
        """FN-HR-005: 인사관리자는 전체, 사원은 본인 요청만 조회한다."""
        if viewer_is_hr_manager:
            return self.repository.list_requests(employee_no=None, status=status)
        if viewer_employee_no is None:
            return []
        return self.repository.list_requests(employee_no=viewer_employee_no, status=status)

    def _ensure_active(self, employee_no: int) -> None:
        if not self.repository.is_active_employee(employee_no):
            raise WorkforceRuleViolation("재직 중인 사원만 개인정보를 변경할 수 있습니다.")

    def _ensure_email_available(self, email: str | None, employee_no: int) -> None:
        if email is not None and self.repository.email_in_use(
            email, exclude_employee_no=employee_no
        ):
            raise WorkforceRuleViolation("이미 사용 중인 이메일입니다.", field="email")

    def _get_for_update(self, request_id: int) -> PersonalInfoChangeRequest:
        request = self.repository.get_request(request_id, for_update=True)
        if request is None:
            raise RequestNotFound("변경 요청을 찾을 수 없습니다.")
        return request
