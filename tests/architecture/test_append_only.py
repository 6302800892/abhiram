"""NFR-02 / NFR-05 structural rule: every append-only table has UPDATE and DELETE abort triggers."""

from pathlib import Path

import pytest

from src.repository.db import apply_migrations, connect
from src.repository.schema import APPEND_ONLY_TABLES


@pytest.fixture
def conn(tmp_path: Path):  # type: ignore[no-untyped-def]
    connection = connect(str(tmp_path / "arch.db"))
    apply_migrations(connection)
    yield connection
    connection.close()


def _triggers(conn) -> set[str]:  # type: ignore[no-untyped-def]
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")}


@pytest.mark.nfr("NFR-02")
def test_append_only_tables_exist_and_have_both_triggers(conn) -> None:  # type: ignore[no-untyped-def]
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    triggers = _triggers(conn)
    for table in APPEND_ONLY_TABLES:
        assert table in tables, f"{table} missing"
        assert f"trg_{table}_no_update" in triggers, f"{table} lacks UPDATE guard"
        assert f"trg_{table}_no_delete" in triggers, f"{table} lacks DELETE guard"


@pytest.mark.nfr("NFR-05")
def test_migration_files_are_numbered_and_contiguous() -> None:
    folder = Path(__file__).resolve().parents[2] / "migrations"
    numbers = [int(p.name[:4]) for p in sorted(folder.glob("*.sql"))]
    assert numbers == list(range(1, len(numbers) + 1))
