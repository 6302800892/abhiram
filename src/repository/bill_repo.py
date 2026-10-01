"""Procedures and versioned final bills (append-only; latest version is the final bill)."""

from __future__ import annotations

import sqlite3


def add_procedure(
    conn: sqlite3.Connection, *, case_id: int, procedure_code: str, description: str, recorded_by: str,
    recorded_at: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO procedures (case_id, procedure_code, description, recorded_by, recorded_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (case_id, procedure_code, description, recorded_by, recorded_at),
    )
    return int(cur.lastrowid or 0)


def procedures(conn: sqlite3.Connection, case_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM procedures WHERE case_id = ? ORDER BY id", (case_id,)))


def append_bill(
    conn: sqlite3.Connection, *, case_id: int, amount: str, cap: str, submitted_by: str, submitted_at: str
) -> int:
    version = int(conn.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM final_bills WHERE case_id = ?",
                               (case_id,)).fetchone()[0])
    conn.execute(
        "INSERT INTO final_bills (case_id, version, amount, cap, submitted_by, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
        (case_id, version, amount, cap, submitted_by, submitted_at),
    )
    return version


def bills(conn: sqlite3.Connection, case_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM final_bills WHERE case_id = ? ORDER BY version", (case_id,)))


def latest_bill(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(
        "SELECT * FROM final_bills WHERE case_id = ? ORDER BY version DESC LIMIT 1", (case_id,)
    ).fetchone()
    return row
