from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from vacation.application.dto import RequestVacationCommand, ResubmitVacationCommand
from vacation.application.service import VacationService
from vacation.infrastructure.models import LeaveBalanceModel, LeaveRequestModel, LeaveTypeModel
from vacation.infrastructure.repositories import DjangoVacationUnitOfWork
from vacation.infrastructure.workforce_gateways import (
    DjangoLeaveBalanceGateway,
    DjangoWorkforceGateway,
)
from workforce.application.services import resolve_vacation_approver
from workforce.infrastructure.gateways import DjangoWorkforceQueryGateway
from workforce.infrastructure.models import Department, Employee, Person, Position


def employee(number: int, department: Department) -> Employee:
    position, _ = Position.objects.get_or_create(
        position_code="STAFF", defaults={"position_name": "사원", "sort_order": 1}
    )
    return Employee.objects.create(
        employee_no=number,
        person=Person.objects.create(name=f"합성 사원 {number}"),
        department=department,
        position=position,
        tenure_status="재직",
        email=f"synthetic{number}@example.com",
        hire_date=date(2024, 1, 1),
    )


@pytest.fixture
def vacation(db):
    department = Department.objects.create(dept_no=10, dept_name="합성 부서")
    applicant = employee(1001, department)
    head = employee(2001, department)
    department.head = head
    department.save(update_fields=["head"])
    kind = LeaveTypeModel.objects.create(
        type_id="ANNUAL", type_name="연차", deduct_days=1
    )
    balance = LeaveBalanceModel.objects.create(
        employee=applicant, vacation_type=kind, remaining_days=1
    )
    service = VacationService(
        DjangoVacationUnitOfWork, DjangoWorkforceGateway(),
        DjangoLeaveBalanceGateway(), timezone.now
    )
    return service, balance


def command(type_id="ANNUAL", reason="최초 신청"):
    return RequestVacationCommand(
        1001, type_id, datetime(2026, 10, 1, tzinfo=UTC),
        datetime(2026, 10, 2, tzinfo=UTC), Decimal("1.00"), reason
    )


def test_lv008_resubmission_preserves_before_and_after_values(vacation):
    service, _ = vacation
    item = service.request_vacation(command())
    service.approve(item.request_id, 2001)
    service.recall(item.request_id, 2001, "일정 정정")
    service.resubmit(ResubmitVacationCommand(
        item.request_id, 1001, "ANNUAL", datetime(2026, 10, 3, tzinfo=UTC),
        datetime(2026, 10, 4, tzinfo=UTC), Decimal("0.50"), "정정 신청"
    ))
    entries = service.history(item.request_id, 1001)
    assert entries[0].before_values is None
    assert entries[0].after_values["request_reason"] == "최초 신청"
    assert entries[-1].before_values["use_days"] == "1.00"
    assert entries[-1].after_values["use_days"] == "0.50"
    assert entries[-1].before_values["start_datetime"].startswith("2026-10-01")
    assert entries[-1].after_values["start_datetime"].startswith("2026-10-03")
    response = APIClient().get(
        f"/api/vacations/requests/{item.request_id}/history/", HTTP_X_EMPLOYEE_NO="1001"
    )
    assert response.status_code == 200
    assert response.json()[-1]["before_values"]["request_reason"] == "최초 신청"


@pytest.mark.parametrize("operation", ["request", "resubmit"])
def test_database_api_reports_nonexistent_type_as_404(vacation, operation):
    from accounts.models import User

    service, balance = vacation
    client = APIClient()
    client.force_authenticate(User.objects.create_user(
        email="user@example.com", employee=balance.employee
    ))
    url = "/api/vacations/requests/"
    method = client.post
    if operation == "resubmit":
        item = service.request_vacation(command())
        service.approve(item.request_id, 2001)
        service.recall(item.request_id, 2001, "정정")
        url = f"/api/vacations/requests/{item.request_id}/resubmit/"
        method = client.put
    with override_settings(VACATION_INTEGRATION_MODE="database"):
        response = method(url, {
            "type_id": "MISSING", "start_datetime": "2026-10-03T09:00:00+09:00",
            "end_datetime": "2026-10-03T18:00:00+09:00", "use_days": "1.00"
        }, format="json")
    assert response.status_code == 404
    assert response.json()["code"] == "type_not_found"


