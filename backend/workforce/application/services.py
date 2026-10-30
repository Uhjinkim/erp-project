from workforce.application.ports import (
    ActiveRolesGateway,
    DepartmentHeadGateway,
    EmployeeProfileGateway,
    RoleCommandGateway,
    WorkforceQueryGateway,
)
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.policies import (
    EmployeeProfile,
    can_view_employee_info,
    choose_vacation_approver,
)

HR_MANAGER_ROLE = "HR_MANAGER"
# 과거 배정 이력·입력 거절에만 사용한다. 0008에서 HR_MANAGER로 통합한다.
HR_LEAVE_APPROVER_ROLE = "HR_LEAVE_APPROVER"
MANAGEMENT_OFFICER_ROLE = "MANAGEMENT_OFFICER"
PAYROLL_MANAGER_ROLE = "PAYROLL_MANAGER"


def is_department_head(employee_no: int, gateway: DepartmentHeadGateway) -> bool:
    """메뉴 안내용 조직 정보. 업무별 권한과 처리 대상은 각 API가 검사한다."""
    return gateway.is_department_head(employee_no)


def employee_has_role(
    employee_no: int,
    role_code: str,
    gateway: WorkforceQueryGateway,
) -> bool:
    return gateway.has_active_role(employee_no, role_code)


def active_employee_roles(employee_no: int, gateway: ActiveRolesGateway) -> set[str]:
    return gateway.active_role_codes(employee_no)


def get_employee_profile(
    employee_no: int,
    gateway: EmployeeProfileGateway,
) -> EmployeeProfile | None:
    """FN-HR-001: 로그인한 사원 본인의 인사정보 조회."""
    return gateway.employee_profile(employee_no)


def can_view_employee(
    viewer_no: int | None,
    target_no: int,
    gateway: WorkforceQueryGateway,
) -> bool:
    viewer_is_hr_manager = viewer_no is not None and gateway.has_active_role(
        viewer_no, HR_MANAGER_ROLE
    )
    return can_view_employee_info(
        viewer_no=viewer_no,
        target_no=target_no,
        viewer_is_hr_manager=viewer_is_hr_manager,
    )


def resolve_vacation_approver(
    employee_no: int,
    gateway: WorkforceQueryGateway,
) -> int | None:
    head = gateway.department_head(employee_no)
    if head is not None and head.employee_no == employee_no:
        head = gateway.parent_department_head(employee_no)
    return choose_vacation_approver(
        applicant_no=employee_no,
        department_head=head,
    )


def has_vacation_hr_approvers(gateway: WorkforceQueryGateway) -> bool:
    return any(candidate.is_active for candidate in gateway.active_role_holders(HR_MANAGER_ROLE))


def assign_employee_role(
    employee_no: int,
    role_code: str,
    gateway: RoleCommandGateway,
) -> int:
    if not gateway.employee_is_active(employee_no):
        raise WorkforceRuleViolation(
            "재직 중인 사원에게만 역할을 부여할 수 있습니다.",
            field="emp_no",
        )
    if gateway.has_active_assignment(employee_no, role_code):
        raise WorkforceRuleViolation("이미 활성화된 역할입니다.")
    if role_code == HR_LEAVE_APPROVER_ROLE:
        raise WorkforceRuleViolation("인사 관리자 역할을 선택하세요.", field="role_code")
    return gateway.assign_role(employee_no, role_code)


def revoke_employee_role(
    employee_no: int,
    assignment_id: int,
    gateway: RoleCommandGateway,
) -> None:
    if not gateway.revoke_role(employee_no, assignment_id):
        raise WorkforceRuleViolation("활성 역할을 찾을 수 없습니다.")
