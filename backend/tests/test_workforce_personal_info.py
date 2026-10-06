from datetime import date, datetime

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.services import HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.personal_info import (
    ApprovalRequiredValues,
    ChangeRequestStatus,
    PersonalInfoChangeRequest,
    validate_change_request_values,
    validate_self_editable_fields,
)
from workforce.infrastructure.models import Employee, EmployeeRole, Person, Role

NOW = datetime(2026, 10, 6, 9, 0)
CURRENT = ApprovalRequiredValues(email="a@example.com", bank_code="004", account_no="111")


def pending_request(employee_no: int = 1001) -> PersonalInfoChangeRequest:
    return PersonalInfoChangeRequest(
        request_id=1,
        employee_no=employee_no,
        previous=CURRENT,
        requested=ApprovalRequiredValues(email="b@example.com"),
        status=ChangeRequestStatus.PENDING,
        requested_at=NOW,
    )


# --- domain ---------------------------------------------------------------------------------


def test_hr_002_employee_may_edit_only_contact_and_address() -> None:
    validate_self_editable_fields({"phone", "address"})
    for forbidden in ("email", "account_no", "bank_code", "tenure_status", "dept_no"):
        with pytest.raises(WorkforceRuleViolation):
            validate_self_editable_fields({"phone", forbidden})


def test_fn_hr_003_account_requires_bank_code_and_number_together() -> None:
    with pytest.raises(WorkforceRuleViolation):
        validate_change_request_values(
            current=CURRENT, requested=ApprovalRequiredValues(account_no="222")
        )


def test_fn_hr_003_rejects_empty_or_unchanged_request() -> None:
    with pytest.raises(WorkforceRuleViolation):
        validate_change_request_values(current=CURRENT, requested=ApprovalRequiredValues())
    with pytest.raises(WorkforceRuleViolation):
        validate_change_request_values(
            current=CURRENT, requested=ApprovalRequiredValues(email="a@example.com")
        )


def test_hr_011_only_pending_requests_can_be_processed() -> None:
    request = pending_request()
    request.approve(9001, NOW)
    assert request.status == ChangeRequestStatus.APPROVED
    assert (request.processed_by, request.processed_at) == (9001, NOW)
    for transition in (
        lambda: request.reject(9001, NOW, "x"),
        lambda: request.cancel(1001, NOW),
        lambda: request.approve(9001, NOW),
    ):
        with pytest.raises(WorkforceRuleViolation):
            transition()


def test_fn_hr_011_only_requester_can_cancel() -> None:
    request = pending_request()
    with pytest.raises(WorkforceRuleViolation):
        request.cancel(1002, NOW)
    request.cancel(1001, NOW)
    assert request.status == ChangeRequestStatus.CANCELLED


# --- API ------------------------------------------------------------------------------------


def create_user(employee_no: int, *, email: str | None = None) -> User:
    person = Person.objects.create(name=f"사원 {employee_no}")
    employee = Employee.objects.create(
        employee_no=employee_no,
        person=person,
        tenure_status=Employee.TenureStatus.ACTIVE,
        email=email or f"user{employee_no}@example.com",
        phone="010-0000-0000",
        address="기존 주소",
        bank_code="004",
        account_no="111-111",
        hire_date=date(2024, 1, 1),
    )
    return User.objects.create_user(
        email=employee.email, password="safe-test-password", employee=employee
    )


def grant_hr_manager(user: User) -> None:
    role, _ = Role.objects.get_or_create(
        role_code=HR_MANAGER_ROLE, defaults={"role_name": "인사 관리자"}
    )
    EmployeeRole.objects.create(employee=user.employee, role=role, assigned_at=timezone.now())


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def staff() -> User:
    return create_user(1001)


@pytest.fixture
def manager() -> User:
    user = create_user(9001)
    grant_hr_manager(user)
    return user


@pytest.mark.django_db
def test_fn_hr_002_employee_updates_own_contact_and_address(staff: User) -> None:
    response = client_for(staff).patch(
        "/api/workforce/employees/me/",
        {"phone": " 010-1234-5678 ", "address": "새 주소"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "010-1234-5678"
    staff.employee.refresh_from_db()
    assert (staff.employee.phone, staff.employee.address) == ("010-1234-5678", "새 주소")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "new@example.com"},
        {"account_no": "999"},
        {"tenure_status": "퇴사"},
        {"phone": "010-9999-9999", "dept_no": 10},
    ],
)
def test_hr_002_employee_cannot_directly_edit_other_fields(
    staff: User, payload: dict[str, object]
) -> None:
    response = client_for(staff).patch("/api/workforce/employees/me/", payload, format="json")

    assert response.status_code == 400
    staff.employee.refresh_from_db()
    assert staff.employee.phone == "010-0000-0000"
    assert staff.employee.email == "user1001@example.com"
    assert staff.employee.account_no == "111-111"


