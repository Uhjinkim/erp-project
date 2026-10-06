import ast
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from evaluation.domain.entities import (
    Evaluation,
    EvaluationStatus,
    EvaluationTarget,
    ensure_can_evaluate,
)
from evaluation.domain.exceptions import (
    EvaluationPermissionError,
    EvaluationStateError,
    InvalidEvaluationError,
    SelfEvaluationError,
)
from evaluation.domain.value_objects import EvaluationScore, EvaluationYear, Grade

NOW = datetime(2026, 10, 6, tzinfo=UTC)
HEAD = 2001
MEMBER = 1001
TARGET = EvaluationTarget(
    employee_no=MEMBER,
    is_active=True,
    department_no=10,
    position_code="STAFF",
    department_head_no=HEAD,
)


def make_draft(score: str = "85") -> Evaluation:
    return Evaluation.draft(
        target=TARGET,
        evaluator_no=HEAD,
        eval_year="2026",
        score=Decimal(score),
        comments="성실함",
        now=NOW,
    )


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


def test_ev001_department_head_creates_draft_with_snapshot() -> None:
    evaluation = make_draft("91.5")

    assert evaluation.status == EvaluationStatus.DRAFT
    assert evaluation.grade == Grade.S
    assert evaluation.snapshot_department_no == 10
    assert evaluation.snapshot_position_code == "STAFF"
    assert evaluation.evaluator_no == HEAD


def test_ev001_only_department_head_can_evaluate() -> None:
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(3001, TARGET)


def test_ev001_target_without_department_head_cannot_be_evaluated() -> None:
    target = EvaluationTarget(MEMBER, True, None, None, None)
    with pytest.raises(EvaluationPermissionError):
        ensure_can_evaluate(HEAD, target)


def test_ev002_self_evaluation_is_rejected_even_for_department_head() -> None:
    head_target = EvaluationTarget(HEAD, True, 10, "MANAGER", HEAD)
    with pytest.raises(SelfEvaluationError):
        ensure_can_evaluate(HEAD, head_target)


def test_evaluator_can_revise_draft_and_grade_is_recalculated() -> None:
    evaluation = make_draft("85")
    evaluation.revise(HEAD, Decimal("65"), "보완 필요", NOW)

    assert evaluation.score == Decimal("65")
    assert evaluation.grade == Grade.C
    assert evaluation.comments == "보완 필요"


def test_only_evaluator_can_revise() -> None:
    evaluation = make_draft()
    with pytest.raises(EvaluationPermissionError):
        evaluation.revise(3001, Decimal("90"), "", NOW)


def test_ev004_confirmed_evaluation_is_locked() -> None:
    evaluation = make_draft()
    evaluation.confirm(9001, NOW)

    assert evaluation.status == EvaluationStatus.CONFIRMED
    assert evaluation.confirmed_by == 9001
    assert evaluation.confirmed_at == NOW
    with pytest.raises(EvaluationStateError):
        evaluation.revise(HEAD, Decimal("90"), "", NOW)
    with pytest.raises(EvaluationStateError):
        evaluation.confirm(9001, NOW)


def test_target_sees_own_evaluation_only_after_confirmation() -> None:
    evaluation = make_draft()
    assert not evaluation.is_visible_to(MEMBER, viewer_is_hr_manager=False)
    assert evaluation.is_visible_to(HEAD, viewer_is_hr_manager=False)
    assert evaluation.is_visible_to(9001, viewer_is_hr_manager=True)
    assert not evaluation.is_visible_to(3001, viewer_is_hr_manager=False)

    evaluation.confirm(9001, NOW)
    assert evaluation.is_visible_to(MEMBER, viewer_is_hr_manager=False)


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