@pytest.mark.django_db
@pytest.mark.parametrize("number", ["999999", "1001"])
def test_types_reject_unknown_or_inactive_development_employee(number):
    with override_settings(VACATION_DEVELOPMENT_EMPLOYEES={"1001": {"active": False}}):
        response = APIClient().get("/api/vacations/types/", HTTP_X_EMPLOYEE_NO=number)
    assert response.status_code == 400
    assert response.json()["code"] == "inactive_employee"


@pytest.mark.parametrize("length, expected", [(255, 201), (256, 400)])
def test_request_reason_length_is_validated_before_writes(vacation, length, expected):
    response = APIClient().post("/api/vacations/requests/", {
        "type_id": "ANNUAL", "start_datetime": "2026-10-01T09:00:00+09:00",
        "end_datetime": "2026-10-01T18:00:00+09:00", "use_days": "1.00",
        "reason": "가" * length
    }, format="json", HTTP_X_EMPLOYEE_NO="1001")
    assert response.status_code == expected
    assert LeaveRequestModel.objects.count() == (1 if expected == 201 else 0)


def test_lv004_department_head_is_approved_by_parent_head(vacation):
    service, balance = vacation
    parent = Department.objects.create(dept_no=20, dept_name="상위 부서")
    upper = employee(3001, parent)
    parent.head = upper
    parent.save(update_fields=["head"])
    department = balance.employee.department
    department.parent = parent
    department.save(update_fields=["parent"])
    assert resolve_vacation_approver(2001, DjangoWorkforceQueryGateway()) == 3001
    assert service.workforce.resolve_vacation_approver(2001) == 3001


def test_lv001_approval_rechecks_and_consumes_balance(vacation):
    from vacation.domain.exceptions import InsufficientLeaveDaysError

    service, balance = vacation
    first = service.request_vacation(command())
    second = service.request_vacation(command())
    service.approve(first.request_id, 2001)
    with pytest.raises(InsufficientLeaveDaysError):
        service.approve(second.request_id, 2001)
    balance.refresh_from_db()
    assert balance.remaining_days == 0
    assert LeaveRequestModel.objects.get(pk=second.request_id).status == "대기"
    assert len(service.history(second.request_id, 1001)) == 1
    service.recall(first.request_id, 2001, "정정")
    balance.refresh_from_db()
    assert balance.remaining_days == 1
    service.approve(second.request_id, 2001)
    balance.refresh_from_db()
    assert balance.remaining_days == 0


def test_lv001_failed_history_write_rolls_back_balance_and_status(vacation, monkeypatch):
    from vacation.infrastructure.repositories import DjangoVacationHistoryRepository

    service, balance = vacation
    item = service.request_vacation(command())

    def fail_history(*args):
        raise RuntimeError("합성 이력 저장 실패")

    monkeypatch.setattr(DjangoVacationHistoryRepository, "add", fail_history)
    with pytest.raises(RuntimeError):
        service.approve(item.request_id, 2001)
    balance.refresh_from_db()
    model = LeaveRequestModel.objects.get(pk=item.request_id)
    assert balance.remaining_days == 1
    assert model.status == "대기"
    assert not model.balance_deducted
    assert len(service.history(item.request_id, 1001)) == 1


def test_legacy_approval_recall_does_not_refund_uncharged_days(vacation):
    service, balance = vacation
    item = service.request_vacation(command())
    LeaveRequestModel.objects.filter(pk=item.request_id).update(status="승인")
    service.recall(item.request_id, 2001, "기존 승인 정정")
    balance.refresh_from_db()
    assert balance.remaining_days == 1


