from datetime import date

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from evaluation.infrastructure.models import EvaluationHistoryModel, EvaluationModel
from workforce.application.services import HR_MANAGER_ROLE
from workforce.infrastructure.models import (
    Department,
    Employee,
    EmployeeRole,
    EmploymentHistory,
    Person,
    Position,
    Role,
)


def current_year() -> str:
    return str(timezone.localdate().year)


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
    user = User.objects.filter(employee=employee).first() or User.objects.create_user(
        email=employee.email,
        password="safe-test-password",
        employee=employee,
    )
    client = APIClient()
    client.force_authenticate(user)
    return client


def make_hr_manager(employee: Employee) -> None:
    role, _ = Role.objects.get_or_create(
        role_code=HR_MANAGER_ROLE, defaults={"role_name": "인사관리자"}
    )
    EmployeeRole.objects.create(employee=employee, role=role, assigned_at=timezone.now())


@pytest.fixture
def org() -> dict[str, Employee]:
    division = Department.objects.create(dept_no=1, dept_name="기술본부")
    parent_head = create_employee(5001, "director@example.com", department=division)
    division.head = parent_head
    division.save(update_fields=["head"])
    department = Department.objects.create(dept_no=10, dept_name="개발팀", parent=division)
    head = create_employee(2001, "head@example.com", department=department)
    department.head = head
    department.save(update_fields=["head"])
    member = create_employee(1001, "member@example.com", department=department)
    new_head = create_employee(2002, "newhead@example.com", department=department)
    Department.objects.create(dept_no=30, dept_name="기획팀", parent=division, head=new_head)
    other = create_employee(3001, "other@example.com")
    hr = create_employee(9001, "hr@example.com")
    make_hr_manager(hr)
    return {
        "parent_head": parent_head,
        "head": head,
        "new_head": new_head,
        "member": member,
        "other": other,
        "hr": hr,
    }


def create_evaluation(client: APIClient, emp_no: int = 1001, score: str = "85.5", year=None):
    return client.post(
        "/api/evaluations/",
        {"emp_no": emp_no, "eval_year": year or current_year(), "score": score, "comments": "우수"},
        format="json",
    )


def create_submitted(org) -> int:
    head = client_for(org["head"])
    eval_id = create_evaluation(head).data["eval_id"]
    assert head.post(f"/api/evaluations/{eval_id}/submit/").status_code == 200
    return eval_id


# Creation --------------------------------------------------------------------------


@pytest.mark.django_db
def test_department_head_creates_evaluation_with_grade_and_snapshot(org) -> None:
    response = create_evaluation(client_for(org["head"]), score="85.5")

    assert response.status_code == 201, response.data
    assert response.data["grade"] == "A"
    assert response.data["score"] == "85.50"
    assert response.data["eval_status"] == "작성중"
    assert response.data["snapshot_dept_no"] == 10
    assert response.data["evaluator_no"] == 2001
    assert response.data["created_by"] == 2001
    assert EvaluationHistoryModel.objects.filter(action="CREATE").count() == 1


@pytest.mark.django_db
def test_parent_department_head_evaluates_department_head(org) -> None:
    parent_head = client_for(org["parent_head"])

    response = create_evaluation(parent_head, emp_no=2001, score="90")
    assert response.status_code == 201, response.data
    assert response.data["evaluator_no"] == 5001
    assert create_evaluation(parent_head, emp_no=1001).status_code == 403


@pytest.mark.django_db
def test_employee_on_leave_can_be_evaluated(org) -> None:
    create_employee(
        1003,
        "leave@example.com",
        department=org["member"].department,
        tenure_status=Employee.TenureStatus.LEAVE,
    )
    response = create_evaluation(client_for(org["head"]), emp_no=1003)
    assert response.status_code == 201, response.data


