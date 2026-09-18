from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vacation.domain.entities import VacationRequest, VacationStatus
from vacation.domain.exceptions import InvalidStatusTransitionError, VacationPermissionError
from vacation.domain.value_objects import UseDays, VacationPeriod


def request(status: VacationStatus = VacationStatus.PENDING) -> VacationRequest:
    return VacationRequest(
        request_id=1,
        employee_no=1001,
        type_id="ANNUAL",
        period=VacationPeriod(datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 10, 2, tzinfo=UTC)),
        use_days=UseDays(Decimal("1.00")),
        status=status,
        approver_no=2001,
    )


def test_only_current_approver_can_approve_pending_request() -> None:
    item = request()

    with pytest.raises(VacationPermissionError):
        item.approve(9001, datetime.now(UTC))

    item.approve(2001, datetime.now(UTC))

    assert item.status is VacationStatus.APPROVED
    assert item.approved_at is not None


def test_employee_can_cancel_only_pending_own_request() -> None:
    with pytest.raises(VacationPermissionError):
        request().cancel(1002)

    with pytest.raises(InvalidStatusTransitionError):
        request(VacationStatus.APPROVED).cancel(1001)


def test_approved_request_must_be_recalled_before_resubmission() -> None:
    item = request(VacationStatus.APPROVED)
    item.recall(2001, "일정 변경")

    assert item.status is VacationStatus.RECALLED
    assert item.approved_at is None

    item.resubmit(
        1001,
        "HALF",
        VacationPeriod(datetime(2026, 10, 3, tzinfo=UTC), datetime(2026, 10, 3, 12, tzinfo=UTC)),
        UseDays(Decimal("0.50")),
        2001,
        "오전 반차",
    )

    assert item.status is VacationStatus.PENDING
    assert item.type_id == "HALF"
