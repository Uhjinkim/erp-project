from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EmployeeCandidate:
    employee_no: int
    is_active: bool


def validate_employment_dates(
    *,
    tenure_status: str,
    hire_date: date,
    term_date: date | None,
) -> dict[str, str]:
    errors: dict[str, str] = {}
    if term_date is not None and term_date < hire_date:
        errors["term_date"] = "퇴사일은 입사일보다 빠를 수 없습니다."
    elif tenure_status == "퇴사" and term_date is None:
        errors["term_date"] = "퇴사 처리에는 퇴사일이 필요합니다."
    elif tenure_status != "퇴사" and term_date is not None:
        errors["term_date"] = "퇴사 상태가 아닌 사원에게는 퇴사일을 지정할 수 없습니다."
    return errors


def choose_vacation_approver(
    *,
    applicant_no: int,
    department_head: EmployeeCandidate | None,
    hr_approvers: list[EmployeeCandidate],
) -> int | None:
    if (
        department_head is not None
        and department_head.employee_no != applicant_no
        and department_head.is_active
    ):
        return department_head.employee_no

    active_hr_approvers = [candidate for candidate in hr_approvers if candidate.is_active]
    return active_hr_approvers[0].employee_no if len(active_hr_approvers) == 1 else None
