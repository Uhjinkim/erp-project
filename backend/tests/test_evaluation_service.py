from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from evaluation.application.dto import CreateEvaluationCommand, ReviseEvaluationCommand
from evaluation.application.ports import WorkforceGateway
from evaluation.application.service import EvaluationService
from evaluation.domain.entities import Evaluation, EvaluationStatus, EvaluationTarget
from evaluation.domain.exceptions import (
    DuplicateEvaluationError,
    EvaluationNotFoundError,
    EvaluationPermissionError,
    EvaluationStateError,
    InactiveEmployeeError,
    SelfEvaluationError,
)
from evaluation.domain.repositories import EvaluationRepository
from evaluation.domain.value_objects import Grade

NOW = datetime(2026, 10, 6, tzinfo=UTC)
HEAD = 2001
MEMBER = 1001
OTHER = 3001
HR = 9001
RETIRED = 1002
PARENT_HEAD = 5001


class FakeEvaluations(EvaluationRepository):
    def __init__(self) -> None:
        self.items: dict[int, Evaluation] = {}

    def add(self, evaluation: Evaluation) -> Evaluation:
        evaluation.eval_id = len(self.items) + 1
        self.items[evaluation.eval_id] = replace(evaluation)
        return replace(evaluation)

    def get(self, eval_id: int) -> Evaluation:
        try:
            return replace(self.items[eval_id])
        except KeyError as exc:
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.") from exc

    def save_draft(self, evaluation: Evaluation) -> Evaluation:
        assert evaluation.eval_id is not None
        if self.items[evaluation.eval_id].status != EvaluationStatus.DRAFT:
            raise EvaluationStateError("확정된 평가는 변경할 수 없습니다.")
        self.items[evaluation.eval_id] = replace(evaluation)
        return replace(evaluation)

    def exists_for(self, employee_no: int, eval_year: str) -> bool:
        return any(
            item.employee_no == employee_no and item.eval_year == eval_year
            for item in self.items.values()
        )

    def list_all(self, eval_year: str | None = None) -> list[Evaluation]:
        return [
            item for item in self.items.values() if eval_year in (None, item.eval_year)
        ]

    def list_visible_to(self, viewer_no: int, eval_year: str | None = None) -> list[Evaluation]:
        return [
            item
            for item in self.list_all(eval_year)
            if item.evaluator_no == viewer_no
            or (item.employee_no == viewer_no and item.status == EvaluationStatus.CONFIRMED)
        ]


class FakeWorkforce(WorkforceGateway):
    def __init__(self) -> None:
        self.inactive: set[int] = {RETIRED}
        self.hr_managers: set[int] = {HR}
        self.targets: dict[int, EvaluationTarget] = {
            MEMBER: EvaluationTarget(MEMBER, True, 10, "STAFF", HEAD),
            HEAD: EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD, PARENT_HEAD),
            RETIRED: EvaluationTarget(RETIRED, False, 10, "STAFF", HEAD),
        }

    def is_active_employee(self, employee_no: int) -> bool:
        return employee_no not in self.inactive

    def is_hr_manager(self, employee_no: int) -> bool:
        return employee_no in self.hr_managers

    def evaluation_target(self, employee_no: int) -> EvaluationTarget | None:
        return self.targets.get(employee_no)


@pytest.fixture
def workforce() -> FakeWorkforce:
    return FakeWorkforce()


@pytest.fixture
def service(workforce: FakeWorkforce) -> EvaluationService:
    return EvaluationService(FakeEvaluations(), workforce, clock=lambda: NOW)


def create(
    service: EvaluationService,
    *,
    evaluator: int = HEAD,
    employee: int = MEMBER,
    year: str = "2026",
    score: str = "85",
) -> Evaluation:
    return service.create_evaluation(
        CreateEvaluationCommand(
            evaluator_no=evaluator,
            employee_no=employee,
            eval_year=year,
            score=Decimal(score),
            comments="의견",
        )
    )


def test_fn_ev_department_head_creates_draft(service: EvaluationService) -> None:
    evaluation = create(service, score="92")

    assert evaluation.eval_id == 1
    assert evaluation.status == EvaluationStatus.DRAFT
    assert evaluation.grade == Grade.S
    assert evaluation.snapshot_department_no == 10


def test_ev001_non_head_cannot_create(service: EvaluationService) -> None:
    with pytest.raises(EvaluationPermissionError):
        create(service, evaluator=OTHER)


def test_ev002_self_evaluation_rejected(service: EvaluationService) -> None:
    with pytest.raises(SelfEvaluationError):
        create(service, evaluator=HEAD, employee=HEAD)


