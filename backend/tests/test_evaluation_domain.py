import ast
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from evaluation.domain.entities import (
    Evaluation,
    EvaluationAction,
    EvaluationHistory,
    EvaluationStatus,
    EvaluationTarget,
    ensure_can_evaluate,
    restorable_status,
)
from evaluation.domain.exceptions import (
    ConfirmationNotAllowedError,
    EvaluationPermissionError,
    EvaluationStateError,
    EvaluationYearNotAllowedError,
    InvalidEvaluationError,
    SelfEvaluationError,
)
from evaluation.domain.value_objects import (
    EvaluationScore,
    EvaluationYear,
    Grade,
    Reason,
    ensure_creatable_year,
)

NOW = datetime(2026, 10, 6, tzinfo=UTC)
HEAD = 2001
MEMBER = 1001
PARENT_HEAD = 5001
NEW_EVALUATOR = 2002
HR = 9001
TARGET = EvaluationTarget(
    employee_no=MEMBER,
    is_employed=True,
    department_no=10,
    position_code="STAFF",
    department_head_no=HEAD,
)


def make_draft(score: str = "85") -> Evaluation:
    evaluation = Evaluation.draft(
        target=TARGET,
        evaluator_no=HEAD,
        eval_year="2026",
        score=Decimal(score),
        comments="성실함",
        now=NOW,
    )
    evaluation.eval_id = 1
    return evaluation


def submitted() -> Evaluation:
    evaluation = make_draft()
    evaluation.submit(HEAD, NOW)
    return evaluation


# Value objects ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "grade"),
    [
        ("100", Grade.S),
        ("90", Grade.S),
        ("89.99", Grade.A),
        ("80", Grade.A),
        ("79.99", Grade.B),
        ("70", Grade.B),
        ("69.99", Grade.C),
        ("0", Grade.C),
    ],
)
def test_ev003_grade_is_derived_from_score_boundaries(score: str, grade: Grade) -> None:
    assert EvaluationScore(Decimal(score)).grade == grade


@pytest.mark.parametrize("score", ["-0.01", "100.01", "85.123", "NaN"])
def test_score_must_be_within_range_and_two_decimals(score: str) -> None:
    with pytest.raises(InvalidEvaluationError):
        EvaluationScore(Decimal(score))


@pytest.mark.parametrize("year", ["26", "20266", "２０２６", "abcd"])
def test_eval_year_must_be_four_ascii_digits(year: str) -> None:
    with pytest.raises(InvalidEvaluationError):
        EvaluationYear(year)


@pytest.mark.parametrize("year", ["2026", "2025"])
def test_new_evaluation_allows_current_and_previous_year(year: str) -> None:
    ensure_creatable_year(year, 2026)


@pytest.mark.parametrize("year", ["2024", "2027", "0000"])
def test_new_evaluation_rejects_other_years(year: str) -> None:
    with pytest.raises(EvaluationYearNotAllowedError):
        ensure_creatable_year(year, 2026)


@pytest.mark.parametrize("reason", ["", "   ", "x" * 256])
def test_reason_is_required_and_bounded(reason: str) -> None:
    with pytest.raises(InvalidEvaluationError):
        Reason(reason)


# Evaluator selection (EV-001/EV-002) -----------------------------------------------


def test_ev001_department_head_creates_draft_with_snapshot() -> None:
    evaluation = make_draft("91.5")

    assert evaluation.status == EvaluationStatus.DRAFT
    assert evaluation.grade == Grade.S
    assert evaluation.snapshot_department_no == 10
    assert evaluation.snapshot_position_code == "STAFF"
    assert evaluation.evaluator_no == HEAD
    assert evaluation.created_by == HEAD


def test_ev001_only_department_head_can_evaluate() -> None:
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(3001, TARGET)


def test_ev001_target_without_department_head_cannot_be_evaluated() -> None:
    target = EvaluationTarget(MEMBER, True, None, None, None)
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(HEAD, target)


def test_ev002_self_evaluation_is_rejected_even_for_department_head() -> None:
    head_target = EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD, PARENT_HEAD)
    with pytest.raises(SelfEvaluationError):
        ensure_can_evaluate(HEAD, head_target)


