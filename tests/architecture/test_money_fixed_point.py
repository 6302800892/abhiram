"""NFR-01 structural rule: no float in domain / service / repository code; money columns are TEXT."""

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECKED = [p for layer in ("domain", "service", "repository") for p in sorted((ROOT / "src" / layer).glob("*.py"))]
MONEY_COLUMNS = re.compile(
    r"\b(\w*(amount|cost|bill|cap|deductible|copay|premium|sum_insured|threshold|paid)\w*)\s+(REAL|FLOAT|DOUBLE)\b",
    re.IGNORECASE,
)


def _float_uses(tree: ast.AST) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "float":
            lines.append(node.lineno)
        elif isinstance(node, ast.Constant) and isinstance(node.value, float):
            lines.append(node.lineno)
    return lines


@pytest.mark.nfr("NFR-01")
@pytest.mark.parametrize("path", CHECKED, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_no_float_in_money_layers(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    lines = [n for n in _float_uses(ast.parse(source)) if "money-float-ok" not in source.splitlines()[n - 1]]
    assert lines == [], f"float used at lines {lines}"


@pytest.mark.nfr("NFR-01")
def test_money_columns_are_never_real() -> None:
    for sql in sorted((ROOT / "migrations").glob("*.sql")):
        assert not MONEY_COLUMNS.search(sql.read_text(encoding="utf-8")), sql.name
