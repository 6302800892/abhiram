"""Pre-auth requests and the append-only decision stream (latest seq = current status)."""

from __future__ import annotations

import json
import sqlite3

from src.domain.exceptions import ConflictError

PREAUTH_SELECT = (
    "SELECT p.*, c.status AS case_status, c.hospital_id AS hospital_id, c.policy_id AS policy_id, "
    "c.member_row_id AS member_row_id, h.code AS hospital_code, m.member_id AS member_code, "
    "m.customer_id AS customer_id, pol.policy_number AS policy_number, prod.code AS rule_product_code "
    "FROM preauths p JOIN claim_cases c ON c.id = p.case_id JOIN hospitals h ON h.id = c.hospital_id "
    "JOIN members m ON m.id = c.member_row_id JOIN policies pol ON pol.id = c.policy_id "
    "JOIN policy_products prod ON prod.id = p.rule_product_id"
)
CURRENT_STATUS = (
    "(SELECT d.status FROM preauth_decisions d WHERE d.preauth_id = p.id ORDER BY d.seq DESC LIMIT 1)"
)


def insert_preauth(conn: sqlite3.Connection, **values: object) -> int:
    cur = conn.execute(
        "INSERT INTO preauths (case_id, diagnosis_code, estimated_cost, expected_admission_date, clinical_notes, "
        "rule_product_id, rule_version, submitted_by, submitted_at) VALUES (:case_id, :diagnosis_code, "
        ":estimated_cost, :expected_admission_date, :clinical_notes, :rule_product_id, :rule_version, "
        ":submitted_by, :submitted_at)",
        values,
    )
    return int(cur.lastrowid or 0)


def append_decision(
    conn: sqlite3.Connection,
    *,
    preauth_id: int,
    status: str,
    approved_amount: str | None,
    reason_codes: list[str],
    decided_by: str,
    decided_at: str,
    note: str | None = None,
    expected_seq: int | None = None,
) -> int:
    """Append the next decision. With `expected_seq` (the seq the caller decided on), a concurrent writer
    that got there first makes UNIQUE(preauth_id, seq) fail -> 409 instead of a second decision."""
    if expected_seq is None:
        seq_row = conn.execute("SELECT COALESCE(MAX(seq), 0) + 1 FROM preauth_decisions WHERE preauth_id = ?",
                               (preauth_id,)).fetchone()
        seq = int(seq_row[0])
    else:
        seq = expected_seq + 1
    try:
        conn.execute(
            "INSERT INTO preauth_decisions (preauth_id, seq, status, approved_amount, reason_codes, note, decided_by, "
            "decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (preauth_id, seq, status, approved_amount, json.dumps(reason_codes), note, decided_by, decided_at),
        )
    except sqlite3.IntegrityError as exc:
        raise ConflictError("INVALID_PREAUTH_STATE", "pre-auth changed concurrently; reload and retry") from exc
    return seq


def get_preauth(conn: sqlite3.Connection, preauth_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(f"{PREAUTH_SELECT} WHERE p.id = ?", (preauth_id,)).fetchone()
    return row


def get_by_case(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(f"{PREAUTH_SELECT} WHERE p.case_id = ?", (case_id,)).fetchone()
    return row


def decisions(conn: sqlite3.Connection, preauth_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM preauth_decisions WHERE preauth_id = ? ORDER BY seq", (preauth_id,)))


def list_preauths(conn: sqlite3.Connection, *, hospital_id: int | None = None) -> list[sqlite3.Row]:
    if hospital_id is None:
        return list(conn.execute(f"{PREAUTH_SELECT} ORDER BY p.id"))
    return list(conn.execute(f"{PREAUTH_SELECT} WHERE c.hospital_id = ? ORDER BY p.id", (hospital_id,)))


def list_by_current_status(conn: sqlite3.Connection, status: str) -> list[sqlite3.Row]:
    """Pre-auths whose latest decision has `status`, oldest submission first."""
    return list(
        conn.execute(f"{PREAUTH_SELECT} WHERE {CURRENT_STATUS} = ? ORDER BY p.submitted_at, p.id", (status,))
    )
