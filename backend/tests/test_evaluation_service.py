from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from evaluation.application.dto import (
    CreateEvaluationCommand,
    ReassignEvaluationCommand,
    ReviseEvaluationCommand,
)
from evaluation.application.ports import WorkforceGateway
from evaluation.application.service import EvaluationService
from evaluation.domain.entities import (
    Evaluation,
    EvaluationAction,
    EvaluationHistory,
    EvaluationStatus,
    EvaluationTarget,
    EvaluatorCandidate,
)
from evaluation.domain.exceptions import (
    ConfirmationNotAllowedError,
    DuplicateEvaluationError,
    EvaluationConflictError,
    EvaluationNotFoundError,
    EvaluationPermissionError,
    EvaluationStateError,
    EvaluationYearNotAllowedError,
    InactiveEmployeeError,
    InsufficientTenureError,
    NotDepartmentHeadError,
    SelfEvaluationError,
)
from evaluation.domain.repositories import (
    EvaluationHistoryRepository,
    EvaluationRepository,
    EvaluationUnitOfWork,
)
from evaluation.domain.value_objects import Grade

NOW = datetime(2026, 10, 6, tzinfo=UTC)
TODAY = date(2026, 10, 6)
HEAD = 2001
NEW_HEAD = 2002
MEMBER = 1001
ON_LEAVE = 1003
OTHER = 3001
HR = 9001
HR_2 = 9002
RETIRED = 1002
PARENT_HEAD = 5001


class FakeEvaluations(EvaluationRepository):
    def __init__(self) -> None:
        self.items: dict[int, Evaluation] = {}

    def add(self, evaluation: Evaluation) -> Evaluation:
        if self.exists_for(evaluation.employee_no, evaluation.eval_year):
            raise DuplicateEvaluationError("해당 연도의 평가가 이미 존재합니다.")
        evaluation.eval_id = len(self.items) + 1
        self.items[evaluation.eval_id] = replace(evaluation)
        return replace(evaluation)

    def get(self, eval_id: int) -> Evaluation:
        try:
            return replace(self.items[eval_id])
        except KeyError as exc:
            raise EvaluationNotFoundError("평가를 찾을 수 없습니다.") from exc

    def save(self, evaluation: Evaluation, expected: Evaluation) -> Evaluation:
        assert evaluation.eval_id is not None
        stored = self.items[evaluation.eval_id]
        if (stored.status, stored.evaluator_no) != (expected.status, expected.evaluator_no):
            raise EvaluationConflictError("다른 사용자가 먼저 평가를 변경했습니다.")
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


class FakeHistories(EvaluationHistoryRepository):
    def __init__(self) -> None:
        self.items: list[EvaluationHistory] = []

    def add(self, entry: EvaluationHistory) -> EvaluationHistory:
        entry.history_id = len(self.items) + 1
        self.items.append(entry)
        return entry

    def list_for(self, eval_id: int) -> list[EvaluationHistory]:
        return [entry for entry in self.items if entry.eval_id == eval_id]


class FakeUnitOfWork(EvaluationUnitOfWork):
    def __init__(self) -> None:
        self.evaluations = FakeEvaluations()
        self.histories = FakeHistories()

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeWorkforce(WorkforceGateway):
    def __init__(self) -> None:
        self.inactive: set[int] = {RETIRED, ON_LEAVE}
        self.hr_managers: set[int] = {HR, HR_2}
        self.requested_dates: list[date] = []
        self.heads: set[int] = {HEAD, NEW_HEAD, PARENT_HEAD}
        self.targets: dict[int, EvaluationTarget] = {
            MEMBER: EvaluationTarget(MEMBER, True, 10, "STAFF", HEAD),
            ON_LEAVE: EvaluationTarget(ON_LEAVE, True, 10, "STAFF", HEAD),
            HEAD: EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD, PARENT_HEAD),
            RETIRED: EvaluationTarget(RETIRED, False, 10, "STAFF", HEAD),
        }

    def is_active_employee(self, employee_no: int) -> bool:
        return employee_no not in self.inactive

    def is_hr_manager(self, employee_no: int) -> bool:
        return employee_no in self.hr_managers

    def is_department_head(self, employee_no: int) -> bool:
        return employee_no in self.heads

    def evaluator_candidates(self) -> list[EvaluatorCandidate]:
        return [
            EvaluatorCandidate(no, f"부서장 {no}", no, f"부서 {no}")
            for no in sorted(self.heads)
            if self.is_active_employee(no)
        ]

    def evaluation_target(self, employee_no: int, as_of: date) -> EvaluationTarget | None:
        self.requested_dates.append(as_of)
        return self.targets.get(employee_no)


