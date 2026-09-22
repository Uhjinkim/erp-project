import ast
from pathlib import Path

import pytest

PAYROLL_ROOT = Path(__file__).parents[1] / "payroll"


@pytest.mark.parametrize(
    ("layer", "forbidden_prefixes"),
    [
        (
            "domain",
            ("django", "rest_framework", "payroll.application", "payroll.infrastructure"),
        ),
        (
            "application",
            ("django", "rest_framework", "payroll.infrastructure", "payroll.presentation"),
        ),
    ],
)
def test_payroll_inner_layers_do_not_import_outer_layers(
    layer: str,
    forbidden_prefixes: tuple[str, ...],
) -> None:
    violations: list[str] = []
    for path in sorted((PAYROLL_ROOT / layer).glob("*.py")):
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