@pytest.mark.django_db
def test_previous_year_uses_year_end_department(org) -> None:
    """A member who moved on 1 January is evaluated for last year by the former department."""
    year = int(current_year())
    sales = Department.objects.create(dept_no=20, dept_name="영업팀")
    sales_head = create_employee(2020, "sales@example.com", department=sales)
    sales.head = sales_head
    sales.save(update_fields=["head"])
    member = org["member"]
    member.department = sales
    member.save(update_fields=["department"])
    position = member.position
    EmploymentHistory.objects.create(
        employee=member,
        start_date=date(year - 1, 1, 1),
        end_date=date(year - 1, 12, 31),
        department=org["head"].department,
        position=position,
    )
    EmploymentHistory.objects.create(
        employee=member, start_date=date(year, 1, 1), department=sales, position=position
    )

    former_head = client_for(org["head"])
    new_head = client_for(sales_head)
    last_year = str(year - 1)

    assert create_evaluation(new_head, year=last_year).status_code == 403
    response = create_evaluation(former_head, year=last_year)
    assert response.status_code == 201, response.data
    assert response.data["snapshot_dept_no"] == 10

    this_year = create_evaluation(new_head)
    assert this_year.status_code == 201, this_year.data
    assert this_year.data["snapshot_dept_no"] == 20


@pytest.mark.django_db
def test_hr_manager_cannot_see_own_unconfirmed_evaluation(org) -> None:
    department = org["member"].department
    org["hr"].department = department
    org["hr"].save(update_fields=["department"])
    hr = client_for(org["hr"])
    hr_2 = create_employee(9002, "hr2@example.com")
    make_hr_manager(hr_2)

    head = client_for(org["head"])
    eval_id = create_evaluation(head, emp_no=9001).data["eval_id"]
    head.post(f"/api/evaluations/{eval_id}/submit/")

    assert hr.get(f"/api/evaluations/{eval_id}/").status_code == 404
    assert hr.get(f"/api/evaluations/{eval_id}/history/").status_code == 404
    assert eval_id not in [item["eval_id"] for item in hr.get("/api/evaluations/").data]

    client_for(hr_2).post(f"/api/evaluations/{eval_id}/confirm/")
    assert hr.get(f"/api/evaluations/{eval_id}/").status_code == 200
    assert hr.get(f"/api/evaluations/{eval_id}/history/").status_code == 403


@pytest.mark.django_db
def test_outsider_gets_identical_response_for_any_target(org) -> None:
    create_employee(1002, "retired@example.com", tenure_status=Employee.TenureStatus.TERMINATED)
    other = client_for(org["other"])

    responses = [create_evaluation(other, emp_no=emp_no) for emp_no in (4040, 1002, 1001, 2001)]
    assert {response.status_code for response in responses} == {403}
    assert len({(r.data["code"], r.data["detail"]) for r in responses}) == 1


@pytest.mark.django_db
def test_creation_year_window(org) -> None:
    head = client_for(org["head"])
    year = int(current_year())

    too_old = create_evaluation(head, year=str(year - 2))
    assert too_old.status_code == 400
    assert too_old.data["code"] == "eval_year_not_allowed"
    assert create_evaluation(head, year=str(year + 1)).status_code == 400
    assert create_evaluation(head, year=str(year - 1)).status_code == 201


@pytest.mark.django_db
def test_duplicate_year_evaluation_conflicts(org) -> None:
    head = client_for(org["head"])
    assert create_evaluation(head).status_code == 201
    response = create_evaluation(head)
    assert response.status_code == 409
    assert response.data["code"] == "duplicate_evaluation"


@pytest.mark.django_db
def test_database_rejects_duplicate_employee_year(org) -> None:
    create_evaluation(client_for(org["head"]))
    existing = EvaluationModel.objects.get()

    with pytest.raises(IntegrityError), transaction.atomic():
        EvaluationModel.objects.create(
            employee=existing.employee,
            eval_year=existing.eval_year,
            evaluator=existing.evaluator,
            score=existing.score,
            grade=existing.grade,
            updated_at=timezone.now(),
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"emp_no": 1001, "score": "100.01"},
        {"emp_no": 1001, "eval_year": "26", "score": "80"},
        {"emp_no": 1001, "score": "80.123"},
        {"emp_no": 1001},
    ],
)
def test_invalid_payload_is_rejected(org, payload) -> None:
    payload.setdefault("eval_year", current_year())
    response = client_for(org["head"]).post("/api/evaluations/", payload, format="json")
    assert response.status_code == 400


