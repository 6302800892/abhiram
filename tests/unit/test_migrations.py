"""NFR-05 / NA-R6: migrations apply in order with a checksum ledger; tampering aborts."""

import sqlite3
from pathlib import Path

import pytest

from src.repository.db import MigrationTamperedError, apply_migrations, connect


def _write(folder: Path, name: str, sql: str) -> Path:
    path = folder / name
    path.write_text(sql, encoding="utf-8")
    return path


@pytest.mark.nfr("NFR-05")
def test_migrations_apply_in_order_once(tmp_path: Path) -> None:
    mig = tmp_path / "migrations"
    mig.mkdir()
    _write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER PRIMARY KEY);")
    _write(mig, "0002_b.sql", "CREATE TABLE b (id INTEGER PRIMARY KEY);")
    conn = connect(str(tmp_path / "t.db"))
    assert apply_migrations(conn, mig) == ["0001_a.sql", "0002_b.sql"]
    assert apply_migrations(conn, mig) == []  # idempotent


@pytest.mark.nfr("NFR-05")
def test_tampered_applied_migration_raises(tmp_path: Path) -> None:
    mig = tmp_path / "migrations"
    mig.mkdir()
    first = _write(mig, "0001_a.sql", "CREATE TABLE a (id INTEGER PRIMARY KEY);")
    conn = connect(str(tmp_path / "t.db"))
    apply_migrations(conn, mig)
    first.write_text("CREATE TABLE a (id INTEGER PRIMARY KEY, sneaky TEXT);", encoding="utf-8")
    with pytest.raises(MigrationTamperedError):
        apply_migrations(conn, mig)


@pytest.mark.nfr("NFR-05")
def test_real_migrations_make_coverage_rules_append_only(tmp_path: Path) -> None:
    conn = connect(str(tmp_path / "t.db"))
    apply_migrations(conn)
    conn.execute("INSERT INTO policy_products (code, name, sum_insured, annual_premium, created_at) "
                 "VALUES ('X', 'X', '1.00', '1.00', '2026-01-01T00:00:00+00:00')")
    conn.execute(
        "INSERT INTO coverage_rule_versions (product_id, version, auto_approve_threshold, auto_approved_diagnoses, "
        "excluded_diagnoses, per_claim_cap, buffer_pct, deductible, copay_pct, reason_codes, published_by, "
        "published_at) VALUES (1, 1, '1.00', '[]', '[]', '1.00', '10', '0.00', '0', '[]', 'seed', 'now')"
    )
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("UPDATE coverage_rule_versions SET buffer_pct = '20'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        conn.execute("DELETE FROM coverage_rule_versions")
