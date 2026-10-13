from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from workforce.application.lifecycle import EmployeeNotFound
from workforce.application.ports import EmploymentHistoryRepository
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.history import (
    HistoryChange,
    HistoryChangeAction,
    HistoryEntry,
    TransferTarget,
    plan_cancellation,
    plan_correction,
    plan_transfer,
    require_reason,
)

ACTIVE = "재직"


@dataclass(frozen=True)
class TransferCommand:
    employee_no: int
    start_date: date
    dept_no: int
    position_code: str
    base_salary: Decimal
    previous_base_salary: Decimal | None = None
    reason: str | None = None
    changed_by: int | None = None


@dataclass(frozen=True)
class CorrectionCommand:
    employee_no: int
    history_id: int
    start_date: date
    dept_no: int
    position_code: str
    base_salary: Decimal
    reason: str
    changed_by: int | None = None


@dataclass(frozen=True)
class CancellationCommand:
    employee_no: int
    history_id: int
    reason: str
    changed_by: int | None = None


@dataclass(frozen=True)
class TransferResult:
    history: list[HistoryEntry]
    released_head_dept_nos: list[int]
    restored_head_dept_nos: list[int]


class EmploymentHistoryService:
    """FN-HR-010 인사이력 조회, 발령 등록, 최근 이력 정정·취소.

    HR-001: 인사이력은 본인 조회 범위에 넣지 않으며 인사관리자만 조회·등록한다(표현 계층 권한).
    발령·정정·취소는 모두 기록하고, 정정·취소는 사유가 필수다.
    """

    def __init__(
        self, repository: EmploymentHistoryRepository, today: Callable[[], date]
    ) -> None:
        self.repository = repository
        self.today = today

    def history(self, employee_no: int) -> list[HistoryEntry]:
        self._ensure_employee(employee_no)
        return self.repository.history(employee_no)

    def changes(self, employee_no: int) -> list[HistoryChange]:
        self._ensure_employee(employee_no)
        return self.repository.changes(employee_no)

    def transfer(self, command: TransferCommand) -> TransferResult:
        repository = self.repository
        reason = (command.reason or "").strip() or None
        with repository.transaction():
            # 동시 발령으로 이력이 엇갈리지 않도록 사원 행을 잠근 뒤 계획한다.
            target = self._lock(command.employee_no)
            self._ensure_references(command.dept_no, command.position_code)
            plan = plan_transfer(
                target,
                repository.history(command.employee_no),
                start_date=command.start_date,
                dept_no=command.dept_no,
                position_code=command.position_code,
                base_salary=command.base_salary,
                previous_base_salary=command.previous_base_salary,
                today=self.today(),
            )

            # 배타 제약이 문장마다 검사되므로 마감을 먼저 반영한 뒤 새 기간을 추가한다.
            if plan.close is not None:
                repository.close_history(*plan.close)
            if plan.baseline is not None:
                repository.add_history(command.employee_no, plan.baseline)
            new_id = repository.add_history(command.employee_no, plan.new)
            repository.update_current_assignment(
                command.employee_no, dept_no=command.dept_no, position_code=command.position_code
            )
            released = self._release_heads(target, command.dept_no)
            # 취소 시 부서장을 복원할 수 있도록 해제 내역도 함께 기록한다.
            repository.record_change(
                HistoryChange(
                    employee_no=command.employee_no,
                    history_id=new_id,
                    action=HistoryChangeAction.TRANSFER,
                    before=None,
                    after=plan.new,
                    reason=reason,
                    changed_by=command.changed_by,
                    released_head_dept_nos=tuple(released),
                )
            )
            return TransferResult(repository.history(command.employee_no), released, [])

    def correct(self, command: CorrectionCommand) -> TransferResult:
        repository = self.repository
        reason = require_reason(command.reason)
        with repository.transaction():
            target = self._lock(command.employee_no)
            self._ensure_references(command.dept_no, command.position_code)
            history = repository.history(command.employee_no)
            plan = plan_correction(
                target,
                history,
                history_id=command.history_id,
                start_date=command.start_date,
                dept_no=command.dept_no,
                position_code=command.position_code,
                base_salary=command.base_salary,
                today=self.today(),
            )
            before = next(item for item in history if item.history_id == command.history_id)

            # 발령일을 앞당기면 직전 이력을 먼저 줄이고, 늦추면 최근 이력을 먼저 옮겨
            # 문장마다 검사되는 배타 제약에 걸리지 않게 한다.
            moves_earlier = plan.corrected.start_date < before.start_date
            if plan.previous_end is not None and moves_earlier:
                repository.close_history(*plan.previous_end)
            repository.update_history(plan.corrected)
            if plan.previous_end is not None and not moves_earlier:
                repository.close_history(*plan.previous_end)

            repository.update_current_assignment(
                command.employee_no, dept_no=command.dept_no, position_code=command.position_code
            )
            released = self._release_heads(target, command.dept_no)
            repository.record_change(
                HistoryChange(
                    employee_no=command.employee_no,
                    history_id=command.history_id,
                    action=HistoryChangeAction.CORRECTION,
                    before=before,
                    after=plan.corrected,
                    reason=reason,
                    changed_by=command.changed_by,
                    released_head_dept_nos=tuple(released),
                )
            )
            return TransferResult(repository.history(command.employee_no), released, [])

    def cancel(self, command: CancellationCommand) -> TransferResult:
        repository = self.repository
        reason = require_reason(command.reason)
        with repository.transaction():
            target = self._lock(command.employee_no)
            plan = plan_cancellation(
                target, repository.history(command.employee_no), history_id=command.history_id
            )
            repository.delete_history(plan.cancelled.history_id)
            repository.close_history(plan.reopened.history_id, None)
            repository.update_current_assignment(
                command.employee_no,
                dept_no=plan.reopened.dept_no,
                position_code=plan.reopened.position_code,
            )

            # 이 발령으로 해제했던 부서장은 그 자리가 아직 비어 있고 되돌아간 소속 부서일
            # 때만 복원한다(부서장은 그 부서 소속 재직자여야 한다).
            restored: list[int] = []
            if target.tenure_status == ACTIVE:
                candidates = [
                    dept_no
                    for dept_no in repository.released_heads_for(
                        command.employee_no, command.history_id
                    )
                    if dept_no == plan.reopened.dept_no
                ]
                restored = repository.restore_department_heads(command.employee_no, candidates)
            repository.record_change(
                HistoryChange(
                    employee_no=command.employee_no,
                    history_id=command.history_id,
                    action=HistoryChangeAction.CANCELLATION,
                    before=plan.cancelled,
                    after=None,
                    reason=reason,
                    changed_by=command.changed_by,
                    restored_head_dept_nos=tuple(restored),
                )
            )
            return TransferResult(repository.history(command.employee_no), [], restored)

    def _ensure_employee(self, employee_no: int) -> None:
        if not self.repository.employee_exists(employee_no):
            raise EmployeeNotFound("사원을 찾을 수 없습니다.")

    def _lock(self, employee_no: int) -> TransferTarget:
        target = self.repository.lock_transfer_target(employee_no)
        if target is None:
            raise EmployeeNotFound("사원을 찾을 수 없습니다.")
        return target

    def _ensure_references(self, dept_no: int, position_code: str) -> None:
        if not self.repository.department_exists(dept_no):
            raise WorkforceRuleViolation("존재하지 않는 부서입니다.", field="dept_no")
        if not self.repository.position_exists(position_code):
            raise WorkforceRuleViolation("존재하지 않는 직급입니다.", field="position_code")

    def _release_heads(self, target: TransferTarget, dept_no: int) -> list[int]:
        # 부서장은 소속 부서의 재직자여야 하므로 다른 부서로 가면 지정을 해제한다.
        if target.dept_no == dept_no:
            return []
        return self.repository.release_department_heads(target.employee_no, keep_dept_no=dept_no)