class Clock:
    """Each call moves time forward so optimistic checks see distinct versions."""

    def __init__(self) -> None:
        self.ticks = 0

    def __call__(self) -> datetime:
        self.ticks += 1
        return NOW.replace(microsecond=self.ticks)


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def workforce() -> FakeWorkforce:
    return FakeWorkforce()


@pytest.fixture
def service(uow: FakeUnitOfWork, workforce: FakeWorkforce) -> EvaluationService:
    return EvaluationService(lambda: uow, workforce, clock=Clock(), today=lambda: TODAY)


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


def submitted(service: EvaluationService, **kwargs) -> int:
    eval_id = create(service, **kwargs).eval_id or 0
    service.submit_evaluation(eval_id, kwargs.get("evaluator", HEAD))
    return eval_id


def actions(uow: FakeUnitOfWork, eval_id: int) -> list[EvaluationAction]:
    return [entry.action for entry in uow.histories.list_for(eval_id)]


# Creation --------------------------------------------------------------------------


def test_department_head_creates_draft_and_history(
    service: EvaluationService, uow: FakeUnitOfWork
) -> None:
    evaluation = create(service, score="92")

    assert evaluation.status == EvaluationStatus.DRAFT
    assert evaluation.grade == Grade.S
    assert evaluation.created_by == HEAD
    assert actions(uow, evaluation.eval_id or 0) == [EvaluationAction.CREATE]


def test_ev001_parent_department_head_evaluates_department_head(
    service: EvaluationService,
) -> None:
    evaluation = create(service, evaluator=PARENT_HEAD, employee=HEAD, score="80")
    assert evaluation.evaluator_no == PARENT_HEAD
    with pytest.raises(EvaluationPermissionError):
        create(service, evaluator=PARENT_HEAD, employee=MEMBER)


def test_ev002_self_evaluation_rejected(service: EvaluationService) -> None:
    with pytest.raises(SelfEvaluationError):
        create(service, evaluator=HEAD, employee=HEAD)


def test_employee_on_leave_can_be_evaluated(service: EvaluationService) -> None:
    assert create(service, employee=ON_LEAVE).employee_no == ON_LEAVE


def test_retired_target_cannot_get_new_evaluation(service: EvaluationService) -> None:
    with pytest.raises(InactiveEmployeeError):
        create(service, employee=RETIRED)


def test_non_evaluator_cannot_learn_target_status(service: EvaluationService) -> None:
    """HR-001: unknown, retired and ordinary targets look identical to an outsider."""
    messages = set()
    for target in (4040, RETIRED, MEMBER, HEAD):
        with pytest.raises(EvaluationPermissionError) as error:
            create(service, evaluator=OTHER, employee=target)
        messages.add((type(error.value), str(error.value)))
    assert len(messages) == 1


@pytest.mark.parametrize("year", ["2026", "2025"])
def test_creation_allows_current_and_previous_year(service: EvaluationService, year: str) -> None:
    assert create(service, year=year).eval_year == year


@pytest.mark.parametrize("year", ["2024", "2027"])
def test_creation_rejects_other_years(service: EvaluationService, year: str) -> None:
    with pytest.raises(EvaluationYearNotAllowedError):
        create(service, year=year)


def test_old_unfinished_evaluation_stays_editable_after_year_change(
    uow: FakeUnitOfWork, workforce: FakeWorkforce
) -> None:
    last_year = EvaluationService(lambda: uow, workforce, Clock(), today=lambda: date(2025, 12, 31))
    eval_id = create(last_year, year="2024").eval_id or 0

    next_year = EvaluationService(lambda: uow, workforce, Clock(), today=lambda: date(2027, 1, 2))
    next_year.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("88")))
    assert next_year.submit_evaluation(eval_id, HEAD).status == EvaluationStatus.SUBMITTED


def test_one_evaluation_per_employee_and_year(service: EvaluationService) -> None:
    create(service, year="2026")
    with pytest.raises(DuplicateEvaluationError):
        create(service, year="2026")
    assert create(service, year="2025").eval_year == "2025"


@pytest.mark.parametrize(
    ("year", "expected"),
    [("2025", date(2025, 12, 31)), ("2026", TODAY)],
)
def test_target_is_resolved_on_year_end_basis_date(
    service: EvaluationService, workforce: FakeWorkforce, year: str, expected: date
) -> None:
    create(service, year=year)
    assert workforce.requested_dates == [expected]


