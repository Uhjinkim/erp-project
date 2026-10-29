from datetime import date, timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.personal_info import Actor, PersonalInfoService, ProcessingNotAllowed
from workforce.domain.personal_info import ApprovalRequiredValues
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    Person,
    Role,
)
from workforce.infrastructure.models import (
    PersonalInfoChangeRequest as RequestModel,
)
from workforce.infrastructure.personal_info import DjangoPersonalInfoRepository


def user_with_employee(number: int, roles: tuple[str, ...] = ()) -> User:
    employee = Employee.objects.create(
        employee_no=number,
        person=Person.objects.create(name=f"합성 사원 {number}"),
        hire_date=date(2020, 1, 1),
        tenure_status="재직",
        email=f"synthetic{number}@example.test",
    )
    user = User.objects.create_user(email=employee.email, employee=employee, password="synthetic")
    for role in roles:
        Role.objects.get_or_create(role_code=role, defaults={"role_name": role})
        EmployeeRole.objects.create(employee=employee, role_id=role, assigned_at=timezone.now())
    return user


def session_client(user: User) -> APIClient:
    client = APIClient()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_session_me_reuses_authenticated_profile_and_keeps_roles_fresh() -> None:
    user = user_with_employee(1001, ("HR_MANAGER",))
    department = Department.objects.create(dept_no=1, dept_name="합성 부서", head=user.employee)
    user.employee.department = department
    user.employee.save(update_fields=["department"])
    client = session_client(user)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/auth/me/")
    assert response.status_code == 200
    assert response.json()["is_department_head"] is True
    assert response.json()["employee"]["dept_name"] == "합성 부서"
    assert response.json()["roles"] == ["HR_MANAGER"]
    assert len(queries) <= 4  # session, user, joined profile/head, roles
    print(f"auth/me queries={len(queries)}")

    EmployeeRole.objects.filter(employee=user.employee).update(revoked_at=timezone.now())
    department.head = None
    department.save(update_fields=["head"])
    current = client.get("/api/auth/me/").json()
    assert current["roles"] == []
    assert current["is_department_head"] is False
    user.employee.tenure_status = "퇴사"
    user.employee.term_date = date.today()
    user.employee.save(update_fields=["tenure_status", "term_date"])
    assert client.get("/api/auth/me/").status_code == 403


@pytest.mark.django_db
def test_notice_categories_use_one_role_query_and_respect_role_dates() -> None:
    user = user_with_employee(1001, ("HR_MANAGER", "MANAGEMENT_OFFICER", "PAYROLL_MANAGER"))
    now = timezone.now()
    EmployeeRole.objects.filter(employee=user.employee, role_id="PAYROLL_MANAGER").update(
        assigned_at=now + timedelta(days=1)
    )
    EmployeeRole.objects.filter(employee=user.employee, role_id="MANAGEMENT_OFFICER").update(
        revoked_at=now - timedelta(days=1)
    )
    client = session_client(user)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/board/notice-categories/eligible/")
    assert response.status_code == 200
    assert response.json() == {"categories": ["HR"]}
    assert len(queries) <= 4
    print(f"notice eligible queries={len(queries)}")
    EmployeeRole.objects.filter(employee=user.employee, role_id="HR_MANAGER").update(revoked_at=now)
    assert client.get("/api/board/notice-categories/eligible/").json() == {"categories": []}


@pytest.mark.django_db
def test_queue_bulk_contexts_preserve_special_processor_and_recheck_before_write() -> None:
    manager = user_with_employee(9001, ("HR_MANAGER",))
    other_manager = user_with_employee(9002, ("HR_MANAGER",))
    department = Department.objects.create(
        dept_no=1, dept_name="합성 인사팀", head=manager.employee
    )
    other_manager.employee.department = department
    other_manager.employee.save(update_fields=["department"])
    service = PersonalInfoService(
        DjangoPersonalInfoRepository(), DjangoWorkforceQueryGateway(), timezone.now
    )
    special = service.submit_change_request(
        other_manager.employee_id, ApprovalRequiredValues(phone="010-0000-1234")
    )
    for number in range(1001, 1021):
        user = user_with_employee(number)
        service.submit_change_request(
            user.employee_id, ApprovalRequiredValues(phone="010-0000-5678")
        )
    client = session_client(manager)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/workforce/personal-info-requests/?processable=true")
    assert response.status_code == 200
    assert len(response.json()) == 21
    assert all(row["can_process"] for row in response.json())
    assert len(queries) <= 7  # auth 3, actor role 1, requests 1, contexts 2
    print(f"processable queue (21 mixed requests) queries={len(queries)}")

    actor = Actor(employee_no=manager.employee_id, is_hr_manager=True)
    assert len(service.list_requests(actor, processable_only=True)) == 21
    # Commands must recheck current organization even after caching a list.
    department.head = other_manager.employee
    department.save(update_fields=["head"])
    with pytest.raises(ProcessingNotAllowed):
        service.approve(special.request_id, actor)
    assert RequestModel.objects.get(pk=special.request_id).status == "대기"


@pytest.mark.django_db
@pytest.mark.parametrize("total", [1, 10])
def test_session_queue_query_count_is_constant(total: int) -> None:
    manager = user_with_employee(9001, ("HR_MANAGER",))
    service = PersonalInfoService(
        DjangoPersonalInfoRepository(), DjangoWorkforceQueryGateway(), timezone.now
    )
    for number in range(1001, 1001 + total):
        user = user_with_employee(number)
        service.submit_change_request(user.employee_id, ApprovalRequiredValues(phone="synthetic"))
    client = session_client(manager)
    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/workforce/personal-info-requests/?processable=true")
    assert response.status_code == 200
    assert len(response.json()) == total
    assert len(queries) == 7
    print(f"processable queue ({total} requests) queries={len(queries)}")
