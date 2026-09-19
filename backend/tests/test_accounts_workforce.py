from datetime import date, timedelta

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from vacation.infrastructure.models import LeaveBalanceModel, LeaveTypeModel
from workforce.application.services import (
    HR_LEAVE_APPROVER_ROLE,
    HR_MANAGER_ROLE,
    employee_has_role,
    resolve_vacation_approver,
)
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)


def create_employee(
    employee_no: int,
    email: str,
    *,
    department: Department | None = None,
) -> Employee:
    person = Person.objects.create(name=f"사원 {employee_no}")
    position, _ = Position.objects.get_or_create(
        position_code="STAFF",
        defaults={"position_name": "사원", "sort_order": 1},
    )
    return Employee.objects.create(
        employee_no=employee_no,
        person=person,
        department=department,
        position=position,
        tenure_status=Employee.TenureStatus.ACTIVE,
        email=email,
        hire_date=date(2024, 1, 1),
    )


@pytest.mark.django_db
def test_email_login_creates_server_session_and_me_response() -> None:
    employee = create_employee(1001, "employee@example.com")
    User.objects.create_user(
        email="Employee@Example.com",
        password="safe-test-password",
        employee=employee,
    )
    client = APIClient(enforce_csrf_checks=True)

    csrf_response = client.get("/api/auth/csrf/")
    csrf_token = csrf_response.cookies["csrftoken"].value
    login_response = client.post(
        "/api/auth/login/",
        {"email": "EMPLOYEE@example.com", "password": "safe-test-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert login_response.status_code == 200
    assert login_response.json()["email"] == "employee@example.com"
    assert login_response.json()["employee"]["emp_no"] == 1001
    assert "sessionid" in login_response.cookies

    me_response = client.get("/api/auth/me/")
    assert me_response.status_code == 200
    assert me_response.json()["employee"]["name"] == "사원 1001"


@pytest.mark.django_db
def test_inactive_employee_cannot_login() -> None:
    employee = create_employee(1001, "inactive@example.com")
    employee.tenure_status = Employee.TenureStatus.TERMINATED
    employee.term_date = date(2025, 1, 1)
    employee.save(update_fields=["tenure_status", "term_date"])
    User.objects.create_user(
        email="inactive@example.com",
        password="safe-test-password",
        employee=employee,
    )
    client = APIClient(enforce_csrf_checks=True)
    csrf_token = client.get("/api/auth/csrf/").cookies["csrftoken"].value

    response = client.post(
        "/api/auth/login/",
        {"email": "inactive@example.com", "password": "safe-test-password"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 400
    assert response.json()["non_field_errors"] == ["재직 중인 사원만 로그인할 수 있습니다."]


@pytest.mark.django_db
def test_hr_leave_approver_is_used_when_department_has_no_head() -> None:
    department = Department.objects.create(dept_no=10, dept_name="개발팀")
    applicant = create_employee(1001, "applicant@example.com", department=department)
    hr_employee = create_employee(9001, "hr@example.com")
    role = Role.objects.create(
        role_code=HR_LEAVE_APPROVER_ROLE,
        role_name="휴가 승인 인사담당자",
    )
    EmployeeRole.objects.create(
        employee=hr_employee,
        role=role,
        assigned_at=timezone.now(),
    )

    assert resolve_vacation_approver(
        applicant.employee_no, DjangoWorkforceQueryGateway()
    ) == hr_employee.employee_no


@pytest.mark.django_db
def test_rehire_uses_new_employee_number_for_same_person() -> None:
    person = Person.objects.create(name="재입사자")
    position = Position.objects.create(
        position_code="STAFF", position_name="사원", sort_order=1
    )
    Employee.objects.create(
        employee_no=1001,
        person=person,
        position=position,
        tenure_status=Employee.TenureStatus.TERMINATED,
        email="former@example.com",
        hire_date=date(2020, 1, 1),
        term_date=date(2024, 12, 31),
    )

    rehired = Employee.objects.create(
        employee_no=2001,
        person=person,
        position=position,
        tenure_status=Employee.TenureStatus.ACTIVE,
        email="rehired@example.com",
        hire_date=date(2026, 1, 1),
    )

    assert list(person.employments.values_list("employee_no", flat=True)) == [1001, 2001]
    assert rehired.person_id == person.person_id


@pytest.mark.django_db
def test_future_role_assignment_is_not_active() -> None:
    employee = create_employee(1001, "future-role@example.com")
    role = Role.objects.create(role_code=HR_MANAGER_ROLE, role_name="인사 관리자")
    EmployeeRole.objects.create(
        employee=employee,
        role=role,
        assigned_at=timezone.now() + timedelta(days=1),
    )
    user = User.objects.create_user(
        email="future-role@example.com",
        password="safe-test-password",
        employee=employee,
    )
    client = APIClient()
    client.force_authenticate(user)

    assert employee_has_role(
        employee.employee_no,
        HR_MANAGER_ROLE,
        DjangoWorkforceQueryGateway(),
    ) is False
    assert client.get("/api/auth/me/").json()["roles"] == []


@pytest.mark.django_db
def test_only_hr_manager_can_create_department() -> None:
    ordinary_employee = create_employee(1001, "ordinary@example.com")
    hr_employee = create_employee(9001, "hr@example.com")
    ordinary_user = User.objects.create_user(
        email="ordinary@example.com",
        password="safe-test-password",
        employee=ordinary_employee,
    )
    hr_user = User.objects.create_user(
        email="hr@example.com",
        password="safe-test-password",
        employee=hr_employee,
    )
    role = Role.objects.create(role_code=HR_MANAGER_ROLE, role_name="인사 관리자")
    EmployeeRole.objects.create(employee=hr_employee, role=role, assigned_at=timezone.now())
    client = APIClient()

    client.force_authenticate(ordinary_user)
    denied = client.post(
        "/api/workforce/departments/",
        {"dept_no": 10, "dept_name": "개발팀", "parent_dept_no": None, "head_emp_no": None},
        format="json",
    )
    assert denied.status_code == 403

    client.force_authenticate(hr_user)
    created = client.post(
        "/api/workforce/departments/",
        {"dept_no": 10, "dept_name": "개발팀", "parent_dept_no": None, "head_emp_no": None},
        format="json",
    )
    assert created.status_code == 201, created.data


@pytest.mark.django_db
def test_hr_manager_assigns_and_revokes_role_through_application_command() -> None:
    manager = create_employee(9001, "manager@example.com")
    target = create_employee(1001, "target@example.com")
    manager_user = User.objects.create_user(
        email="manager@example.com",
        password="safe-test-password",
        employee=manager,
    )
    manager_role = Role.objects.create(role_code=HR_MANAGER_ROLE, role_name="인사 관리자")
    target_role = Role.objects.create(role_code="PAYROLL_MANAGER", role_name="급여 담당자")
    EmployeeRole.objects.create(
        employee=manager,
        role=manager_role,
        assigned_at=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(manager_user)

    assigned = client.post(
        f"/api/workforce/employees/{target.employee_no}/roles/",
        {"role_code": target_role.role_code},
        format="json",
    )
    assert assigned.status_code == 201, assigned.data

    duplicate = client.post(
        f"/api/workforce/employees/{target.employee_no}/roles/",
        {"role_code": target_role.role_code},
        format="json",
    )
    assert duplicate.status_code == 400

    revoked = client.post(
        f"/api/workforce/employees/{target.employee_no}/roles/"
        f"{assigned.json()['employee_role_id']}/revoke/",
        format="json",
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None


@pytest.mark.django_db
@override_settings(
    VACATION_INTEGRATION_MODE="database",
    VACATION_INTEGRATION_READY=True,
)
def test_session_identity_and_workforce_gateway_complete_vacation_flow() -> None:
    department = Department.objects.create(dept_no=10, dept_name="개발팀")
    applicant = create_employee(1001, "applicant@example.com", department=department)
    approver = create_employee(2001, "approver@example.com", department=department)
    department.head = approver
    department.save(update_fields=["head"])
    applicant_user = User.objects.create_user(
        email="applicant@example.com",
        password="safe-test-password",
        employee=applicant,
    )
    approver_user = User.objects.create_user(
        email="approver@example.com",
        password="safe-test-password",
        employee=approver,
    )
    vacation_type = LeaveTypeModel.objects.create(
        type_id="ANNUAL",
        type_name="연차",
        is_paid=True,
        deduct_days=1,
    )
    LeaveBalanceModel.objects.create(
        employee=applicant,
        vacation_type=vacation_type,
        remaining_days=10,
    )
    client = APIClient()
    client.force_authenticate(applicant_user)

    created = client.post(
        "/api/vacations/requests/",
        {
            "type_id": "ANNUAL",
            "start_datetime": "2026-10-01T09:00:00+09:00",
            "end_datetime": "2026-10-01T18:00:00+09:00",
            "use_days": "1.00",
            "reason": "통합 테스트",
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    assert created.json()["approver_no"] == approver.employee_no

    client.force_authenticate(approver_user)
    approved = client.post(
        f"/api/vacations/requests/{created.json()['request_id']}/approve/",
        format="json",
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "승인"
