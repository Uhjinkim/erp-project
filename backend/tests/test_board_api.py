from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.services import PAYROLL_MANAGER_ROLE
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


def create_user(employee: Employee, *, is_superuser: bool = False) -> User:
    return User.objects.create_user(
        email=employee.email,
        password="safe-test-password",
        employee=employee,
        is_staff=is_superuser,
        is_superuser=is_superuser,
    )


def assign_role(employee: Employee, role_code: str, role_name: str) -> None:
    role, _ = Role.objects.get_or_create(role_code=role_code, defaults={"role_name": role_name})
    EmployeeRole.objects.create(employee=employee, role=role, assigned_at=timezone.now())


@pytest.mark.django_db
def test_active_employee_can_create_and_read_general_post() -> None:
    employee = create_employee(1001, "writer@example.com")
    user = create_user(employee)
    client = APIClient()
    client.force_authenticate(user)

    created = client.post(
        "/api/board/posts/",
        {"post_type": "일반", "title": "안녕하세요", "content": "본문입니다"},
        format="json",
    )
    assert created.status_code == 201, created.data
    post_id = created.data["post_id"]

    detail = client.get(f"/api/board/posts/{post_id}/")
    assert detail.status_code == 200
    assert detail.data["title"] == "안녕하세요"

    listing = client.get("/api/board/posts/")
    assert listing.status_code == 200
    assert len(listing.data) == 1


@pytest.mark.django_db
def test_employee_without_role_cannot_write_hr_notice() -> None:
    employee = create_employee(1001, "ordinary@example.com")
    user = create_user(employee)
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/board/posts/",
        {
            "post_type": "공지",
            "notice_category": "인사",
            "title": "인사 공지",
            "content": "본문",
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_payroll_manager_can_write_payroll_notice_visible_to_others() -> None:
    payroll_employee = create_employee(9001, "payroll@example.com")
    assign_role(payroll_employee, PAYROLL_MANAGER_ROLE, "급여 담당자")
    payroll_user = create_user(payroll_employee)

    viewer_employee = create_employee(1001, "viewer@example.com")
    viewer_user = create_user(viewer_employee)

    client = APIClient()
    client.force_authenticate(payroll_user)
    created = client.post(
        "/api/board/posts/",
        {
            "post_type": "공지",
            "notice_category": "급여",
            "title": "급여 지급 안내",
            "content": "본문",
        },
        format="json",
    )
    assert created.status_code == 201, created.data

    client.force_authenticate(viewer_user)
    detail = client.get(f"/api/board/posts/{created.data['post_id']}/")
    assert detail.status_code == 200
    assert detail.data["notice_category"] == "급여"


@pytest.mark.django_db
def test_only_author_or_admin_can_edit_or_delete() -> None:
    author = create_employee(1001, "author@example.com")
    author_user = create_user(author)
    other = create_employee(2002, "other@example.com")
    other_user = create_user(other)
    admin = create_employee(9999, "admin@example.com")
    admin_user = create_user(admin, is_superuser=True)

    client = APIClient()
    client.force_authenticate(author_user)
    created = client.post(
        "/api/board/posts/",
        {"post_type": "일반", "title": "제목", "content": "내용"},
        format="json",
    )
    post_id = created.data["post_id"]

    client.force_authenticate(other_user)
    denied = client.patch(
        f"/api/board/posts/{post_id}/",
        {"title": "변경 시도", "content": "변경 시도"},
        format="json",
    )
    assert denied.status_code == 403

    client.force_authenticate(author_user)
    edited = client.patch(
        f"/api/board/posts/{post_id}/",
        {"title": "수정됨", "content": "수정됨"},
        format="json",
    )
    assert edited.status_code == 200
    assert edited.data["title"] == "수정됨"

    client.force_authenticate(other_user)
    denied_delete = client.delete(f"/api/board/posts/{post_id}/")
    assert denied_delete.status_code == 403

    client.force_authenticate(admin_user)
    deleted = client.delete(f"/api/board/posts/{post_id}/")
    assert deleted.status_code == 204

    not_found = client.get(f"/api/board/posts/{post_id}/")
    assert not_found.status_code == 404