def test_ev001_parent_department_head_evaluates_department_head(
    service: EvaluationService,
) -> None:
    evaluation = create(service, evaluator=PARENT_HEAD, employee=HEAD, score="80")

    assert evaluation.evaluator_no == PARENT_HEAD
    assert evaluation.employee_no == HEAD
    assert evaluation.snapshot_position_code == "MANAGER"
    with pytest.raises(EvaluationPermissionError):
        create(service, evaluator=PARENT_HEAD, employee=MEMBER)


def test_inactive_evaluator_cannot_create(service: EvaluationService) -> None:
    with pytest.raises(InactiveEmployeeError):
        create(service, evaluator=RETIRED)


def test_retired_target_cannot_be_evaluated(service: EvaluationService) -> None:
    with pytest.raises(InactiveEmployeeError):
        create(service, employee=RETIRED)


def test_unknown_target_is_reported_as_permission_error(service: EvaluationService) -> None:
    with pytest.raises(EvaluationPermissionError):
        create(service, employee=4040)


def test_non_evaluator_cannot_learn_target_status(service: EvaluationService) -> None:
    """HR-001: unknown, retired and ordinary targets look identical to an outsider."""
    messages = []
    for target in (4040, RETIRED, MEMBER, HEAD):
        with pytest.raises(EvaluationPermissionError) as error:
            create(service, evaluator=OTHER, employee=target)
        messages.append((type(error.value), str(error.value)))
    assert len(set(messages)) == 1


def test_revise_without_comments_keeps_existing_comments(service: EvaluationService) -> None:
    created = create(service)
    revised = service.revise_evaluation(
        ReviseEvaluationCommand(created.eval_id or 0, HEAD, Decimal("90"))
    )
    assert revised.comments == "의견"

    cleared = service.revise_evaluation(
        ReviseEvaluationCommand(created.eval_id or 0, HEAD, Decimal("90"), "")
    )
    assert cleared.comments == ""


def test_one_evaluation_per_employee_and_year(service: EvaluationService) -> None:
    create(service, year="2026")
    with pytest.raises(DuplicateEvaluationError):
        create(service, year="2026")
    assert create(service, year="2025").eval_id == 2


def test_evaluator_revises_draft(service: EvaluationService) -> None:
    created = create(service, score="85")
    revised = service.revise_evaluation(
        ReviseEvaluationCommand(created.eval_id or 0, HEAD, Decimal("72"), "수정")
    )
    assert revised.grade == Grade.B
    assert revised.comments == "수정"


def test_ev004_only_hr_manager_confirms(service: EvaluationService) -> None:
    created = create(service)
    with pytest.raises(EvaluationPermissionError):
        service.confirm_evaluation(created.eval_id or 0, HEAD)

    confirmed = service.confirm_evaluation(created.eval_id or 0, HR)
    assert confirmed.status == EvaluationStatus.CONFIRMED
    assert confirmed.confirmed_by == HR
    assert confirmed.confirmed_at == NOW


def test_confirmed_evaluation_cannot_be_revised_or_reconfirmed(
    service: EvaluationService,
) -> None:
    created = create(service)
    service.confirm_evaluation(created.eval_id or 0, HR)

    with pytest.raises(EvaluationStateError):
        service.revise_evaluation(
            ReviseEvaluationCommand(created.eval_id or 0, HEAD, Decimal("99"), "")
        )
    with pytest.raises(EvaluationStateError):
        service.confirm_evaluation(created.eval_id or 0, HR)


def test_visibility_rules(service: EvaluationService) -> None:
    created = create(service)
    eval_id = created.eval_id or 0

    assert service.get_evaluation(eval_id, HEAD).eval_id == eval_id
    assert service.get_evaluation(eval_id, HR).eval_id == eval_id
    with pytest.raises(EvaluationNotFoundError):
        service.get_evaluation(eval_id, MEMBER)
    with pytest.raises(EvaluationNotFoundError):
        service.get_evaluation(eval_id, OTHER)
    assert service.list_evaluations(MEMBER) == []

    service.confirm_evaluation(eval_id, HR)
    assert service.get_evaluation(eval_id, MEMBER).status == EvaluationStatus.CONFIRMED
    assert [item.eval_id for item in service.list_evaluations(MEMBER)] == [eval_id]


def test_hr_manager_lists_all_with_year_filter(service: EvaluationService) -> None:
    create(service, year="2025")
    create(service, year="2026")

    assert len(service.list_evaluations(HR)) == 2
    assert [item.eval_year for item in service.list_evaluations(HR, "2025")] == ["2025"]
    assert service.list_evaluations(OTHER) == []
