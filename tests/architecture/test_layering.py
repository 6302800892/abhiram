"""Structural rule: one-way layer imports (domain <- config <- repository <- service <- api <- main)."""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
RANK = {"domain": 1, "config": 2, "repository": 3, "service": 4, "api": 5, "main": 6}
DOMAIN_FORBIDDEN = {"fastapi", "starlette", "pydantic", "sqlite3", "uvicorn", "logging", "os"}


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _layer_of(path: Path) -> str:
    rel = path.relative_to(SRC).parts
    return rel[0] if len(rel) > 1 else rel[0].removesuffix(".py")


def _src_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if p.name != "__init__.py" or p.stat().st_size > 0]


@pytest.mark.parametrize("path", _src_files(), ids=lambda p: p.relative_to(SRC).as_posix())
def test_no_upward_imports(path: Path) -> None:
    layer = _layer_of(path)
    if layer not in RANK:
        pytest.skip("not a layered module")
    for name in _imports(path):
        if name.startswith("src."):
            target = name.split(".")[1]
            assert RANK.get(target, 0) <= RANK[layer], f"{path.name}: {layer} must not import {name}"


@pytest.mark.parametrize("path", sorted((SRC / "domain").glob("*.py")), ids=lambda p: p.name)
def test_domain_is_framework_and_io_free(path: Path) -> None:
    for name in _imports(path):
        assert name.split(".")[0] not in DOMAIN_FORBIDDEN, f"domain/{path.name} imports {name}"


def test_import_linter_contracts_are_declared() -> None:
    pyproject = (SRC.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert pyproject.count("[[tool.importlinter.contracts]]") >= 3
    assert '"src.api", "src.service", "src.repository", "src.config", "src.domain"' in pyproject
