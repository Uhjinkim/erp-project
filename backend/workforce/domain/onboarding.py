"""FN-HR-006 신규 입사자 등록 도메인 규칙(HR-008, HR-010).

HR-007 사번은 DB identity 시퀀스가 발급하고 이후 바꾸지 않는다.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from workforce.domain.exceptions import WorkforceRuleViolation

GENDER_CODES = frozenset({"M", "F"})


@dataclass(frozen=True)
class EmploymentPeriod:
    start_date: date
    end_date: date | None = None

    def overlaps(self, other: "EmploymentPeriod") -> bool:
        # 종료일이 없는 기간은 현재까지 이어지는 것으로 보고, 경계일이 같아도 겹친다고 본다.
        self_ends_before = self.end_date is not None and self.end_date < other.start_date
        other_ends_before = other.end_date is not None and other.end_date < self.start_date
        return not (self_ends_before or other_ends_before)


def validate_new_hire(
    *,
    name: str,
    gender: str,
    email: str,
    base_salary: Decimal,
    role_codes: tuple[str, ...],
) -> None:
    """HR-008: 등록 필수값과 코드값을 검증한다. 형식 검증은 표현 계층이 먼저 수행한다."""
    validate_person_values(name=name, gender=gender)
    validate_employment_terms(email=email, base_salary=base_salary, role_codes=role_codes)


def validate_person_values(*, name: str | None, gender: str | None) -> None:
    """HR-008 인적사항 값 검증. None은 값을 바꾸지 않는 재입사 요청에서만 쓴다."""
    if name is not None and not name.strip():
        raise WorkforceRuleViolation("이름은 필수입니다.", field="name")
    if gender is not None and gender not in GENDER_CODES:
        raise WorkforceRuleViolation("성별은 M 또는 F여야 합니다.", field="gender")


def validate_employment_terms(
    *, email: str, base_salary: Decimal, role_codes: tuple[str, ...]
) -> None:
    if not email.strip():
        raise WorkforceRuleViolation("사내 이메일은 필수입니다.", field="email")
    if base_salary < 0:
        raise WorkforceRuleViolation("기본급은 0 이상이어야 합니다.", field="base_salary")
    if len(set(role_codes)) != len(role_codes):
        raise WorkforceRuleViolation("같은 역할을 중복해서 배정할 수 없습니다.", field="role_codes")


def ensure_no_period_overlap(
    existing: list[EmploymentPeriod],
    new_period: EmploymentPeriod,
    *,
    field: str = "hire_date",
) -> None:
    """HR-010: 같은 사원의 인사이력 기간은 겹칠 수 없다."""
    if new_period.end_date is not None and new_period.end_date < new_period.start_date:
        raise WorkforceRuleViolation("인사이력 종료일은 시작일보다 빠를 수 없습니다.", field=field)
    if any(period.overlaps(new_period) for period in existing):
        raise WorkforceRuleViolation("기존 인사이력과 기간이 겹칩니다.", field=field)
