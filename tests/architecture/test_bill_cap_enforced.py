"""NFR-08 rule (structural): final bills never bypass the cap; settlements never bypass the invariant."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"


def _function(path: Path, name: str) -> ast.FunctionDef:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} not found in {path.name}")


def _calls(node: ast.AST) -> set[str]:
    names = set()
    for call in ast.walk(node):
        if isinstance(call, ast.Call):
            func = call.func
            names.add(func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", ""))
    return names


@pytest.mark.nfr("NFR-08")
def test_submit_final_bill_calls_the_cap_rule() -> None:
    assert "ensure_bill_within_cap" in _calls(_function(SRC / "service" / "case_service.py", "submit_final_bill"))


@pytest.mark.nfr("NFR-08")
def test_settle_uses_the_calculator() -> None:
    assert "calculate_settlement" in _calls(_function(SRC / "service" / "settlement_service.py", "settle"))


@pytest.mark.nfr("NFR-08")
def test_calculator_asserts_invariant_before_returning() -> None:
    fn = _function(SRC / "domain" / "settlement_calculator.py", "calculate_settlement")
    assert "assert_settlement_invariant" in _calls(fn)


@pytest.mark.nfr("NFR-08")
@pytest.mark.parametrize(("module", "function"), [("case_service.py", "bill_terms"),
                                                   ("settlement_service.py", "_settlement_input"),
                                                   ("settlement_service.py", "settle")])
def test_money_paths_never_read_the_current_rule_version(module: str, function: str) -> None:
    """FL-001 lesson: bill cap and settlement terms come from the pre-auth's recorded rule version (ST-R1)."""
    assert "current_rule" not in _calls(_function(SRC / "service" / module, function))


@pytest.mark.nfr("NFR-08")
def test_no_other_module_inserts_settlements() -> None:
    writers = [p.name for p in SRC.rglob("*.py") if "INSERT INTO settlements" in p.read_text(encoding="utf-8")]
    assert writers == ["settlement_repo.py"]