@pytest.mark.django_db
def test_hr_002_employee_cannot_edit_core_info_through_employee_api(staff: User) -> None:
    response = client_for(staff).patch(
        "/api/workforce/employees/1001/", {"tenure_status": "휴직"}, format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_hr_002_hr_manager_edits_core_info(staff: User, manager: User) -> None:
    response = client_for(manager).patch(
        "/api/workforce/employees/1001/", {"tenure_status": "휴직"}, format="json"
    )

    assert response.status_code == 200
    staff.employee.refresh_from_db()
    assert staff.employee.tenure_status == "휴직"


@pytest.mark.django_db
def test_fn_hr_003_to_004_request_is_applied_only_after_approval(
    staff: User, manager: User
) -> None:
    created = client_for(staff).post(
        "/api/workforce/personal-info-requests/",
        {"email": "New@Example.com", "bank_code": "088", "account_no": "222-222"},
        format="json",
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "대기"
    assert body["previous"] == {
        "email": "user1001@example.com",
        "bank_code": "004",
        "account_no": "111-111",
    }
    assert body["requested"]["email"] == "new@example.com"
    staff.employee.refresh_from_db()
    assert staff.employee.account_no == "111-111"

    denied = client_for(staff).post(
        f"/api/workforce/personal-info-requests/{body['request_id']}/approve/"
    )
    assert denied.status_code == 403

    approved = client_for(manager).post(
        f"/api/workforce/personal-info-requests/{body['request_id']}/approve/"
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "승인"
    assert approved.json()["processed_by"] == 9001
    staff.employee.refresh_from_db()
    assert (staff.employee.email, staff.employee.bank_code, staff.employee.account_no) == (
        "new@example.com",
        "088",
        "222-222",
    )


@pytest.mark.django_db
def test_fn_hr_004_reject_keeps_existing_values(staff: User, manager: User) -> None:
    created = client_for(staff).post(
        "/api/workforce/personal-info-requests/",
        {"bank_code": "088", "account_no": "222-222"},
        format="json",
    ).json()

    rejected = client_for(manager).post(
        f"/api/workforce/personal-info-requests/{created['request_id']}/reject/",
        {"reason": "증빙 필요"},
        format="json",
    )

    assert rejected.status_code == 200
    assert rejected.json()["status"] == "반려"
    assert rejected.json()["reject_reason"] == "증빙 필요"
    staff.employee.refresh_from_db()
    assert staff.employee.account_no == "111-111"


@pytest.mark.django_db
def test_fn_hr_003_rejects_duplicate_email(staff: User) -> None:
    create_user(1002, email="taken@example.com")

    response = client_for(staff).post(
        "/api/workforce/personal-info-requests/", {"email": "taken@example.com"}, format="json"
    )

    assert response.status_code == 400
    assert response.json()["field"] == "email"


@pytest.mark.django_db
def test_fn_hr_011_requester_cancels_pending_request(staff: User, manager: User) -> None:
    created = client_for(staff).post(
        "/api/workforce/personal-info-requests/", {"email": "new@example.com"}, format="json"
    ).json()
    url = f"/api/workforce/personal-info-requests/{created['request_id']}"

    other = create_user(1002)
    assert client_for(other).post(f"{url}/cancel/").status_code == 400
    assert (
        client_for(staff)
        .post("/api/workforce/personal-info-requests/", {"email": "x@example.com"}, format="json")
        .status_code
        == 400
    ), "a second pending request is blocked until the first is processed"
    cancelled = client_for(staff).post(f"{url}/cancel/")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "취소"

    assert client_for(manager).post(f"{url}/approve/").status_code == 400


@pytest.mark.django_db
def test_fn_hr_005_employee_sees_only_own_requests(staff: User, manager: User) -> None:
    other = create_user(1002)
    client_for(staff).post(
        "/api/workforce/personal-info-requests/", {"email": "a1@example.com"}, format="json"
    )
    other_request = client_for(other).post(
        "/api/workforce/personal-info-requests/", {"email": "a2@example.com"}, format="json"
    ).json()

    own = client_for(staff).get("/api/workforce/personal-info-requests/").json()
    assert [item["emp_no"] for item in own] == [1001]
    assert (
        client_for(staff)
        .get(f"/api/workforce/personal-info-requests/{other_request['request_id']}/")
        .status_code
        == 404
    )

    pending = client_for(manager).get("/api/workforce/personal-info-requests/?status=대기")
    assert sorted(item["emp_no"] for item in pending.json()) == [1001, 1002]
