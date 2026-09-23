from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from payroll.infrastructure.models import PayrollComponentTypeModel
from workforce.infrastructure.models import Employee, Person, Position, Role


def create_employee(employee_no: int, email: str) -> Employee:
    person = Person.objects.create(name=f"사원 {employee_no}")
    position, _ = Position.objects.get_or_create(
        position_code="STAFF", defaults={"position_name": "사원", "sort_order": 1}
    )
    return Employee.objects.create(
        employee_no=employee_no,
        person=person,
        position=position,
        tenure_status=Employee.TenureStatus.ACTIVE,
        email=email,
        hire_date=date(2024, 1, 1),
    )


def create_user(employee: Employee, email: str) -> User:
    return User.objects.create_user(email=email, password="safe-test-password", employee=employee)


def seed_components() -> None:
    PayrollComponentTypeModel.objects.create(code="BASE_PAY", name="기본급", category="지급")
    PayrollComponentTypeModel.objects.create(
        code="NATIONAL_PENSION", name="국민연금", category="공제"
    )


@pytest.mark.django_db
def test_only_payroll_manager_can_create_a_statement() -> None:

    employee = create_employee(1001, "employee@example.com")
    manager = create_employee(9001, "manager@example.com")
    employee_user = create_user(employee, "employee@example.com")
    manager_user = create_user(manager, "manager@example.com")
    role = Role.objects.create(role_code="PAYROLL_MANAGER", role_name="급여 담당자")
    manager.role_assignments.create(role=role, assigned_at=timezone.now())
    seed_components()

    client = APIClient()
    client.force_authenticate(employee_user)
    denied = client.post(
        "/api/payroll/statements/", {"emp_no": 1001, "year": 2026, "month": 9}, format="json"
    )
    assert denied.status_code == 403

    client.force_authenticate(manager_user)
    created = client.post(
        "/api/payroll/statements/", {"emp_no": 1001, "year": 2026, "month": 9}, format="json"
    )
    assert created.status_code == 201, created.data
    assert created.json()["status"] == "작성중"
    assert created.json()["payment_date"] == "2026-09-25"


@pytest.mark.django_db
def test_full_create_edit_confirm_cancel_reconfirm_flow_via_api() -> None:

    employee = create_employee(1001, "employee@example.com")
    manager = create_employee(9001, "manager@example.com")
    employee_user = create_user(employee, "employee@example.com")
    manager_user = create_user(manager, "manager@example.com")
    role = Role.objects.create(role_code="PAYROLL_MANAGER", role_name="급여 담당자")
    manager.role_assignments.create(role=role, assigned_at=timezone.now())
    seed_components()

    client = APIClient()
    client.force_authenticate(manager_user)

    created = client.post(
        "/api/payroll/statements/", {"emp_no": 1001, "year": 2026, "month": 9}, format="json"
    )
    statement_id = created.json()["statement_id"]

    updated = client.put(
        f"/api/payroll/statements/{statement_id}/items/",
        {
            "items": [
                {"component_code": "BASE_PAY", "amount": "3000000"},
                {"component_code": "NATIONAL_PENSION", "amount": "135000"},
            ]
        },
        format="json",
    )
    assert updated.status_code == 200, updated.data
    assert updated.json()["net_pay"] == 2865000.0

    confirmed = client.post(f"/api/payroll/statements/{statement_id}/confirm/", format="json")
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "확정"

    blocked_edit = client.put(
        f"/api/payroll/statements/{statement_id}/items/",
        {"items": [{"component_code": "BASE_PAY", "amount": "3200000"}]},
        format="json",
    )
    assert blocked_edit.status_code == 400

    cancelled = client.post(
        f"/api/payroll/statements/{statement_id}/cancel-confirmation/",
        {"reason": "기본급 정정"},
        format="json",
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "작성중"

    client.put(
        f"/api/payroll/statements/{statement_id}/items/",
        {"items": [{"component_code": "BASE_PAY", "amount": "3200000"}]},
        format="json",
    )
    reconfirmed = client.post(f"/api/payroll/statements/{statement_id}/confirm/", format="json")
    assert reconfirmed.status_code == 200

    client.force_authenticate(employee_user)
    own_view = client.get(f"/api/payroll/statements/{statement_id}/")
    assert own_view.status_code == 200
    assert own_view.json()["net_pay"] == 3200000.0

    history = client.get(f"/api/payroll/statements/{statement_id}/history/")
    assert [entry["action"] for entry in history.json()] == [
        "수정",
        "확정",
        "확정취소",
        "수정",
        "재확정",
    ]


@pytest.mark.django_db
def test_create_statement_accepts_items_up_front_and_returns_employee_summary() -> None:

    employee = create_employee(1001, "employee@example.com")
    manager = create_employee(9001, "manager@example.com")
    create_user(employee, "employee@example.com")
    manager_user = create_user(manager, "manager@example.com")
    role = Role.objects.create(role_code="PAYROLL_MANAGER", role_name="급여 담당자")
    manager.role_assignments.create(role=role, assigned_at=timezone.now())
    seed_components()

    client = APIClient()
    client.force_authenticate(manager_user)
    created = client.post(
        "/api/payroll/statements/",
        {
            "emp_no": 1001,
            "year": 2026,
            "month": 9,
            "items": [
                {"component_code": "BASE_PAY", "amount": "3000000"},
                {"component_code": "NATIONAL_PENSION", "amount": "135000"},
            ],
        },
        format="json",
    )

    assert created.status_code == 201, created.data
    assert created.json()["net_pay"] == 2865000.0
    assert created.json()["employee"] == {
        "emp_no": 1001,
        "name": "사원 1001",
        "position_name": "사원",
    }

    history = client.get(f"/api/payroll/statements/{created.json()['statement_id']}/history/")
    assert history.json() == []


@pytest.mark.django_db
def test_employee_cannot_view_another_employees_statement() -> None:

    owner = create_employee(1001, "owner@example.com")
    other = create_employee(1002, "other@example.com")
    manager = create_employee(9001, "manager@example.com")
    create_user(owner, "owner@example.com")
    other_user = create_user(other, "other@example.com")
    manager_user = create_user(manager, "manager@example.com")
    role = Role.objects.create(role_code="PAYROLL_MANAGER", role_name="급여 담당자")
    manager.role_assignments.create(role=role, assigned_at=timezone.now())
    seed_components()

    client = APIClient()
    client.force_authenticate(manager_user)
    created = client.post(
        "/api/payroll/statements/", {"emp_no": 1001, "year": 2026, "month": 9}, format="json"
    )
    statement_id = created.json()["statement_id"]

    client.force_authenticate(other_user)
    forbidden = client.get(f"/api/payroll/statements/{statement_id}/")
    assert forbidden.status_code == 403
