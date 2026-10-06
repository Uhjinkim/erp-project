from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from evaluation.infrastructure.models import EvaluationModel
from workforce.application.services import HR_MANAGER_ROLE
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
    tenure_status: str = Employee.TenureStatus.ACTIVE,
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
        tenure_status=tenure_status,
        email=email,
        hire_date=date(2024, 1, 1),
    )


def client_for(employee: Employee) -> APIClient:
    user = User.objects.create_user(
        email=employee.email,
        password="safe-test-password",
        employee=employee,
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def org() -> dict[str, Employee]:
    department = Department.objects.create(dept_no=10, dept_name="개발팀")
    head = create_employee(2001, "head@example.com", department=department)
    department.head = head
    department.save(update_fields=["head"])
    member = create_employee(1001, "member@example.com", department=department)
    other = create_employee(3001, "other@example.com")
    hr = create_employee(9001, "hr@example.com")
    role, _ = Role.objects.get_or_create(
        role_code=HR_MANAGER_ROLE, defaults={"role_name": "인사관리자"}
    )
    EmployeeRole.objects.create(employee=hr, role=role, assigned_at=timezone.now())
    return {"head": head, "member": member, "other": other, "hr": hr}


def create_evaluation(client: APIClient, emp_no: int = 1001, score: str = "85.5"):
    return client.post(
        "/api/evaluations/",
        {"emp_no": emp_no, "eval_year": "2026", "score": score, "comments": "우수"},
        format="json",
    )


@pytest.mark.django_db
def test_department_head_creates_evaluation_with_grade_and_snapshot(org) -> None:
    response = create_evaluation(client_for(org["head"]), score="85.5")

    assert response.status_code == 201, response.data
    assert response.data["grade"] == "A"
    assert response.data["score"] == "85.50"
    assert response.data["eval_status"] == "작성중"
    assert response.data["snapshot_dept_no"] == 10
    assert response.data["snapshot_pos_code"] == "STAFF"
    assert response.data["evaluator_no"] == 2001
    assert response.data["employee_name"] == "사원 1001"


@pytest.mark.django_db
def test_non_head_cannot_create_evaluation(org) -> None:
    response = create_evaluation(client_for(org["other"]))
    assert response.status_code == 403
    assert response.data["code"] == "permission_denied"


@pytest.mark.django_db
def test_self_evaluation_is_rejected(org) -> None:
    response = create_evaluation(client_for(org["head"]), emp_no=2001)
    assert response.status_code == 403
    assert response.data["code"] == "self_evaluation_not_allowed"


@pytest.mark.django_db
def test_duplicate_year_evaluation_conflicts(org) -> None:
    head = client_for(org["head"])
    assert create_evaluation(head).status_code == 201
    response = create_evaluation(head)
    assert response.status_code == 409
    assert response.data["code"] == "duplicate_evaluation"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"emp_no": 1001, "eval_year": "2026", "score": "100.01"},
        {"emp_no": 1001, "eval_year": "26", "score": "80"},
        {"emp_no": 1001, "eval_year": "2026", "score": "80.123"},
        {"emp_no": 1001, "eval_year": "2026"},
    ],
)
def test_invalid_payload_is_rejected(org, payload) -> None:
    response = client_for(org["head"]).post("/api/evaluations/", payload, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_head_revises_and_hr_confirms_then_evaluation_is_locked(org) -> None:
    head = client_for(org["head"])
    hr = client_for(org["hr"])
    eval_id = create_evaluation(head).data["eval_id"]

    revised = head.patch(
        f"/api/evaluations/{eval_id}/", {"score": "69.99", "comments": "보완"}, format="json"
    )
    assert revised.status_code == 200
    assert revised.data["grade"] == "C"

    assert head.post(f"/api/evaluations/{eval_id}/confirm/").status_code == 403

    confirmed = hr.post(f"/api/evaluations/{eval_id}/confirm/")
    assert confirmed.status_code == 200
    assert confirmed.data["eval_status"] == "확정"
    assert confirmed.data["confirmed_by"] == 9001
    assert confirmed.data["confirmed_at"] is not None

    locked = head.patch(f"/api/evaluations/{eval_id}/", {"score": "95"}, format="json")
    assert locked.status_code == 409
    assert hr.post(f"/api/evaluations/{eval_id}/confirm/").status_code == 409

    stored = EvaluationModel.objects.get(eval_id=eval_id)
    assert str(stored.score) == "69.99"
    assert stored.grade == "C"


@pytest.mark.django_db
def test_target_sees_evaluation_only_after_confirmation(org) -> None:
    head = client_for(org["head"])
    member = client_for(org["member"])
    other = client_for(org["other"])
    eval_id = create_evaluation(head).data["eval_id"]

    assert member.get(f"/api/evaluations/{eval_id}/").status_code == 404
    assert member.get("/api/evaluations/").data == []
    assert other.get(f"/api/evaluations/{eval_id}/").status_code == 404

    client_for(org["hr"]).post(f"/api/evaluations/{eval_id}/confirm/")

    assert member.get(f"/api/evaluations/{eval_id}/").status_code == 200
    assert [item["eval_id"] for item in member.get("/api/evaluations/").data] == [eval_id]
    assert other.get("/api/evaluations/").data == []


@pytest.mark.django_db
def test_hr_manager_lists_all_and_filters_by_year(org) -> None:
    create_evaluation(client_for(org["head"]))
    hr = client_for(org["hr"])

    assert len(hr.get("/api/evaluations/").data) == 1
    assert len(hr.get("/api/evaluations/?year=2026").data) == 1
    assert hr.get("/api/evaluations/?year=2025").data == []
    assert hr.get("/api/evaluations/?year=abc").status_code == 400


@pytest.mark.django_db
def test_missing_evaluation_returns_404(org) -> None:
    assert client_for(org["hr"]).get("/api/evaluations/999/").status_code == 404


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected() -> None:
    assert APIClient().get("/api/evaluations/").status_code in (401, 403)