def test_ev001_department_head_is_evaluated_by_parent_department_head() -> None:
    head_target = EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD, PARENT_HEAD)

    ensure_can_evaluate(PARENT_HEAD, head_target)
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(3001, head_target)


def test_ev001_parent_head_cannot_skip_level_to_evaluate_members() -> None:
    member_target = replace(TARGET, parent_department_head_no=PARENT_HEAD)
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(PARENT_HEAD, member_target)


def test_ev001_top_level_head_without_parent_head_cannot_be_evaluated() -> None:
    top_head = EvaluationTarget(PARENT_HEAD, True, 1, "DIRECTOR", PARENT_HEAD, None)
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(HEAD, top_head)


def test_ev002_head_of_both_department_and_parent_cannot_self_evaluate() -> None:
    head_target = EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD, HEAD)
    with pytest.raises(SelfEvaluationError):
        ensure_can_evaluate(HEAD, head_target)


def test_permission_message_does_not_reveal_target_role() -> None:
    head_target = EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD, PARENT_HEAD)
    messages = set()
    for target in (TARGET, head_target):
        with pytest.raises(EvaluationPermissionError) as error:
            ensure_can_evaluate(3001, target)
        messages.add(str(error.value))
    assert len(messages) == 1


# Evaluator actions -----------------------------------------------------------------


def test_evaluator_revises_draft_and_grade_is_recalculated() -> None:
    evaluation = make_draft("85")
    history = evaluation.revise(HEAD, Decimal("65"), "보완 필요", NOW)

    assert evaluation.score == Decimal("65")
    assert evaluation.grade == Grade.C
    assert evaluation.comments == "보완 필요"
    assert history.action == EvaluationAction.REVISE
    assert history.score == Decimal("65")


def test_revise_without_comments_keeps_text() -> None:
    evaluation = make_draft()
    evaluation.revise(HEAD, Decimal("90"), None, NOW)
    assert evaluation.comments == "성실함"


def test_only_current_evaluator_can_revise_or_submit() -> None:
    evaluation = make_draft()
    with pytest.raises(EvaluationPermissionError):
        evaluation.revise(3001, Decimal("90"), "", NOW)
    with pytest.raises(EvaluationPermissionError):
        evaluation.submit(HR, NOW)


def test_submitted_evaluation_must_be_returned_before_editing() -> None:
    evaluation = submitted()
    assert evaluation.status == EvaluationStatus.SUBMITTED

    with pytest.raises(EvaluationStateError):
        evaluation.revise(HEAD, Decimal("90"), None, NOW)

    history = evaluation.return_for_revision(HR, "근거 보완", NOW)
    assert evaluation.status == EvaluationStatus.RETURNED
    assert history.reason == "근거 보완"

    evaluation.revise(HEAD, Decimal("90"), None, NOW)
    evaluation.submit(HEAD, NOW)
    assert evaluation.status == EvaluationStatus.SUBMITTED


def test_return_requires_reason_and_submitted_state() -> None:
    with pytest.raises(InvalidEvaluationError):
        submitted().return_for_revision(HR, " ", NOW)
    with pytest.raises(EvaluationStateError):
        make_draft().return_for_revision(HR, "사유", NOW)


# Reassignment ----------------------------------------------------------------------


def test_reassign_moves_authority_and_keeps_first_author() -> None:
    evaluation = make_draft()
    history = evaluation.reassign(HR, NEW_EVALUATOR, "부서장 교체", NOW)

    assert evaluation.evaluator_no == NEW_EVALUATOR
    assert evaluation.created_by == HEAD
    assert history.from_evaluator_no == HEAD
    assert history.to_evaluator_no == NEW_EVALUATOR
    with pytest.raises(EvaluationPermissionError):
        evaluation.revise(HEAD, Decimal("70"), None, NOW)
    evaluation.revise(NEW_EVALUATOR, Decimal("70"), None, NOW)


def test_reassigning_submitted_evaluation_returns_it_to_draft_for_review() -> None:
    evaluation = submitted()
    evaluation.reassign(HR, NEW_EVALUATOR, "부서장 교체", NOW)
    assert evaluation.status == EvaluationStatus.DRAFT