# Evaluator workflow ----------------------------------------------------------------


def test_revise_without_comments_keeps_existing_comments(service: EvaluationService) -> None:
    eval_id = create(service).eval_id or 0
    revised = service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("90")))
    assert revised.comments == "의견"


def test_submit_return_revise_resubmit(service: EvaluationService, uow: FakeUnitOfWork) -> None:
    eval_id = submitted(service)
    with pytest.raises(EvaluationStateError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("70")))

    returned = service.return_evaluation(eval_id, HR, "근거 보완")
    assert returned.status == EvaluationStatus.RETURNED
    service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("72")))
    assert service.submit_evaluation(eval_id, HEAD).status == EvaluationStatus.SUBMITTED

    assert actions(uow, eval_id) == [
        EvaluationAction.CREATE,
        EvaluationAction.SUBMIT,
        EvaluationAction.RETURN,
        EvaluationAction.REVISE,
        EvaluationAction.SUBMIT,
    ]


def test_hr_manager_cannot_edit_scores(service: EvaluationService) -> None:
    eval_id = create(service).eval_id or 0
    with pytest.raises(EvaluationPermissionError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HR, Decimal("99")))


def test_evaluator_cannot_perform_hr_actions(service: EvaluationService) -> None:
    eval_id = submitted(service)
    for action in (
        lambda: service.return_evaluation(eval_id, HEAD, "사유"),
        lambda: service.confirm_evaluation(eval_id, HEAD),
        lambda: service.exclude_evaluation(eval_id, HEAD, "사유"),
    ):
        with pytest.raises(EvaluationPermissionError):
            action()


# Reassignment ----------------------------------------------------------------------


def test_reassignment_transfers_access_and_requires_review(
    service: EvaluationService, uow: FakeUnitOfWork
) -> None:
    eval_id = submitted(service)

    reassigned = service.reassign_evaluation(
        ReassignEvaluationCommand(eval_id, HR, NEW_HEAD, "부서장 교체")
    )
    assert reassigned.evaluator_no == NEW_HEAD
    assert reassigned.created_by == HEAD
    assert reassigned.status == EvaluationStatus.DRAFT

    # The former evaluator loses read and write access.
    with pytest.raises(EvaluationNotFoundError):
        service.get_evaluation(eval_id, HEAD)
    with pytest.raises(EvaluationNotFoundError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("70")))
    assert service.list_evaluations(HEAD) == []

    # The new evaluator inherits the draft, reviews it, then submits.
    assert service.get_evaluation(eval_id, NEW_HEAD).comments == "의견"
    assert service.submit_evaluation(eval_id, NEW_HEAD).status == EvaluationStatus.SUBMITTED

    entry = uow.histories.list_for(eval_id)[2]
    assert entry.action == EvaluationAction.REASSIGN
    assert (entry.from_evaluator_no, entry.to_evaluator_no, entry.reason) == (
        HEAD,
        NEW_HEAD,
        "부서장 교체",
    )


def test_reassignment_rejects_inactive_evaluator(service: EvaluationService) -> None:
    eval_id = create(service).eval_id or 0
    with pytest.raises(InactiveEmployeeError):
        service.reassign_evaluation(ReassignEvaluationCommand(eval_id, HR, RETIRED, "사유"))


def test_inactive_evaluator_is_blocked_until_reassigned(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    eval_id = create(service).eval_id or 0
    workforce.inactive.add(HEAD)

    with pytest.raises(InactiveEmployeeError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("70")))

    service.reassign_evaluation(ReassignEvaluationCommand(eval_id, HR, NEW_HEAD, "평가자 퇴사"))
    service.revise_evaluation(ReviseEvaluationCommand(eval_id, NEW_HEAD, Decimal("70")))


# Confirmation ----------------------------------------------------------------------


def test_ev004_hr_confirms_submitted_evaluation(service: EvaluationService) -> None:
    eval_id = create(service).eval_id or 0
    with pytest.raises(EvaluationStateError):
        service.confirm_evaluation(eval_id, HR)

    service.submit_evaluation(eval_id, HEAD)
    confirmed = service.confirm_evaluation(eval_id, HR)
    assert confirmed.status == EvaluationStatus.CONFIRMED
    assert confirmed.confirmed_by == HR


