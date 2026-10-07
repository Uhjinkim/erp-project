from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from workforce.application.ports import PersonalInfoRepository, WorkforceQueryGateway
from workforce.application.services import HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.personal_info import (
    ApprovalRequiredValues,
    ChangeRequestStatus,
    PersonalInfoChangeRequest,
    ProcessorAssignment,
    resolve_change_request_processor,
    validate_change_request_values,
    validate_self_editable_fields,
)


class RequestNotFound(WorkforceRuleViolation):
    pass


class ProcessingNotAllowed(WorkforceRuleViolation):
    pass


@dataclass(frozen=True)
class Actor:
    employee_no: int | None
    is_hr_manager: bool = False
    is_superuser: bool = False


class PersonalInfoService:
    """HR-002/HR-003 개인정보 직접 수정과 승인형 변경 요청 유스케이스."""

    def __init__(
        self,
        repository: PersonalInfoRepository,
        workforce: WorkforceQueryGateway,
        clock: Callable[[], datetime],
    ) -> None:
        self.repository = repository
        self.workforce = workforce
        self.clock = clock
        self._processor_cache: dict[int, ProcessorAssignment] = {}

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
            # 동시 요청으로 대기 요청이 2건 생기지 않도록 사원 행을 잠근 뒤 검사한다.
            self.repository.lock_employee(employee_no)
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
                    previous=current.masked(),
                    requested=requested,
                    status=ChangeRequestStatus.PENDING,
                    requested_at=self.clock(),
                )
            )

    def approve(self, request_id: int, actor: Actor) -> PersonalInfoChangeRequest:
        """FN-HR-004: 승인 시 요청값을 실제 인사정보에 반영한다."""
        with self.repository.transaction():
            request = self._get_for_processing(request_id, actor)
            values = request.approve(actor.employee_no, self.clock())
            # HR-004: 요청 후 퇴사·휴직한 사원의 값은 반영하지 않는다(반려로 처리).
            self._ensure_active(request.employee_no)
            self._ensure_email_available(values.email, request.employee_no)
            self.repository.apply_values(request.employee_no, values)
            if values.email is not None:
                # 로그인 ID는 사내 이메일을 따른다: 승인된 이메일로 바로 로그인할 수 있게 한다.
                self.repository.update_login_email(request.employee_no, values.email)
            self.repository.save_request(request)
            return request

    def reject(
        self,
        request_id: int,
        actor: Actor,
        reason: str | None,
    ) -> PersonalInfoChangeRequest:
        """FN-HR-004: 반려 시 기존 값을 유지하고 처리 결과만 기록한다."""
        with self.repository.transaction():
            request = self._get_for_processing(request_id, actor)
            request.reject(actor.employee_no, self.clock(), reason)
            self.repository.save_request(request)
            return request

    def cancel(self, request_id: int, actor: Actor) -> PersonalInfoChangeRequest:
        """FN-HR-011: 요청자가 대기 요청을 취소한다."""
        with self.repository.transaction():
            request = self.repository.get_request(request_id, for_update=True)
            if request is None or not self._can_view(request, actor):
                raise RequestNotFound("변경 요청을 찾을 수 없습니다.")
            request.cancel(actor.employee_no, self.clock())
            self.repository.save_request(request)
            return request

    def can_process(self, request: PersonalInfoChangeRequest, actor: Actor) -> bool:
        return request.status == ChangeRequestStatus.PENDING and self._allows(request, actor)

    def get(self, request_id: int, actor: Actor) -> PersonalInfoChangeRequest:
        """FN-HR-005: 요청자, 인사관리자, 현재 처리자만 결과·이력을 조회한다."""
        request = self.repository.get_request(request_id)
        if request is None or not self._can_view(request, actor):
            raise RequestNotFound("변경 요청을 찾을 수 없습니다.")
        return request

    def list_requests(
        self,
        actor: Actor,
        *,
        status: ChangeRequestStatus | None = None,
        processable_only: bool = False,
        mine_only: bool = False,
    ) -> list[PersonalInfoChangeRequest]:
        """FN-HR-005: 인사관리자는 전체, 사원은 본인 요청과 처리 대상 요청만 조회한다."""
        if processable_only:
            pending = self.repository.list_requests(
                employee_no=None, status=ChangeRequestStatus.PENDING
            )
            return [request for request in pending if self.can_process(request, actor)]
        if (actor.is_hr_manager or actor.is_superuser) and not mine_only:
            return self.repository.list_requests(employee_no=None, status=status)
        if actor.employee_no is None:
            return []
        return self.repository.list_requests(employee_no=actor.employee_no, status=status)

    def _can_view(self, request: PersonalInfoChangeRequest, actor: Actor) -> bool:
        return (
            actor.is_hr_manager
            or actor.is_superuser
            or request.employee_no == actor.employee_no
            or self.can_process(request, actor)
        )

    def _allows(self, request: PersonalInfoChangeRequest, actor: Actor) -> bool:
        return self._processor_for(request.employee_no).allows(
            actor_employee_no=actor.employee_no,
            actor_is_hr_manager=actor.is_hr_manager,
            actor_is_superuser=actor.is_superuser,
        )

    def _processor_for(self, requester_no: int) -> ProcessorAssignment:
        # 서비스는 HTTP 요청마다 생성되므로, 같은 요청 안에서만 요청자별 판정을 재사용한다.
        if requester_no not in self._processor_cache:
            self._processor_cache[requester_no] = self._resolve_processor(requester_no)
        return self._processor_cache[requester_no]

    def _resolve_processor(self, requester_no: int) -> ProcessorAssignment:
        if not self.workforce.has_active_role(requester_no, HR_MANAGER_ROLE):
            return resolve_change_request_processor(
                requester_is_hr_manager=False, department_head=None
            )
        head = self.workforce.department_head(requester_no)
        return resolve_change_request_processor(
            requester_is_hr_manager=True,
            department_head=head,
            department_head_is_hr_manager=head is not None
            and self.workforce.has_active_role(head.employee_no, HR_MANAGER_ROLE),
        )

    def _get_for_processing(self, request_id: int, actor: Actor) -> PersonalInfoChangeRequest:
        request = self.repository.get_request(request_id, for_update=True)
        if request is None or not self._can_view(request, actor):
            raise RequestNotFound("변경 요청을 찾을 수 없습니다.")
        if not self._allows(request, actor):
            raise ProcessingNotAllowed("이 변경 요청을 처리할 권한이 없습니다.")
        return request

    def _ensure_active(self, employee_no: int) -> None:
        if not self.repository.is_active_employee(employee_no):
            raise WorkforceRuleViolation("재직 중인 사원만 개인정보를 변경할 수 있습니다.")

    def _ensure_email_available(self, email: str | None, employee_no: int) -> None:
        if email is not None and self.repository.email_in_use(
            email, exclude_employee_no=employee_no
        ):
            raise WorkforceRuleViolation("이미 사용 중인 이메일입니다.", field="email")
