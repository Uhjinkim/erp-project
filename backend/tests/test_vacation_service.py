from datetime import UTC, datetime
from decimal import Decimal

import pytest

from vacation.application.dto import RequestVacationCommand
from vacation.application.ports import LeaveBalanceGateway, WorkforceGateway
from vacation.application.service import VacationService
from vacation.domain.entities import VacationHistory, VacationRequest, VacationStatus, VacationType
from vacation.domain.exceptions import InsufficientLeaveDaysError
from vacation.domain.repositories import (
    VacationHistoryRepository,
    VacationRequestRepository,
    VacationTypeRepository,
    VacationUnitOfWork,
)


class FakeRequests(VacationRequestRepository):
    def __init__(self) -> None:
        self.items: dict[int, VacationRequest] = {}

    def add(self, request: VacationRequest) -> VacationRequest:
        request.request_id = len(self.items) + 1
        self.items[request.request_id] = request
        return request

    def get(self, request_id: int, *, for_update: bool = False) -> VacationRequest:
        return self.items[request_id]

    def save(self, request: VacationRequest) -> None:
        assert request.request_id is not None
        self.items[request.request_id] = request

    def list_for_employee(self, employee_no: int) -> list[VacationRequest]:
        return [item for item in self.items.values() if item.employee_no == employee_no]

    def list_for_approver(self, employee_no: int) -> list[VacationRequest]:
        return [item for item in self.items.values() if item.approver_no == employee_no]


class FakeHistories(VacationHistoryRepository):
    def __init__(self) -> None:
        self.items: list[VacationHistory] = []

    def add(self, history: VacationHistory) -> None:
        self.items.append(history)

    def list_for_request(self, request_id: int) -> list[VacationHistory]:
        return [item for item in self.items if item.request_id == request_id]


class FakeTypes(VacationTypeRepository):
    annual = VacationType("ANNUAL", "연차", True, Decimal("1.00"))

    def get(self, type_id: str) -> VacationType:
        assert type_id == "ANNUAL"
        return self.annual

    def list_active(self) -> list[VacationType]:
        return [self.annual]


class FakeUnitOfWork(VacationUnitOfWork):
    def __init__(self) -> None:
        self.requests = FakeRequests()
        self.histories = FakeHistories()
        self.types = FakeTypes()

    def __enter__(self):
        return self

    def __exit__(self, *args: object):
        return None


class FakeWorkforce(WorkforceGateway):
    def is_active_employee(self, employee_no: int) -> bool:
        return employee_no in {1001, 2001}

    def resolve_vacation_approver(self, employee_no: int) -> int | None:
        return 2001

    def is_hr_manager(self, employee_no: int) -> bool:
        return False


class FakeBalances(LeaveBalanceGateway):
    def __init__(self, remaining: Decimal) -> None:
        self.remaining = remaining

    def remaining_days(self, employee_no: int, type_id: str) -> Decimal | None:
        return self.remaining


def command(days: str = "1.00") -> RequestVacationCommand:
    return RequestVacationCommand(
        employee_no=1001,
        type_id="ANNUAL",
        start=datetime(2026, 10, 1, tzinfo=UTC),
        end=datetime(2026, 10, 2, tzinfo=UTC),
        use_days=Decimal(days),
        reason="가족 일정",
    )


def service(uow: FakeUnitOfWork, remaining: str = "15.00") -> VacationService:
    return VacationService(
        unit_of_work_factory=lambda: uow,
        workforce=FakeWorkforce(),
        balances=FakeBalances(Decimal(remaining)),
        clock=lambda: datetime(2026, 9, 18, tzinfo=UTC),
    )


def test_request_and_approval_create_atomic_history_entries() -> None:
    uow = FakeUnitOfWork()
    vacation = service(uow)

    item = vacation.request_vacation(command())
    vacation.approve(item.request_id or 0, 2001)

    assert item.status is VacationStatus.APPROVED
    assert [entry.to_status for entry in uow.histories.items] == [
        VacationStatus.PENDING,
        VacationStatus.APPROVED,
    ]


def test_request_cannot_exceed_remaining_days() -> None:
    with pytest.raises(InsufficientLeaveDaysError):
        service(FakeUnitOfWork(), remaining="0.50").request_vacation(command("1.00"))
