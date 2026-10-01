"""Append-only case timeline and stub customer notifications (AC-09)."""

from __future__ import annotations

import sqlite3


def append_event(
    conn: sqlite3.Connection,
    *,
    case_id: int,
    event_type: str,
    from_status: str | None,
    to_status: str | None,
    actor: str,
    occurred_at: str,
    event_date: str | None = None,
    note: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO case_events (case_id, event_type, from_status, to_status, actor, occurred_at, event_date, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (case_id, event_type, from_status, to_status, actor, occurred_at, event_date, note),
    )


def timeline(conn: sqlite3.Connection, case_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM case_events WHERE case_id = ? ORDER BY id", (case_id,)))


def append_notification(
    conn: sqlite3.Connection, *, case_id: int, member_row_id: int, event: str, to_status: str, message: str,
    created_at: str,
) -> None:
    conn.execute(
        "INSERT INTO notifications (case_id, member_row_id, channel, event, to_status, message, created_at) "
        "VALUES (?, ?, 'STUB', ?, ?, ?, ?)",
        (case_id, member_row_id, event, to_status, message, created_at),
    )


def notifications_for_customer(conn: sqlite3.Connection, customer_id: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT n.* FROM notifications n JOIN members m ON m.id = n.member_row_id WHERE m.customer_id = ? "
            "ORDER BY n.id",
            (customer_id,),
        )
    )