def test_reassigning_returned_evaluation_keeps_returned_state() -> None:
    evaluation = submitted()
    evaluation.return_for_revision(HR, "보완", NOW)
    evaluation.reassign(HR, NEW_EVALUATOR, "부서장 교체", NOW)
    assert evaluation.status == EvaluationStatus.RETURNED


def test_reassign_guards() -> None:
    with pytest.raises(SelfEvaluationError):
        make_draft().reassign(HR, MEMBER, "사유", NOW)
    with pytest.raises(InvalidEvaluationError):
        make_draft().reassign(HR, HEAD, "사유", NOW)
    with pytest.raises(InvalidEvaluationError):
        make_draft().reassign(HR, NEW_EVALUATOR, "", NOW)
    with pytest.raises(EvaluationPermissionError):
        make_draft().reassign(MEMBER, NEW_EVALUATOR, "사유", NOW)

    confirmed = submitted()
    confirmed.confirm(HR, {HEAD}, NOW)
    with pytest.raises(EvaluationStateError):
        confirmed.reassign(HR, NEW_EVALUATOR, "사유", NOW)


# Confirmation (EV-004 + separation of duties) --------------------------------------


def test_ev004_confirm_requires_submission() -> None:
    with pytest.raises(EvaluationStateError):
        make_draft().confirm(HR, {HEAD}, NOW)

    evaluation = submitted()
    evaluation.confirm(HR, {HEAD}, NOW)
    assert evaluation.status == EvaluationStatus.CONFIRMED
    assert evaluation.confirmed_by == HR
    assert evaluation.confirmed_at == NOW


@pytest.mark.parametrize(
    ("actor", "authors"),
    [
        (MEMBER, {HEAD}),  # the evaluated employee
        (HEAD, {HEAD}),  # the current evaluator
        (HR, {HEAD, HR}),  # a former evaluator who wrote part of the content
    ],
)
def test_confirmer_must_be_independent(actor: int, authors: set[int]) -> None:
    with pytest.raises(ConfirmationNotAllowedError):
        submitted().confirm(actor, authors, NOW)


def test_confirmed_evaluation_is_locked() -> None:
    evaluation = submitted()
    evaluation.confirm(HR, {HEAD}, NOW)

    with pytest.raises(EvaluationStateError):
        evaluation.revise(HEAD, Decimal("90"), "", NOW)
    with pytest.raises(EvaluationStateError):
        evaluation.confirm(9002, {HEAD}, NOW)
    with pytest.raises(EvaluationStateError):
        evaluation.exclude(HR, "사유", NOW)


def test_cancel_confirmation_returns_evaluation_to_evaluator() -> None:
    evaluation = submitted()
    evaluation.confirm(HR, {HEAD}, NOW)

    history = evaluation.cancel_confirmation(9002, "점수 오기 정정", NOW)
    assert evaluation.status == EvaluationStatus.RETURNED
    assert evaluation.confirmed_by is None
    assert evaluation.confirmed_at is None
    assert history.action == EvaluationAction.CANCEL_CONFIRMATION
    assert history.reason == "점수 오기 정정"
    assert not evaluation.is_visible_to(MEMBER, viewer_is_hr_manager=False)

    evaluation.revise(HEAD, Decimal("75"), None, NOW)
    evaluation.submit(HEAD, NOW)
    evaluation.confirm(HR, {HEAD}, NOW)
    assert evaluation.status == EvaluationStatus.CONFIRMED
    assert evaluation.grade == Grade.B


def test_cancel_confirmation_guards() -> None:
    with pytest.raises(EvaluationStateError):
        submitted().cancel_confirmation(HR, "사유", NOW)

    confirmed = submitted()
    confirmed.confirm(HR, {HEAD}, NOW)
    with pytest.raises(InvalidEvaluationError):
        confirmed.cancel_confirmation(HR, " ", NOW)
    with pytest.raises(EvaluationPermissionError):
        confirmed.cancel_confirmation(MEMBER, "사유", NOW)