# Workflow --------------------------------------------------------------------------


@pytest.mark.django_db
def test_full_workflow_with_return_and_confirmation(org) -> None:
    head = client_for(org["head"])
    hr = client_for(org["hr"])
    eval_id = create_submitted(org)

    locked = head.patch(f"/api/evaluations/{eval_id}/", {"score": "70"}, format="json")
    assert locked.status_code == 409

    assert hr.post(f"/api/evaluations/{eval_id}/return/", {}, format="json").status_code == 400
    returned = hr.post(
        f"/api/evaluations/{eval_id}/return/", {"reason": "근거 보완"}, format="json"
    )
    assert returned.data["eval_status"] == "반려"

    revised = head.patch(f"/api/evaluations/{eval_id}/", {"score": "69.99"}, format="json")
    assert revised.status_code == 200
    assert revised.data["grade"] == "C"
    assert revised.data["comments"] == "우수"
    assert head.post(f"/api/evaluations/{eval_id}/submit/").data["eval_status"] == "제출"

    assert head.post(f"/api/evaluations/{eval_id}/confirm/").status_code == 403
    confirmed = hr.post(f"/api/evaluations/{eval_id}/confirm/")
    assert confirmed.status_code == 200
    assert confirmed.data["eval_status"] == "확정"
    assert confirmed.data["confirmed_by"] == 9001

    late = head.patch(f"/api/evaluations/{eval_id}/", {"score": "95"}, format="json")
    assert late.status_code == 409

    history = hr.get(f"/api/evaluations/{eval_id}/history/").data
    assert [entry["action"] for entry in history] == [
        "CREATE",
        "SUBMIT",
        "RETURN",
        "REVISE",
        "SUBMIT",
        "CONFIRM",
    ]
    assert history[2]["reason"] == "근거 보완"


@pytest.mark.django_db
def test_reassignment_moves_access_to_new_evaluator(org) -> None:
    head = client_for(org["head"])
    new_head = client_for(org["new_head"])
    hr = client_for(org["hr"])
    eval_id = create_submitted(org)

    assert new_head.get(f"/api/evaluations/{eval_id}/").status_code == 404
    missing_reason = hr.post(
        f"/api/evaluations/{eval_id}/reassign/", {"evaluator_no": 2002}, format="json"
    )
    assert missing_reason.status_code == 400

    reassigned = hr.post(
        f"/api/evaluations/{eval_id}/reassign/",
        {"evaluator_no": 2002, "reason": "부서장 교체"},
        format="json",
    )
    assert reassigned.status_code == 200, reassigned.data
    assert reassigned.data["evaluator_no"] == 2002
    assert reassigned.data["created_by"] == 2001
    assert reassigned.data["eval_status"] == "작성중"

    assert head.get(f"/api/evaluations/{eval_id}/").status_code == 404
    assert head.get("/api/evaluations/").data == []
    stale = head.patch(f"/api/evaluations/{eval_id}/", {"score": "70"}, format="json")
    assert stale.status_code == 404

    assert new_head.get(f"/api/evaluations/{eval_id}/").data["comments"] == "우수"
    assert new_head.post(f"/api/evaluations/{eval_id}/submit/").status_code == 200

    entry = EvaluationHistoryModel.objects.get(action="REASSIGN")
    assert (entry.from_evaluator_id, entry.to_evaluator_id, entry.reason) == (
        2001,
        2002,
        "부서장 교체",
    )


