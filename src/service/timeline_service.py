"""AC-09 / AM-R7: every status change appends a timeline event and one STUB customer notification."""

from __future__ import annotations

import logging
import sqlite3

from src.repository import case_repo, event_repo

logger = logging.getLogger("medicard.timeline")
PREAUTH_STATUS = "PREAUTH_STATUS"
CASE_STATUS = "CASE_STATUS"


def _notify(conn: sqlite3.Connection, case: sqlite3.Row, event: str, to_status: str, now: str) -> None:
    """Stub channel: persist the message the customer would receive. No diagnosis/procedure text (NFR-03)."""
    subject = "pre-authorization" if event == PREAUTH_STATUS else "cashless case"
    message = f"{case_repo.case_number(case['id'])}: your {subject} status is now {to_status}."
    event_repo.append_notification(conn, case_id=case["id"], member_row_id=case["member_row_id"], event=event,
                                   to_status=to_status, message=message, created_at=now)
    logger.info("notification.stub_sent", extra={"case_id": case["id"], "event": event, "to_status": to_status})


def record_status_change(
    conn: sqlite3.Connection,
    case_id: int,
    *,
    event: str,
    from_status: str | None,
    to_status: str,
    actor: str,
    now: str,
    event_date: str | None = None,
    note: str | None = None,
) -> None:
    """Append the timeline event and send the customer notification (call inside the caller's transaction)."""
    case = case_repo.get_case(conn, case_id)
    assert case is not None
    event_repo.append_event(conn, case_id=case_id, event_type=event, from_status=from_status, to_status=to_status,
                            actor=actor, occurred_at=now, event_date=event_date, note=note)
    _notify(conn, case, event, to_status, now)


def record_info(conn: sqlite3.Connection, case_id: int, *, event_type: str, actor: str, now: str, note: str) -> None:
    """Non-transition timeline entries (procedure added, bill submitted): no notification."""
    event_repo.append_event(conn, case_id=case_id, event_type=event_type, from_status=None, to_status=None,
                            actor=actor, occurred_at=now, note=note)


def timeline_view(conn: sqlite3.Connection, case_id: int) -> list[dict[str, object]]:
    return [
        {
            "event_type": e["event_type"], "from_status": e["from_status"], "to_status": e["to_status"],
            "actor": e["actor"], "occurred_at": e["occurred_at"], "event_date": e["event_date"], "note": e["note"],
        }
        for e in event_repo.timeline(conn, case_id)
    ]


def notifications_view(conn: sqlite3.Connection, customer_id: int) -> list[dict[str, object]]:
    return [
        {
            "case_id": n["case_id"], "channel": n["channel"], "event": n["event"], "to_status": n["to_status"],
            "message": n["message"], "created_at": n["created_at"],
        }
        for n in event_repo.notifications_for_customer(conn, customer_id)
    ]