# Exclusion -------------------------------------------------------------------------


@pytest.mark.parametrize("prepare", [make_draft, submitted])
def test_exclusion_is_a_separate_state_and_can_be_cancelled(prepare) -> None:
    evaluation = prepare()
    before = evaluation.status
    history = evaluation.exclude(HR, "장기 휴직으로 평가 불가", NOW)

    assert evaluation.status == EvaluationStatus.EXCLUDED
    assert evaluation.score == Decimal("85")  # not turned into a zero score
    with pytest.raises(EvaluationStateError):
        evaluation.revise(HEAD, Decimal("90"), None, NOW)

    evaluation.cancel_exclusion(HR, restorable_status([history]), "", NOW)
    assert evaluation.status == before


def test_exclusion_requires_reason() -> None:
    with pytest.raises(InvalidEvaluationError):
        make_draft().exclude(HR, "", NOW)


def test_target_cannot_handle_own_evaluation_as_hr() -> None:
    evaluation = submitted()
    with pytest.raises(EvaluationPermissionError):
        evaluation.return_for_revision(MEMBER, "사유", NOW)
    with pytest.raises(EvaluationPermissionError):
        evaluation.exclude(MEMBER, "사유", NOW)


def test_restorable_status_uses_latest_exclusion() -> None:
    def entry(action: EvaluationAction, from_status: EvaluationStatus) -> EvaluationHistory:
        return EvaluationHistory(None, 1, action, from_status, EvaluationStatus.EXCLUDED, HR, NOW)

    histories = [
        entry(EvaluationAction.EXCLUDE, EvaluationStatus.DRAFT),
        entry(EvaluationAction.CANCEL_EXCLUSION, EvaluationStatus.EXCLUDED),
        entry(EvaluationAction.EXCLUDE, EvaluationStatus.SUBMITTED),
    ]
    assert restorable_status(histories) == EvaluationStatus.SUBMITTED
    with pytest.raises(EvaluationStateError):
        restorable_status([])


# Visibility ------------------------------------------------------------------------


def test_visibility_follows_current_evaluator_and_confirmation() -> None:
    evaluation = make_draft()
    assert not evaluation.is_visible_to(MEMBER, viewer_is_hr_manager=False)
    assert evaluation.is_visible_to(HEAD, viewer_is_hr_manager=False)
    assert evaluation.is_visible_to(HR, viewer_is_hr_manager=True)

    evaluation.reassign(HR, NEW_EVALUATOR, "부서장 교체", NOW)
    assert not evaluation.is_visible_to(HEAD, viewer_is_hr_manager=False)
    assert evaluation.is_visible_to(NEW_EVALUATOR, viewer_is_hr_manager=False)

    evaluation.submit(NEW_EVALUATOR, NOW)
    evaluation.confirm(HR, {HEAD, NEW_EVALUATOR}, NOW)
    assert evaluation.is_visible_to(MEMBER, viewer_is_hr_manager=False)
    assert not evaluation.can_view_history(MEMBER, viewer_is_hr_manager=False)


# Architecture ----------------------------------------------------------------------

EVALUATION_ROOT = Path(__file__).parents[1] / "evaluation"


@pytest.mark.parametrize(
    ("layer", "forbidden_prefixes"),
    [
        (
            "domain",
            (
                "django",
                "rest_framework",
                "evaluation.application",
                "evaluation.infrastructure",
                "evaluation.presentation",
                "workforce",
            ),
        ),
        (
            "application",
            (
                "django",
                "rest_framework",
                "evaluation.infrastructure",
                "evaluation.presentation",
                "workforce",
            ),
        ),
    ],
)
def test_evaluation_inner_layers_do_not_import_outer_layers(
    layer: str,
    forbidden_prefixes: tuple[str, ...],
) -> None:
    violations: list[str] = []
    for path in sorted((EVALUATION_ROOT / layer).glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_modules: list[str] = []
            if isinstance(node, ast.Import):
                imported_modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules = [node.module]
            for module in imported_modules:
                if module.startswith(forbidden_prefixes):
                    violations.append(f"{path.name}: {module}")

    assert violations == []
