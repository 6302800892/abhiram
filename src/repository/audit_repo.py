"""Append-only audit records for privileged actions (AC-10)."""

from __future__ import annotations

import sqlite3


def insert(
    conn: sqlite3.Connection,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: int,
    from_status: str | None,
    to_status: str | None,
    reason: str,
    occurred_at: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO audit_records (actor, action, entity_type, entity_id, from_status, to_status, reason, "
        "occurred_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (actor, action, entity_type, entity_id, from_status, to_status, reason, occurred_at),
    )
    return int(cur.lastrowid or 0)


def list_recent(conn: sqlite3.Connection, limit: int = 200) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM audit_records ORDER BY id DESC LIMIT ?", (limit,)))
