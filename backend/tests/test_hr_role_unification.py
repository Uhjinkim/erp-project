from datetime import date, timedelta
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.infrastructure.models import Employee, EmployeeRole, Person, Role


@pytest.mark.django_db
def test_hr_role_migration_preserves_assignment_history_and_merges_open_duplicates():
    now = timezone.now()
    legacy = Role.objects.create(role_code="HR_LEAVE_APPROVER", role_name="휴가 승인 인사담당자")
    manager = Role.objects.create(role_code="HR_MANAGER", role_name="인사 관리자")
    employee = Employee.objects.create(
        employee_no=9001, person=Person.objects.create(name="합성 관리자"),
        tenure_status="재직", hire_date=date(2024, 1, 1),
    )
    rows = [
        EmployeeRole.objects.create(
            employee=employee, role=role, assigned_at=now + timedelta(days=start),
            revoked_at=now + timedelta(days=end) if end is not None else None,
        )
        for role, start, end in [
            (manager, -10, None), (legacy, -5, None),
            (legacy, -30, -20), (legacy, 10, 20),
        ]
    ]
    original = {row.pk: (row.assigned_at, row.revoked_at) for row in rows}
    migration = import_module("workforce.migrations.0008_unify_hr_roles")
    migration.unify_hr_roles(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))
    assert not Role.objects.filter(pk="HR_LEAVE_APPROVER").exists()
    assert EmployeeRole.objects.count() == 4
    for row in rows:
        row.refresh_from_db()
        assert row.role_id == "HR_MANAGER"
        assert row.assigned_at == original[row.pk][0]
    assert rows[0].revoked_at is None
    assert rows[1].revoked_at >= now
    assert rows[2].revoked_at == original[rows[2].pk][1]
    assert rows[3].revoked_at == original[rows[3].pk][1]


@pytest.mark.django_db
def test_multiple_hr_managers_can_be_assigned_and_legacy_role_is_not_offered():
    user = User.objects.create_superuser(email="synthetic-admin@example.test", password="test-only")
    client = APIClient()
    client.force_authenticate(user)
    Role.objects.create(role_code="HR_MANAGER", role_name="인사 관리자")
    Role.objects.create(role_code="HR_LEAVE_APPROVER", role_name="휴가 승인 인사담당자")
    for number in (9001, 9002):
        Employee.objects.create(
            employee_no=number, person=Person.objects.create(name=f"합성 관리자 {number}"),
            tenure_status="재직", hire_date=date(2024, 1, 1),
        )
        url = f"/api/workforce/employees/{number}/roles/"
        assert client.post(url, {"role_code": "HR_MANAGER"}, format="json").status_code == 201
        legacy_response = client.post(url, {"role_code": "HR_LEAVE_APPROVER"}, format="json")
        assert legacy_response.status_code == 400
    response = client.get("/api/workforce/roles/")
    assert response.status_code == 200
    assert [role["role_code"] for role in response.json()] == ["HR_MANAGER"]
    assert client.get("/api/workforce/roles/HR_LEAVE_APPROVER/").status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("existing", [False, True])
def test_management_officer_and_board_moderator_share_one_seeded_role(existing):
    assignment = None
    if existing:
        role = Role.objects.create(role_code="MANAGEMENT_OFFICER", role_name="경영 담당자")
        employee = Employee.objects.create(
            employee_no=3003, person=Person.objects.create(name="합성 경영 담당자"),
            tenure_status="재직", hire_date=date(2024, 1, 1),
        )
        assignment = EmployeeRole.objects.create(
            employee=employee, role=role, assigned_at=timezone.now()
        )
    migration = import_module("workforce.migrations.0009_management_officer_role")
    schema_editor = SimpleNamespace(connection=SimpleNamespace(alias="default"))
    # 재실행해도 역할을 중복 생성하지 않는다.
    migration.ensure_management_officer_role(apps, schema_editor)
    migration.ensure_management_officer_role(apps, schema_editor)
    assert list(Role.objects.values_list("role_code", "role_name")) == [
        ("MANAGEMENT_OFFICER", "경영 담당자 (게시판 운영자)")
    ]
    if assignment:
        assignment.refresh_from_db()
        assert assignment.role_id == "MANAGEMENT_OFFICER"
        assert assignment.revoked_at is None
    user = User.objects.create_user(email="synthetic-viewer@example.test")
    client = APIClient()
    client.force_authenticate(user)
    assert client.get("/api/workforce/roles/").json() == [
        {"role_code": "MANAGEMENT_OFFICER", "role_name": "경영 담당자 (게시판 운영자)"}
    ]