def test_non_deducting_leave_can_be_approved_without_balance(vacation):
    service, balance = vacation
    LeaveTypeModel.objects.create(type_id="SICK", type_name="병가", deduct_days=0)
    item = service.request_vacation(command("SICK"))
    service.approve(item.request_id, 2001)
    assert not LeaveRequestModel.objects.get(pk=item.request_id).balance_deducted
    service.recall(item.request_id, 2001, "정정")
    balance.refresh_from_db()
    assert balance.remaining_days == 1


def test_development_approvals_consume_configured_allowance(vacation):
    from vacation.domain.exceptions import InsufficientLeaveDaysError
    from vacation.infrastructure.development_gateways import SettingsLeaveBalanceGateway

    service, _ = vacation
    service.balances = SettingsLeaveBalanceGateway()
    with override_settings(VACATION_DEVELOPMENT_EMPLOYEES={
        "1001": {"balances": {"ANNUAL": 1}}
    }):
        first = service.request_vacation(command())
        second = service.request_vacation(command())
        service.approve(first.request_id, 2001)
        with pytest.raises(InsufficientLeaveDaysError):
            service.approve(second.request_id, 2001)
        service.recall(first.request_id, 2001, "정정")
        service.approve(second.request_id, 2001)
        assert service.balances.remaining_days(1001, "ANNUAL") == 0


@pytest.mark.parametrize("action, actor", [("approve", 1001), ("recall", 1001)])
def test_unauthorized_transition_never_changes_balance(vacation, action, actor):
    from vacation.domain.exceptions import VacationPermissionError

    service, balance = vacation
    item = service.request_vacation(command())
    if action == "recall":
        service.approve(item.request_id, 2001)
    before = service.balances.remaining_days(1001, "ANNUAL")
    with pytest.raises(VacationPermissionError):
        if action == "recall":
            service.recall(item.request_id, actor, "정정")
        else:
            service.approve(item.request_id, actor)
    balance.refresh_from_db()
    assert balance.remaining_days == before


def test_recall_history_failure_rolls_back_refund(vacation, monkeypatch):
    from vacation.infrastructure.repositories import DjangoVacationHistoryRepository

    service, balance = vacation
    item = service.request_vacation(command())
    service.approve(item.request_id, 2001)

    def fail_history(*args):
        raise RuntimeError("합성 이력 저장 실패")

    monkeypatch.setattr(DjangoVacationHistoryRepository, "add", fail_history)
    with pytest.raises(RuntimeError):
        service.recall(item.request_id, 2001, "정정")
    balance.refresh_from_db()
    stored = LeaveRequestModel.objects.get(pk=item.request_id)
    assert balance.remaining_days == 0
    assert stored.status == "승인"
    assert stored.balance_deducted


def test_database_approval_api_maps_balance_shortage(vacation):
    from accounts.models import User

    service, balance = vacation
    first = service.request_vacation(command())
    second = service.request_vacation(command())
    service.approve(first.request_id, 2001)
    user = User.objects.create_user(
        email="synthetic-approver@example.com", employee=Employee.objects.get(pk=2001)
    )
    client = APIClient()
    client.force_authenticate(user)
    with override_settings(VACATION_INTEGRATION_MODE="database"):
        response = client.post(f"/api/vacations/requests/{second.request_id}/approve/")
    assert response.status_code == 400
    assert response.json()["code"] == "insufficient_leave_days"
    assert LeaveRequestModel.objects.get(pk=second.request_id).status == "대기"


@pytest.mark.parametrize("action", ["cancel", "reject"])
def test_pending_cancel_and_reject_leave_balance_unchanged(vacation, action):
    service, balance = vacation
    item = service.request_vacation(command())
    if action == "cancel":
        service.cancel(item.request_id, 1001)
    else:
        service.reject(item.request_id, 2001, "반려")
    balance.refresh_from_db()
    assert balance.remaining_days == 1
    assert not LeaveRequestModel.objects.get(pk=item.request_id).balance_deducted
