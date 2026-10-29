from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from vacation.application.dto import RequestVacationCommand
from vacation.application.service import VacationService
from vacation.domain.balance import balance_type_id
from vacation.domain.exceptions import InsufficientLeaveDaysError
from vacation.infrastructure.development_gateways import SettingsLeaveBalanceGateway
from vacation.infrastructure.models import LeaveBalanceModel, LeaveTypeModel
from vacation.infrastructure.repositories import DjangoVacationUnitOfWork
from vacation.infrastructure.workforce_gateways import (
    DjangoLeaveBalanceGateway,
    DjangoWorkforceGateway,
)
from workforce.infrastructure.models import Department, Employee, Person, Position


@pytest.fixture
def shared(db):
    department = Department.objects.create(dept_no=30, dept_name="합성 부서")
    position = Position.objects.create(position_code="STAFF", position_name="사원", sort_order=1)
    employees = []
    for number in (1001, 2001):
        employees.append(
            Employee.objects.create(
                employee_no=number,
                person=Person.objects.create(name="합성 사원"),
                department=department,
                position=position,
                tenure_status="재직",
                email=f"synthetic{number}@example.com",
                hire_date=date(2024, 1, 1),
            )
        )
    department.head = employees[1]
    department.save(update_fields=["head"])
    annual = LeaveTypeModel.objects.create(type_id="ANNUAL", type_name="연차", deduct_days=1)
    LeaveTypeModel.objects.create(type_id="HALF", type_name="반차", deduct_days=Decimal("0.5"))
    balance = LeaveBalanceModel.objects.create(
        employee=employees[0], vacation_type=annual, remaining_days=1
    )
    return balance


def command(kind, days):
    return RequestVacationCommand(
        1001,
        kind,
        datetime(2026, 11, 1, tzinfo=UTC),
        datetime(2026, 11, 2, tzinfo=UTC),
        Decimal(days),
        "합성 신청",
    )


@pytest.mark.parametrize(
    "kind, expected", [("HALF", "ANNUAL"), ("ANNUAL", "ANNUAL"), ("SICK", "SICK")]
)
def test_lv001_balance_policy(kind, expected):
    assert balance_type_id(kind) == expected


def test_half_and_annual_share_approval_and_recall_balance(shared, django_assert_num_queries):
    gateway = DjangoLeaveBalanceGateway()
    service = VacationService(
        DjangoVacationUnitOfWork, DjangoWorkforceGateway(), gateway, timezone.now
    )
    types = service.list_types(1001)
    with django_assert_num_queries(1):
        assert gateway.remaining_for_types(1001, types) == {
            "ANNUAL": Decimal("1.00"),
            "HALF": Decimal("1.00"),
        }
    half = service.request_vacation(command("HALF", "0.50"))
    annual = service.request_vacation(command("ANNUAL", "1.00"))
    assert gateway.remaining_days(1001, "HALF") == Decimal("1.00")
    service.approve(half.request_id, 2001)
    shared.refresh_from_db()
    assert shared.remaining_days == Decimal("0.50")
    assert gateway.remaining_days(1001, "HALF") == gateway.remaining_days(1001, "ANNUAL")
    with pytest.raises(InsufficientLeaveDaysError):
        service.approve(annual.request_id, 2001)
    service.recall(half.request_id, 2001, "합성 회수")
    shared.refresh_from_db()
    assert shared.remaining_days == Decimal("1.00")
    assert not LeaveBalanceModel.objects.filter(vacation_type_id="HALF").exists()


def test_half_cannot_use_a_separate_balance_or_bypass_annual_shortage(shared):
    LeaveBalanceModel.objects.create(
        employee=shared.employee, vacation_type_id="HALF", remaining_days=9
    )
    shared.remaining_days = Decimal("0.25")
    shared.save(update_fields=["remaining_days"])
    service = VacationService(
        DjangoVacationUnitOfWork,
        DjangoWorkforceGateway(),
        DjangoLeaveBalanceGateway(),
        timezone.now,
    )
    assert service.balances.remaining_days(1001, "HALF") == Decimal("0.25")
    with pytest.raises(InsufficientLeaveDaysError):
        service.request_vacation(command("HALF", "0.50"))


def test_development_annual_and_half_share_usage_and_lock_pool(shared, django_assert_num_queries):
    gateway = SettingsLeaveBalanceGateway()
    service = VacationService(
        DjangoVacationUnitOfWork, DjangoWorkforceGateway(), gateway, timezone.now
    )
    with override_settings(VACATION_DEVELOPMENT_EMPLOYEES={"1001": {"balances": {"ANNUAL": 2}}}):
        half = service.request_vacation(command("HALF", "0.50"))
        annual = service.request_vacation(command("ANNUAL", "1.00"))
        service.approve(half.request_id, 2001)
        service.approve(annual.request_id, 2001)
        types = service.list_types(1001)
        with django_assert_num_queries(1):
            assert gateway.remaining_for_types(1001, types) == {
                "ANNUAL": Decimal("0.50"),
                "HALF": Decimal("0.50"),
            }
        assert gateway.remaining_days(1001, "HALF") == Decimal("0.50")
        service.recall(half.request_id, 2001, "합성 회수")
        assert gateway.remaining_days(1001, "ANNUAL") == Decimal("1.00")


def test_types_api_reports_shared_balance_without_half_balance_row(shared):
    from rest_framework.test import APIClient

    from accounts.models import User

    client = APIClient()
    client.force_authenticate(
        User.objects.create_user(email="shared-balance@example.com", employee=shared.employee)
    )
    with override_settings(VACATION_INTEGRATION_MODE="database"):
        response = client.get("/api/vacations/types/?include_balance=true")
    assert response.status_code == 200
    types = {item["type_id"]: item for item in response.json()}
    assert types["HALF"]["remaining_days"] == types["ANNUAL"]["remaining_days"] == "1.00"
    assert types["HALF"]["balance_type_id"] == "ANNUAL"
    assert types["HALF"]["deduct_days"] == 0.5
