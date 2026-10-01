"""Settlements — one append-only row per case (the only writer of the settlements table)."""

from __future__ import annotations

import sqlite3

from src.domain.exceptions import ConflictError
from src.domain.money import money_str
from src.domain.settlement_calculator import SettlementBreakdown


def insert(
    conn: sqlite3.Connection, *, case_id: int, breakdown: SettlementBreakdown, payment_reference: str,
    settled_by: str, settled_at: str,
) -> None:
    b = breakdown
    try:
        _insert(conn, case_id, b, payment_reference, settled_by, settled_at)
    except sqlite3.IntegrityError as exc:  # UNIQUE(case_id): a concurrent settle won (SEC-08)
        raise ConflictError("CASE_SETTLED_IMMUTABLE", "case was settled concurrently") from exc


def _insert(conn: sqlite3.Connection, case_id: int, b: SettlementBreakdown, payment_reference: str,
            settled_by: str, settled_at: str) -> None:
    conn.execute(
        "INSERT INTO settlements (case_id, pre_auth_amount, buffer_pct, cap, final_bill, admissible, deductible, "
        "copay, settlement_amount, payment_reference, settled_by, settled_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            case_id, money_str(b.pre_auth_amount), str(b.buffer_pct), money_str(b.cap), money_str(b.final_bill),
            money_str(b.admissible), money_str(b.deductible_applied), money_str(b.copay),
            money_str(b.settlement_amount), payment_reference, settled_by, settled_at,
        ),
    )


def get(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute("SELECT * FROM settlements WHERE case_id = ?", (case_id,)).fetchone()
    return row


def amounts_for_policy(conn: sqlite3.Connection, policy_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT s.settlement_amount FROM settlements s JOIN claim_cases c ON c.id = s.case_id WHERE c.policy_id = ?",
        (policy_id,),
    )
    return [row[0] for row in rows]


def count_for_case(conn: sqlite3.Connection, case_id: int) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM settlements WHERE case_id = ?", (case_id,)).fetchone()[0])
