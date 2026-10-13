from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from workforce.application.lifecycle import EmployeeNotFound
from workforce.application.ports import EmploymentHistoryRepository
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.history import HistoryEntry, plan_transfer


@dataclass(frozen=True)
class TransferCommand:
    employee_no: int
    start_date: date
    dept_no: int
    position_code: str
    base_salary: Decimal
    previous_base_salary: Decimal | None = None


@dataclass(frozen=True)
class TransferResult:
    history: list[HistoryEntry]
    released_head_dept_nos: list[int]


class EmploymentHistoryService:
    """FN-HR-010 인사이력 조회와 발령(부서·직급 변경) 등록.

    HR-001: 인사이력은 본인 조회 범위에 넣지 않으며 인사관리자만 조회·등록한다(표현 계층 권한).
    """

    def __init__(
        self, repository: EmploymentHistoryRepository, today: Callable[[], date]
    ) -> None:
        self.repository = repository
        self.today = today

    def history(self, employee_no: int) -> list[HistoryEntry]:
        if not self.repository.employee_exists(employee_no):
            raise EmployeeNotFound("사원을 찾을 수 없습니다.")
        return self.repository.history(employee_no)

    def transfer(self, command: TransferCommand) -> TransferResult:
        repository = self.repository
        with repository.transaction():
            # 동시 발령으로 이력이 엇갈리지 않도록 사원 행을 잠근 뒤 계획한다.
            target = repository.lock_transfer_target(command.employee_no)
            if target is None:
                raise EmployeeNotFound("사원을 찾을 수 없습니다.")
            if not repository.department_exists(command.dept_no):
                raise WorkforceRuleViolation("존재하지 않는 부서입니다.", field="dept_no")
            if not repository.position_exists(command.position_code):
                raise WorkforceRuleViolation("존재하지 않는 직급입니다.", field="position_code")
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
            repository.add_history(command.employee_no, plan.new)
            repository.update_current_assignment(
                command.employee_no, dept_no=command.dept_no, position_code=command.position_code
            )
            released: list[int] = []
            if target.dept_no != command.dept_no:
                # 부서장은 소속 부서의 재직자여야 하므로 다른 부서로 가면 지정을 해제한다.
                released = repository.release_department_heads(
                    command.employee_no, keep_dept_no=command.dept_no
                )
            return TransferResult(repository.history(command.employee_no), released)