@pytest.mark.django_db
def test_former_evaluator_who_became_hr_manager_cannot_confirm(org) -> None:
    head = client_for(org["head"])
    hr = client_for(org["hr"])
    eval_id = create_evaluation(head).data["eval_id"]
    make_hr_manager(org["head"])

    hr.post(
        f"/api/evaluations/{eval_id}/reassign/",
        {"evaluator_no": 2002, "reason": "역할 변경"},
        format="json",
    )
    client_for(org["new_head"]).post(f"/api/evaluations/{eval_id}/submit/")

    blocked = head.post(f"/api/evaluations/{eval_id}/confirm/")
    assert blocked.status_code == 403
    assert blocked.data["code"] == "confirmation_not_allowed"
    assert hr.post(f"/api/evaluations/{eval_id}/confirm/").status_code == 200


@pytest.mark.django_db
def test_fn_ev_001_hr_manager_is_never_an_evaluator(org) -> None:
    hr = client_for(org["hr"])
    hr_2 = create_employee(9002, "hr2@example.com")
    make_hr_manager(hr_2)

    # An HR manager who heads the department cannot write the evaluation.
    department = org["member"].department
    department.head = org["hr"]
    department.save(update_fields=["head"])
    blocked = create_evaluation(hr)
    assert blocked.status_code == 403
    assert blocked.data["code"] == "hr_manager_cannot_evaluate"

    department.head = org["head"]
    department.save(update_fields=["head"])
    eval_id = create_evaluation(client_for(org["head"])).data["eval_id"]
    for evaluator_no in (9001, 9002):
        response = hr.post(
            f"/api/evaluations/{eval_id}/reassign/",
            {"evaluator_no": evaluator_no, "reason": "사유"},
            format="json",
        )
        assert response.status_code == 403
        assert response.data["code"] == "hr_manager_cannot_evaluate"
    assert EvaluationModel.objects.get(eval_id=eval_id).evaluator_id == 2001


@pytest.mark.django_db
def test_reassignment_only_to_department_heads_via_candidate_list(org) -> None:
    hr = client_for(org["hr"])
    eval_id = create_evaluation(client_for(org["head"])).data["eval_id"]

    candidates = hr.get("/api/evaluations/evaluator-candidates/")
    assert candidates.status_code == 200
    candidate_nos = {item["emp_no"] for item in candidates.data}
    assert {2001, 2002, 5001} <= candidate_nos
    assert 9001 not in candidate_nos and 3001 not in candidate_nos
    assert client_for(org["head"]).get("/api/evaluations/evaluator-candidates/").status_code == 403

    not_head = hr.post(
        f"/api/evaluations/{eval_id}/reassign/",
        {"evaluator_no": 3001, "reason": "사유"},
        format="json",
    )
    assert not_head.status_code == 403
    assert not_head.data["code"] == "evaluator_must_be_department_head"


@pytest.mark.django_db
def test_hr_actions_hide_own_unconfirmed_evaluation(org) -> None:
    department = org["member"].department
    org["hr"].department = department
    org["hr"].save(update_fields=["department"])
    head = client_for(org["head"])
    eval_id = create_evaluation(head, emp_no=9001).data["eval_id"]
    head.post(f"/api/evaluations/{eval_id}/submit/")

    hr = client_for(org["hr"])
    # README: the target may not confirm -> 403 confirmation_not_allowed.
    confirm = hr.post(f"/api/evaluations/{eval_id}/confirm/")
    assert confirm.status_code == 403
    assert confirm.data["code"] == "confirmation_not_allowed"
    # README EV-005: the other HR actions keep the evaluation hidden.
    returned = hr.post(f"/api/evaluations/{eval_id}/return/", {"reason": "사유"}, format="json")
    assert returned.status_code == 404
    assert EvaluationModel.objects.get(eval_id=eval_id).eval_status == "제출"


@pytest.mark.django_db
def test_exclusion_and_cancellation(org) -> None:
    hr = client_for(org["hr"])
    eval_id = create_submitted(org)

    assert hr.post(f"/api/evaluations/{eval_id}/exclude/", {}, format="json").status_code == 400
    excluded = hr.post(
        f"/api/evaluations/{eval_id}/exclude/", {"reason": "장기 휴직"}, format="json"
    )
    assert excluded.data["eval_status"] == "제외"
    assert hr.post(f"/api/evaluations/{eval_id}/confirm/").status_code == 409

    restored = hr.post(f"/api/evaluations/{eval_id}/cancel-exclusion/", {}, format="json")
    assert restored.status_code == 200
    assert restored.data["eval_status"] == "제출"


