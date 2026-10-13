from collections.abc import Callable
from datetime import date

from workforce.application.ports import EmploymentLifecycleRepository, RetiredEmployeeQuery
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.lifecycle import (
    RetiredEmployee,
    RetiredEmployeeCriteria,
    validate_retired_criteria,
    validate_termination,
)


class EmployeeNotFound(WorkforceRuleViolation):
    pass


class EmploymentLifecycleService:
    """FN-HR-007 퇴사 처리, FN-HR-008 퇴사자 조회.

    HR-005: 퇴사 처리는 상태·퇴사일만 바꾸고 인사이력·역할·부서장·변경 요청 기록은 보존한다.
    """

    def __init__(
        self,
        repository: EmploymentLifecycleRepository,
        retired: RetiredEmployeeQuery,
        today: Callable[[], date],
    ) -> None:
        self.repository = repository
        self.retired = retired
        self.today = today

    def terminate(self, employee_no: int, term_date: date) -> None:
        with self.repository.transaction():
            # 동시 퇴사 처리나 다른 수정과 겹치지 않도록 사원 행을 잠근 뒤 검사한다.
            state = self.repository.lock_employment(employee_no)
            if state is None:
                raise EmployeeNotFound("사원을 찾을 수 없습니다.")
            validate_termination(state, term_date=term_date, today=self.today())
            self.repository.terminate(employee_no, term_date)

    def list_retired(self, criteria: RetiredEmployeeCriteria) -> list[RetiredEmployee]:
        validate_retired_criteria(criteria)
        return self.retired.retired_employees(criteria)
