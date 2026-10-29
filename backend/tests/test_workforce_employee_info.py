from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.services import HR_MANAGER_ROLE
from workforce.domain.policies import can_view_employee_info
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Position,
    Role,
)

ACCOUNT_FIELDS = {"bank_code": "000", "account_no": "0000000000"}


@pytest.mark.parametrize(
    ("viewer_no", "target_no", "is_hr_manager", "expected"),
    [
        (1001, 1001, False, True),
        (1001, 1002, False, False),
        (9001, 1002, True, True),
        (None, 1001, False, False),
    ],
)
def test_hr_001_employee_info_visibility(
    viewer_no: int | None,
    target_no: int,
    is_hr_manager: bool,
    expected: bool,
) -> None:
    assert (
        can_view_employee_info(
            viewer_no=viewer_no,
            target_no=target_no,
            viewer_is_hr_manager=is_hr_manager,
        )
        is expected
    )


def create_user(employee_no: int, *, department: Department | None = None) -> User:
    person = Person.objects.create(
        name=f"사원 {employee_no}", birth_date=date(1990, 5, 1), gender="F"
    )
    position, _ = Position.objects.get_or_create(
        position_code="STAFF",
        defaults={"position_name": "사원", "sort_order": 1},
    )
    employee = Employee.objects.create(
        employee_no=employee_no,
        person=person,
        department=department,
        position=position,
        tenure_status=Employee.TenureStatus.ACTIVE,
        email=f"user{employee_no}@example.com",
        phone="010-0000-0000",
        address="테스트 주소",
        bank_code="000",
        account_no="0000000000",
        hire_date=date(2024, 1, 1),
    )
    return User.objects.create_user(
        email=employee.email,
        password="safe-test-password",
        employee=employee,
    )


def grant_hr_manager(user: User) -> None:
    role, _ = Role.objects.get_or_create(
        role_code=HR_MANAGER_ROLE, defaults={"role_name": "인사 관리자"}
    )
    EmployeeRole.objects.create(employee=user.employee, role=role, assigned_at=timezone.now())


@pytest.fixture
def department() -> Department:
    return Department.objects.create(dept_no=10, dept_name="개발팀")


@pytest.mark.django_db
def test_fn_hr_001_employee_reads_own_info_with_account(department: Department) -> None:
    user = create_user(1001, department=department)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/workforce/employees/me/")

    assert response.status_code == 200
    body = response.json()
    assert body["emp_no"] == 1001
    assert body["name"] == "사원 1001"
    assert body["birth_date"] == "1990-05-01"
    assert body["dept_name"] == "개발팀"
    assert body["position_name"] == "사원"
    assert body["address"] == "테스트 주소"
    assert ACCOUNT_FIELDS.items() <= body.items()


@pytest.mark.django_db
def test_me_returns_404_when_account_has_no_employee() -> None:
    user = User.objects.create_user(email="no-employee@example.com", password="safe-test-password")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/workforce/employees/me/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_me_requires_authentication() -> None:
    response = APIClient().get("/api/workforce/employees/me/")

    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_hr_001_employee_can_retrieve_only_own_detail() -> None:
    user = create_user(1001)
    create_user(1002)
    client = APIClient()
    client.force_authenticate(user)

    own = client.get("/api/workforce/employees/1001/")
    other = client.get("/api/workforce/employees/1002/")

    assert own.status_code == 200
    assert ACCOUNT_FIELDS.items() <= own.json().items()
    assert other.status_code == 403


@pytest.mark.django_db
def test_hr_001_only_hr_manager_can_list_employees() -> None:
    ordinary = create_user(1001)
    manager = create_user(9001)
    grant_hr_manager(manager)
    client = APIClient()

    client.force_authenticate(ordinary)
    assert client.get("/api/workforce/employees/").status_code == 403

    client.force_authenticate(manager)
    listed = client.get("/api/workforce/employees/")
    assert listed.status_code == 200
    assert [item["emp_no"] for item in listed.json()] == [1001, 9001]


@pytest.mark.django_db
def test_hr_manager_retrieves_other_employee_detail_with_account(
    department: Department,
) -> None:
    create_user(1001, department=department)
    manager = create_user(9001)
    grant_hr_manager(manager)
    client = APIClient()
    client.force_authenticate(manager)

    response = client.get("/api/workforce/employees/1001/")

    assert response.status_code == 200
    assert response.json()["dept_name"] == "개발팀"
    assert ACCOUNT_FIELDS.items() <= response.json().items()


@pytest.mark.django_db
def test_detail_ignores_list_filters() -> None:
    manager = create_user(9001)
    grant_hr_manager(manager)
    client = APIClient()
    client.force_authenticate(manager)

    response = client.get("/api/workforce/employees/9001/?tenure_status=퇴사")

    assert response.status_code == 200


@pytest.mark.django_db
def test_retrieve_unknown_employee_returns_404() -> None:
    manager = create_user(9001)
    grant_hr_manager(manager)
    client = APIClient()
    client.force_authenticate(manager)

    assert client.get("/api/workforce/employees/4040/").status_code == 404
