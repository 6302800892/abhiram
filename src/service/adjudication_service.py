"""AC-04 adjudicator workbench: review queue and manual decisions (AD-R1 .. AD-R5)."""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from decimal import Decimal

from src.config.logging_config import bind_case_id
from src.domain.clock import Clock, iso
from src.domain.enums import PreAuthStatus
from src.domain.exceptions import NotFoundError
from src.domain.money import money_str, quantize, to_money
from src.domain.preauth_rules import ensure_reason_codes, policy_cap, validate_decision_amount
from src.domain.preauth_state_machine import transition
from src.domain.principal import Principal
from src.repository import case_repo, policy_repo, preauth_repo
from src.service import coverage_service, preauth_service

logger = logging.getLogger("medicard.adjudication")
SECONDS_PER_HOUR = Decimal(3600)


def _age_hours(submitted_at: str, clock: Clock) -> str:
    elapsed = clock.now() - dt.datetime.fromisoformat(submitted_at)
    return money_str(quantize(Decimal(int(elapsed.total_seconds())) / SECONDS_PER_HOUR))


def queue(conn: sqlite3.Connection, clock: Clock) -> list[dict[str, object]]:
    """AD-R1: every PENDING pre-auth, oldest first."""
    return [
        {
            "preauth_id": row["id"], "case_id": row["case_id"], "case_number": case_repo.case_number(row["case_id"]),
            "hospital_code": row["hospital_code"],
            "member_id": row["member_code"], "policy_number": row["policy_number"],
            "diagnosis_code": row["diagnosis_code"], "estimated_cost": row["estimated_cost"],
            "submitted_at": row["submitted_at"], "age_hours": _age_hours(row["submitted_at"], clock),
        }
        for row in preauth_repo.list_by_current_status(conn, PreAuthStatus.PENDING.value)
    ]


def current_cap(conn: sqlite3.Connection, row: sqlite3.Row) -> Decimal:
    """Policy cap for this pre-auth: its own rule version x the policy's current remaining cover."""
    policy = policy_repo.find_policy_by_id(conn, row["policy_id"])
    if policy is None:
        raise NotFoundError("POLICY_NOT_FOUND", "policy not found")
    rule = preauth_service.rule_version_of(conn, row).rule
    return policy_cap(rule, coverage_service.remaining_sum_insured(conn, policy))


def decide(
    conn: sqlite3.Connection,
    principal: Principal,
    preauth_id: int,
    *,
    status: PreAuthStatus,
    approved_amount: Decimal | None,
    reason_codes: list[str],
    note: str | None,
    clock: Clock,
) -> dict[str, object]:
    """AD-R2..AD-R5: PENDING only; amount + reason codes validated; append a decision by the adjudicator."""
    row = preauth_service.load_visible(conn, principal, preauth_id)
    bind_case_id(row["case_id"])
    latest = preauth_service.current_decision(conn, preauth_id)
    current = PreAuthStatus(latest["status"])
    transition(current, status)
    codes = ensure_reason_codes(reason_codes, preauth_service.rule_version_of(conn, row).rule.reason_codes)
    amount = validate_decision_amount(status, approved_amount, to_money(row["estimated_cost"]),
                                      current_cap(conn, row))
    now = iso(clock.now())
    with conn:
        preauth_repo.append_decision(
            conn, preauth_id=preauth_id, status=status.value,
            approved_amount=money_str(amount) if amount is not None else None, reason_codes=codes,
            decided_by=principal.username, decided_at=now, note=note, expected_seq=latest["seq"],
        )
        preauth_service.record_preauth_status(conn, row["case_id"], current, status, principal.username, now, codes)
    logger.info("preauth.decided", extra={"preauth_id": preauth_id, "status": status.value, "reason_codes": codes})
    return preauth_service.view(conn, preauth_id)