@pytest.mark.django_db
def test_confirmed_evaluation_is_corrected_by_cancel_and_reconfirm(org) -> None:
    head = client_for(org["head"])
    hr = client_for(org["hr"])
    member = client_for(org["member"])
    eval_id = create_submitted(org)
    hr.post(f"/api/evaluations/{eval_id}/confirm/")

    direct = head.patch(f"/api/evaluations/{eval_id}/", {"score": "75"}, format="json")
    assert direct.status_code == 409
    no_reason = hr.post(f"/api/evaluations/{eval_id}/cancel-confirmation/", {}, format="json")
    assert no_reason.status_code == 400

    cancelled = hr.post(
        f"/api/evaluations/{eval_id}/cancel-confirmation/",
        {"reason": "점수 오기 정정"},
        format="json",
    )
    assert cancelled.status_code == 200, cancelled.data
    assert cancelled.data["eval_status"] == "반려"
    assert cancelled.data["confirmed_by"] is None
    assert member.get(f"/api/evaluations/{eval_id}/").status_code == 404

    revised = head.patch(f"/api/evaluations/{eval_id}/", {"score": "75"}, format="json")
    assert revised.status_code == 200
    head.post(f"/api/evaluations/{eval_id}/submit/")
    reconfirmed = hr.post(f"/api/evaluations/{eval_id}/confirm/")
    assert reconfirmed.data["eval_status"] == "확정"
    assert reconfirmed.data["grade"] == "B"

    entry = EvaluationHistoryModel.objects.get(action="CANCEL_CONFIRMATION")
    assert (entry.from_status, entry.to_status, entry.reason) == ("확정", "반려", "점수 오기 정정")


# Visibility ------------------------------------------------------------------------


@pytest.mark.django_db
def test_target_sees_evaluation_only_after_confirmation(org) -> None:
    member = client_for(org["member"])
    other = client_for(org["other"])
    eval_id = create_submitted(org)

    assert member.get(f"/api/evaluations/{eval_id}/").status_code == 404
    assert member.get("/api/evaluations/").data == []
    assert other.get(f"/api/evaluations/{eval_id}/").status_code == 404

    client_for(org["hr"]).post(f"/api/evaluations/{eval_id}/confirm/")

    assert member.get(f"/api/evaluations/{eval_id}/").status_code == 200
    assert [item["eval_id"] for item in member.get("/api/evaluations/").data] == [eval_id]
    assert member.get(f"/api/evaluations/{eval_id}/history/").status_code == 403
    assert other.get("/api/evaluations/").data == []


@pytest.mark.django_db
def test_hr_manager_lists_all_and_filters_by_year(org) -> None:
    create_evaluation(client_for(org["head"]))
    hr = client_for(org["hr"])

    assert len(hr.get("/api/evaluations/").data) == 1
    assert len(hr.get(f"/api/evaluations/?year={current_year()}").data) == 1
    assert hr.get("/api/evaluations/?year=1999").data == []
    assert hr.get("/api/evaluations/?year=abc").status_code == 400


@pytest.mark.django_db
def test_missing_evaluation_returns_404(org) -> None:
    assert client_for(org["hr"]).get("/api/evaluations/999/").status_code == 404


@pytest.mark.django_db
def test_unauthenticated_request_is_rejected() -> None:
    assert APIClient().get("/api/evaluations/").status_code in (401, 403)


def test_evaluation_admin_is_read_only() -> None:
    from django.contrib.admin.sites import site
    from django.test import RequestFactory

    request = RequestFactory().get("/admin/")
    for model in (EvaluationModel, EvaluationHistoryModel):
        model_admin = site._registry[model]
        assert not model_admin.has_add_permission(request)
        assert not model_admin.has_change_permission(request)
        assert not model_admin.has_delete_permission(request)
