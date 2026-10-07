from datetime import date, datetime

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from workforce.application.services import HR_MANAGER_ROLE
from workforce.domain.exceptions import WorkforceRuleViolation
from workforce.domain.personal_info import (
    ApprovalRequiredValues,
    ChangeRequestStatus,
    PersonalInfoChangeRequest,
    ProcessorAssignment,
    resolve_change_request_processor,
    validate_change_request_values,
    validate_self_editable_fields,
)
from workforce.domain.policies import EmployeeCandidate
from workforce.infrastructure.models import Department, Employee, EmployeeRole, Person, Role
from workforce.infrastructure.models import (
    PersonalInfoChangeRequest as PersonalInfoChangeRequestModel,
)

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
    assert client_for(other).post(f"{url}/cancel/").status_code == 404
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


@pytest.mark.django_db
def test_hr_007_employee_number_cannot_be_changed(staff: User, manager: User) -> None:
    response = client_for(manager).patch(
        "/api/workforce/employees/1001/", {"emp_no": 5555}, format="json"
    )

    assert response.status_code == 400
    assert sorted(Employee.objects.values_list("employee_no", flat=True)) == [1001, 9001]


@pytest.mark.django_db
def test_hr_007_same_employee_number_in_update_is_allowed(staff: User, manager: User) -> None:
    response = client_for(manager).patch(
        "/api/workforce/employees/1001/", {"emp_no": 1001, "phone": "010-2222-3333"}, format="json"
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_hr_004_request_of_terminated_employee_cannot_be_approved(
    staff: User, manager: User
) -> None:
    created = client_for(staff).post(
        "/api/workforce/personal-info-requests/",
        {"bank_code": "088", "account_no": "222-222"},
        format="json",
    ).json()
    Employee.objects.filter(employee_no=1001).update(
        tenure_status=Employee.TenureStatus.TERMINATED, term_date=date(2026, 10, 1)
    )

    url = f"/api/workforce/personal-info-requests/{created['request_id']}"
    approved = client_for(manager).post(f"{url}/approve/")

    assert approved.status_code == 400
    staff.employee.refresh_from_db()
    assert staff.employee.account_no == "111-111"
    assert client_for(manager).get(f"{url}/").json()["status"] == "대기"
    assert client_for(manager).post(f"{url}/reject/").json()["status"] == "반려"


@pytest.mark.django_db
def test_hr_003_hr_manager_cannot_directly_change_email(staff: User, manager: User) -> None:
    response = client_for(manager).patch(
        "/api/workforce/employees/1001/", {"email": "direct@example.com"}, format="json"
    )

    assert response.status_code == 400
    staff.employee.refresh_from_db()
    assert staff.employee.email == "user1001@example.com"
    unchanged = client_for(manager).patch(
        "/api/workforce/employees/1001/", {"email": "USER1001@example.com"}, format="json"
    )
    assert unchanged.status_code == 200


# --- FN-HR-004 처리자: 인사관리자 본인 요청은 상급자(소속 부서장)가 승인 시점 기준으로 처리 ----


def test_fn_hr_004_processor_resolution() -> None:
    assert resolve_change_request_processor(
        requester_is_hr_manager=False, department_head=None
    ) == ProcessorAssignment(any_hr_manager=True)
    assert resolve_change_request_processor(
        requester_is_hr_manager=True,
        department_head=EmployeeCandidate(2001, True),
        department_head_is_hr_manager=True,
    ) == ProcessorAssignment(employee_no=2001)
    assert resolve_change_request_processor(
        requester_is_hr_manager=True,
        department_head=EmployeeCandidate(2001, False),
        department_head_is_hr_manager=True,
    ) == ProcessorAssignment()
    # 상급자가 인사관리자가 아니면 급여계좌 노출을 막기 위해 superuser만 처리한다.
    assert resolve_change_request_processor(
        requester_is_hr_manager=True,
        department_head=EmployeeCandidate(2001, True),
        department_head_is_hr_manager=False,
    ) == ProcessorAssignment()
    superuser_only = ProcessorAssignment()
    assert not superuser_only.allows(
        actor_employee_no=2001, actor_is_hr_manager=True, actor_is_superuser=False
    )
    assert superuser_only.allows(
        actor_employee_no=None, actor_is_hr_manager=False, actor_is_superuser=True
    )


def submit_account_change(user: User) -> str:
    created = client_for(user).post(
        "/api/workforce/personal-info-requests/",
        {"bank_code": "088", "account_no": "222-222"},
        format="json",
    )
    assert created.status_code == 201
    return f"/api/workforce/personal-info-requests/{created.json()['request_id']}"


@pytest.mark.django_db
def test_fn_hr_004_hr_manager_request_is_processed_by_department_head(manager: User) -> None:
    head = create_user(2001)
    grant_hr_manager(head)
    department = Department.objects.create(dept_no=20, dept_name="인사팀", head=head.employee)
    Employee.objects.filter(employee_no__in=[2001, 9001]).update(department=department)
    other_manager = create_user(9002)
    grant_hr_manager(other_manager)
    url = submit_account_change(manager)

    assert client_for(manager).post(f"{url}/approve/").status_code == 403
    assert client_for(other_manager).post(f"{url}/approve/").status_code == 403
    assert client_for(other_manager).get(f"{url}/").json()["can_process"] is False

    queue = client_for(head).get("/api/workforce/personal-info-requests/?processable=true")
    assert [item["emp_no"] for item in queue.json()] == [9001]
    assert client_for(head).get(f"{url}/").json()["can_process"] is True
    approved = client_for(head).post(f"{url}/approve/")
    assert approved.status_code == 200
    assert approved.json()["processed_by"] == 2001


@pytest.mark.django_db
def test_fn_hr_004_hr_department_head_processes_own_request(manager: User) -> None:
    department = Department.objects.create(dept_no=20, dept_name="인사팀", head=manager.employee)
    Employee.objects.filter(employee_no=9001).update(department=department)
    url = submit_account_change(manager)

    assert client_for(manager).post(f"{url}/approve/").status_code == 200


@pytest.mark.django_db
def test_fn_hr_004_superuser_processes_when_no_active_superior(manager: User) -> None:
    head = create_user(2001)
    grant_hr_manager(head)
    department = Department.objects.create(dept_no=20, dept_name="인사팀", head=head.employee)
    Employee.objects.filter(employee_no=9001).update(department=department)
    url = submit_account_change(manager)
    # 처리자는 승인 시점에 결정된다: 요청 후 상급자가 퇴사하면 superuser만 처리할 수 있다.
    Employee.objects.filter(employee_no=2001).update(
        tenure_status=Employee.TenureStatus.TERMINATED, term_date=date(2026, 10, 1)
    )
    admin = User.objects.create_superuser(email="admin@example.com", password="safe-test-password")

    assert client_for(manager).post(f"{url}/approve/").status_code == 403
    assert client_for(head).post(f"{url}/approve/").status_code == 403
    assert client_for(admin).post(f"{url}/reject/").json()["status"] == "반려"


@pytest.mark.django_db
def test_fn_hr_004_superior_without_hr_role_cannot_process(manager: User) -> None:
    head = create_user(2001)
    department = Department.objects.create(dept_no=30, dept_name="개발팀", head=head.employee)
    Employee.objects.filter(employee_no__in=[2001, 9001]).update(department=department)
    url = submit_account_change(manager)
    admin = User.objects.create_superuser(email="admin@example.com", password="safe-test-password")

    assert client_for(head).post(f"{url}/approve/").status_code == 404
    assert client_for(head).get(f"{url}/").status_code == 404
    queue = client_for(head).get("/api/workforce/personal-info-requests/?processable=true")
    assert queue.json() == []
    assert client_for(admin).post(f"{url}/approve/").status_code == 200


@pytest.mark.django_db
def test_fn_hr_005_mine_lists_only_own_requests_even_for_hr_manager(
    staff: User, manager: User
) -> None:
    client_for(staff).post(
        "/api/workforce/personal-info-requests/", {"email": "a1@example.com"}, format="json"
    )
    submit_account_change(manager)

    mine = client_for(manager).get("/api/workforce/personal-info-requests/?mine=true").json()
    everything = client_for(manager).get("/api/workforce/personal-info-requests/").json()

    assert [item["emp_no"] for item in mine] == [9001]
    assert sorted(item["emp_no"] for item in everything) == [1001, 9001]


@pytest.mark.django_db
def test_unrelated_employee_gets_404_for_processing(staff: User) -> None:
    url = submit_account_change(staff)
    other = create_user(1002)

    for action in ("approve", "reject", "cancel"):
        assert client_for(other).post(f"{url}/{action}/").status_code == 404
    assert client_for(staff).post(f"{url}/approve/").status_code == 403


@pytest.mark.django_db
def test_processable_list_resolves_processor_once_per_requester(manager: User) -> None:
    def count_queries(total: int) -> int:
        for index in range(total):
            submit_account_change(create_user(5000 + total * 100 + index))
        with CaptureQueriesContext(connection) as queries:
            response = client_for(manager).get(
                "/api/workforce/personal-info-requests/?processable=true"
            )
        assert len(response.json()) == total
        return len(queries)

    few = count_queries(2)
    PersonalInfoChangeRequestModel.objects.all().delete()
    many = count_queries(10)

    # 요청자당 처리자 판정은 1회(역할 조회 1건)로 끝나고, 같은 판정을 두 번 하지 않는다.
    assert many - few <= 8
