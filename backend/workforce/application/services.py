from workforce.application.ports import (
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
HR_LEAVE_APPROVER_ROLE = "HR_LEAVE_APPROVER"


def employee_has_role(
    employee_no: int,
    role_code: str,
    gateway: WorkforceQueryGateway,
) -> bool:
    return gateway.has_active_role(employee_no, role_code)


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
    return choose_vacation_approver(
        applicant_no=employee_no,
        department_head=gateway.department_head(employee_no),
        hr_approvers=gateway.active_role_holders(HR_LEAVE_APPROVER_ROLE, limit=2),
    )


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
    if (
        role_code == HR_LEAVE_APPROVER_ROLE
        and gateway.active_role_holder_count(role_code) > 0
    ):
        raise WorkforceRuleViolation("휴가 승인 인사담당자는 한 명만 지정할 수 있습니다.")
    return gateway.assign_role(employee_no, role_code)


def revoke_employee_role(
    employee_no: int,
    assignment_id: int,
    gateway: RoleCommandGateway,
) -> None:
    if not gateway.revoke_role(employee_no, assignment_id):
        raise WorkforceRuleViolation("활성 역할을 찾을 수 없습니다.")
