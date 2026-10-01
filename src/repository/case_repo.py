"""Claim cases. The status column is the projection of the append-only case_events stream (sprint 3)."""

from __future__ import annotations

import sqlite3

CASE_SELECT = (
    "SELECT c.*, h.code AS hospital_code, h.name AS hospital_name, m.member_id AS member_code, "
    "m.full_name AS member_name, m.customer_id AS customer_id, pol.policy_number AS policy_number "
    "FROM claim_cases c JOIN hospitals h ON h.id = c.hospital_id JOIN members m ON m.id = c.member_row_id "
    "JOIN policies pol ON pol.id = c.policy_id"
)


def insert_case(
    conn: sqlite3.Connection, *, policy_id: int, member_row_id: int, hospital_id: int, status: str, now: str
) -> int:
    cur = conn.execute(
        "INSERT INTO claim_cases (policy_id, member_row_id, hospital_id, status, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (policy_id, member_row_id, hospital_id, status, now, now),
    )
    return int(cur.lastrowid or 0)


def get_case(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(f"{CASE_SELECT} WHERE c.id = ?", (case_id,)).fetchone()
    return row


def set_status(conn: sqlite3.Connection, case_id: int, status: str, now: str) -> None:
    conn.execute("UPDATE claim_cases SET status = ?, updated_at = ? WHERE id = ?", (status, now, case_id))


def list_cases(
    conn: sqlite3.Connection, *, hospital_id: int | None = None, customer_id: int | None = None
) -> list[sqlite3.Row]:
    clauses, params = [], []
    if hospital_id is not None:
        clauses.append("c.hospital_id = ?")
        params.append(hospital_id)
    if customer_id is not None:
        clauses.append("m.customer_id = ?")
        params.append(customer_id)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return list(conn.execute(f"{CASE_SELECT}{where} ORDER BY c.id", params))


def case_number(case_id: int) -> str:
    return f"CASE-{case_id:06d}"