def test_former_evaluator_who_became_hr_manager_cannot_confirm(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    # HEAD writes the draft, later receives the HR manager role and is replaced.
    eval_id = create(service).eval_id or 0
    workforce.hr_managers.add(HEAD)
    service.reassign_evaluation(ReassignEvaluationCommand(eval_id, HR_2, NEW_HEAD, "역할 변경"))
    service.submit_evaluation(eval_id, NEW_HEAD)

    with pytest.raises(ConfirmationNotAllowedError):
        service.confirm_evaluation(eval_id, HEAD)
    # Another HR manager can still confirm, so the evaluation is not stuck.
    assert service.confirm_evaluation(eval_id, HR_2).status == EvaluationStatus.CONFIRMED


def test_hr_manager_department_head_evaluates_and_another_hr_confirms(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    """인사관리자+부서장은 평가자가 되고, 확정은 다른 인사관리자가 한다 (2026-10-08)."""
    workforce.heads.add(HR)
    workforce.targets[MEMBER] = EvaluationTarget(MEMBER, True, 10, "STAFF", HR)
    eval_id = create(service, evaluator=HR).eval_id or 0
    service.revise_evaluation(ReviseEvaluationCommand(eval_id, HR, Decimal("88")))
    service.submit_evaluation(eval_id, HR)

    with pytest.raises(ConfirmationNotAllowedError):
        service.confirm_evaluation(eval_id, HR)
    assert service.confirm_evaluation(eval_id, HR_2).confirmed_by == HR_2


def test_hr_manager_department_head_can_be_reassignment_target(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    workforce.heads.add(HR_2)
    eval_id = create(service).eval_id or 0
    reassigned = service.reassign_evaluation(
        ReassignEvaluationCommand(eval_id, HR, HR_2, "부서장 교체")
    )
    assert reassigned.evaluator_no == HR_2


def test_evaluator_who_became_hr_manager_keeps_writing_but_cannot_confirm(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    eval_id = create(service).eval_id or 0
    workforce.hr_managers.add(HEAD)

    service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("70")))
    service.submit_evaluation(eval_id, HEAD)
    with pytest.raises(ConfirmationNotAllowedError):
        service.confirm_evaluation(eval_id, HEAD)
    assert service.confirm_evaluation(eval_id, HR).status == EvaluationStatus.CONFIRMED


@pytest.mark.parametrize(
    ("year", "hire_date", "allowed"),
    [
        # Current year: tenure counted up to today (2026-10-06).
        ("2026", date(2026, 7, 5), True),  # 3 months and 1 day
        ("2026", date(2026, 7, 6), False),  # exactly 3 months
        ("2026", date(2026, 9, 22), False),  # about two weeks
        # Previous year: tenure counted up to 2025-12-31.
        ("2025", date(2025, 9, 30), True),
        ("2025", date(2025, 10, 1), False),
        ("2025", date(2026, 1, 1), False),  # hired after the evaluated year
    ],
)
def test_employees_with_three_months_or_less_are_not_evaluated(
    service: EvaluationService,
    workforce: FakeWorkforce,
    year: str,
    hire_date: date,
    allowed: bool,
) -> None:
    workforce.targets[MEMBER] = replace(workforce.targets[MEMBER], hire_date=hire_date)
    if allowed:
        assert create(service, year=year).employee_no == MEMBER
    else:
        with pytest.raises(InsufficientTenureError):
            create(service, year=year)


def test_tenure_is_checked_after_authority(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    """An outsider learns nothing about the target's hire date (HR-001)."""
    workforce.targets[MEMBER] = replace(workforce.targets[MEMBER], hire_date=TODAY)
    with pytest.raises(EvaluationPermissionError):
        create(service, evaluator=OTHER)


def test_fn_ev_001_reassignment_target_must_be_department_head(
    service: EvaluationService, uow: FakeUnitOfWork
) -> None:
    eval_id = create(service).eval_id or 0
    with pytest.raises(NotDepartmentHeadError):
        service.reassign_evaluation(ReassignEvaluationCommand(eval_id, HR, OTHER, "사유"))
    assert uow.evaluations.get(eval_id).evaluator_no == HEAD


def test_evaluator_who_lost_head_post_must_be_reassigned(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    eval_id = create(service).eval_id or 0
    workforce.heads.discard(HEAD)

    with pytest.raises(NotDepartmentHeadError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("70")))
    with pytest.raises(NotDepartmentHeadError):
        service.submit_evaluation(eval_id, HEAD)

    service.reassign_evaluation(ReassignEvaluationCommand(eval_id, HR, NEW_HEAD, "보직 변경"))
    service.submit_evaluation(eval_id, NEW_HEAD)


def test_evaluator_candidates_are_for_hr_only(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    workforce.heads.add(HR_2)  # an HR manager who heads a department is a candidate
    candidates = service.evaluator_candidates(HR)
    assert [item.employee_no for item in candidates] == [HEAD, NEW_HEAD, PARENT_HEAD, HR_2]
    with pytest.raises(EvaluationPermissionError):
        service.evaluator_candidates(HEAD)


def test_hr_actions_on_own_unconfirmed_evaluation_look_missing(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    """EV-005: an HR manager cannot detect their own unconfirmed evaluation via HR actions.

    Confirmation is the README exception and answers confirmation_not_allowed instead.
    """
    workforce.targets[HR] = EvaluationTarget(HR, True, 10, "STAFF", HEAD)
    eval_id = submitted(service, employee=HR)

    for action in (
        lambda: service.return_evaluation(eval_id, HR, "사유"),
        lambda: service.exclude_evaluation(eval_id, HR, "사유"),
        lambda: service.reassign_evaluation(
            ReassignEvaluationCommand(eval_id, HR, NEW_HEAD, "사유")
        ),
    ):
        with pytest.raises(EvaluationNotFoundError):
            action()


def test_non_hr_caller_learns_nothing_from_reassign(service: EvaluationService) -> None:
    eval_id = create(service).eval_id or 0
    for new_evaluator in (RETIRED, HR_2, NEW_HEAD):
        with pytest.raises(EvaluationPermissionError) as error:
            service.reassign_evaluation(
                ReassignEvaluationCommand(eval_id, OTHER, new_evaluator, "사유")
            )
        assert error.value.code == "permission_denied"


def test_hr_manager_cannot_confirm_own_evaluation(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    """README: the evaluated employee may not confirm -> confirmation_not_allowed (403)."""
    workforce.targets[HR] = EvaluationTarget(HR, True, 10, "STAFF", HEAD)
    eval_id = submitted(service, employee=HR)

    with pytest.raises(ConfirmationNotAllowedError):
        service.confirm_evaluation(eval_id, HR)
    assert service.confirm_evaluation(eval_id, HR_2).confirmed_by == HR_2


def test_confirmed_evaluation_cannot_change(service: EvaluationService) -> None:
    eval_id = submitted(service)
    service.confirm_evaluation(eval_id, HR)

    with pytest.raises(EvaluationStateError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("99")))
    with pytest.raises(EvaluationStateError):
        service.return_evaluation(eval_id, HR, "사유")
    with pytest.raises(EvaluationStateError):
        service.reassign_evaluation(ReassignEvaluationCommand(eval_id, HR, NEW_HEAD, "사유"))
    with pytest.raises(EvaluationStateError):
        service.exclude_evaluation(eval_id, HR, "사유")


def test_correction_cycle_after_confirmation(
    service: EvaluationService, uow: FakeUnitOfWork
) -> None:
    eval_id = submitted(service)
    service.confirm_evaluation(eval_id, HR)

    with pytest.raises(EvaluationPermissionError):
        service.cancel_confirmation(eval_id, HEAD, "사유")
    cancelled = service.cancel_confirmation(eval_id, HR, "점수 오기 정정")
    assert cancelled.status == EvaluationStatus.RETURNED
    assert cancelled.confirmed_by is None
    with pytest.raises(EvaluationNotFoundError):
        service.get_evaluation(eval_id, MEMBER)

    with pytest.raises(EvaluationPermissionError):
        service.revise_evaluation(ReviseEvaluationCommand(eval_id, HR, Decimal("75")))
    service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("75")))
    service.submit_evaluation(eval_id, HEAD)
    reconfirmed = service.confirm_evaluation(eval_id, HR_2)
    assert reconfirmed.status == EvaluationStatus.CONFIRMED
    assert reconfirmed.grade == Grade.B

    assert actions(uow, eval_id) == [
        EvaluationAction.CREATE,
        EvaluationAction.SUBMIT,
        EvaluationAction.CONFIRM,
        EvaluationAction.CANCEL_CONFIRMATION,
        EvaluationAction.REVISE,
        EvaluationAction.SUBMIT,
        EvaluationAction.CONFIRM,
    ]


# Exclusion -------------------------------------------------------------------------


def test_exclusion_and_cancellation_restore_previous_state(service: EvaluationService) -> None:
    eval_id = submitted(service, employee=ON_LEAVE)

    excluded = service.exclude_evaluation(eval_id, HR, "장기 휴직")
    assert excluded.status == EvaluationStatus.EXCLUDED
    with pytest.raises(EvaluationStateError):
        service.confirm_evaluation(eval_id, HR)

    restored = service.cancel_exclusion(eval_id, HR)
    assert restored.status == EvaluationStatus.SUBMITTED


def test_retired_target_in_progress_can_be_completed_or_excluded(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    first = submitted(service)
    second = create(service, year="2025").eval_id or 0
    workforce.targets[MEMBER] = replace(workforce.targets[MEMBER], is_employed=False)

    assert service.confirm_evaluation(first, HR).status == EvaluationStatus.CONFIRMED
    assert service.exclude_evaluation(second, HR, "퇴사").status == EvaluationStatus.EXCLUDED


# Visibility and concurrency --------------------------------------------------------


def test_visibility_rules(service: EvaluationService) -> None:
    eval_id = submitted(service)

    assert service.get_evaluation(eval_id, HEAD).eval_id == eval_id
    assert service.get_evaluation(eval_id, HR).eval_id == eval_id
    for viewer in (MEMBER, OTHER):
        with pytest.raises(EvaluationNotFoundError):
            service.get_evaluation(eval_id, viewer)
    assert service.list_evaluations(MEMBER) == []

    service.confirm_evaluation(eval_id, HR)
    assert service.get_evaluation(eval_id, MEMBER).status == EvaluationStatus.CONFIRMED
    assert [item.eval_id for item in service.list_evaluations(MEMBER)] == [eval_id]


def test_history_is_for_hr_and_current_evaluator_only(service: EvaluationService) -> None:
    eval_id = submitted(service)
    service.confirm_evaluation(eval_id, HR)

    assert len(service.list_history(eval_id, HR)) == 3
    assert len(service.list_history(eval_id, HEAD)) == 3
    with pytest.raises(EvaluationPermissionError):
        service.list_history(eval_id, MEMBER)
    with pytest.raises(EvaluationNotFoundError):
        service.list_history(eval_id, OTHER)


def test_hr_manager_cannot_see_own_unconfirmed_evaluation(
    service: EvaluationService, workforce: FakeWorkforce
) -> None:
    """EV-005: being an HR manager does not widen access to one's own evaluation."""
    workforce.targets[HR] = EvaluationTarget(HR, True, 10, "STAFF", HEAD)
    eval_id = submitted(service, employee=HR)

    with pytest.raises(EvaluationNotFoundError):
        service.get_evaluation(eval_id, HR)
    with pytest.raises(EvaluationNotFoundError):
        service.list_history(eval_id, HR)
    assert eval_id not in [item.eval_id for item in service.list_evaluations(HR)]
    assert eval_id in [item.eval_id for item in service.list_evaluations(HR_2)]

    service.confirm_evaluation(eval_id, HR_2)
    assert service.get_evaluation(eval_id, HR).status == EvaluationStatus.CONFIRMED
    assert eval_id in [item.eval_id for item in service.list_evaluations(HR)]
    with pytest.raises(EvaluationPermissionError):
        service.list_history(eval_id, HR)


def test_concurrent_content_edits_keep_last_saved(
    service: EvaluationService, uow: FakeUnitOfWork
) -> None:
    eval_id = create(service).eval_id or 0
    first_load = uow.evaluations.get(eval_id)

    service.revise_evaluation(ReviseEvaluationCommand(eval_id, HEAD, Decimal("70")))
    # A save based on the older load still succeeds: same status and evaluator.
    first_load.revise(HEAD, Decimal("95"), None, NOW)
    uow.evaluations.save(first_load, uow.evaluations.get(eval_id))
    assert uow.evaluations.get(eval_id).score == Decimal("95")


def test_concurrent_change_is_reported_as_conflict(
    service: EvaluationService, uow: FakeUnitOfWork
) -> None:
    eval_id = submitted(service)

    original_get = uow.evaluations.get

    def stale_get(requested_id: int) -> Evaluation:
        loaded = original_get(requested_id)
        # Someone else returns the evaluation between this request's load and save.
        stored = uow.evaluations.items[requested_id]
        uow.evaluations.items[requested_id] = replace(
            stored, status=EvaluationStatus.RETURNED, updated_at=NOW
        )
        return loaded

    uow.evaluations.get = stale_get  # type: ignore[method-assign]
    with pytest.raises(EvaluationConflictError):
        service.confirm_evaluation(eval_id, HR)
