"""AC-10 insurer-admin override with an audit record written in the same transaction (AD-R6 .. AD-R8)."""

from __future__ import annotations

import logging
import sqlite3
from decimal import Decimal

from src.domain.clock import Clock, iso
from src.domain.enums import CaseStatus, PreAuthStatus
from src.domain.exceptions import InvalidClaimStateException
from src.domain.money import money_str, to_money
from src.domain.override_policy import ensure_override_allowed
from src.domain.preauth_rules import PA_OVERRIDE, ensure_reason_codes, validate_decision_amount
from src.domain.preauth_state_machine import transition
from src.domain.principal import Principal
from src.repository import audit_repo, preauth_repo
from src.service import adjudication_service, preauth_service

logger = logging.getLogger("medicard.override")
ACTION = "PREAUTH_OVERRIDE"


def override(
    conn: sqlite3.Connection,
    principal: Principal,
    preauth_id: int,
    *,
    target: PreAuthStatus,
    approved_amount: Decimal | None,
    reason: str,
    clock: Clock,
) -> dict[str, object]:
    """Validate (policy, state edge, amount, catalogue), then append decision + audit atomically."""
    row = preauth_service.load_visible(conn, principal, preauth_id)
    if CaseStatus(row["case_status"]) is not CaseStatus.PRE_AUTH:  # AD-R6 (SEC-09)
        raise InvalidClaimStateException(row["case_status"], "override requires a PRE_AUTH case")
    latest = preauth_service.current_decision(conn, preauth_id)
    current = PreAuthStatus(latest["status"])
    cleaned = ensure_override_allowed(current, decided_by=latest["decided_by"], target=target, reason=reason)
    transition(current, target, override=True)
    codes = ensure_reason_codes([PA_OVERRIDE], preauth_service.rule_version_of(conn, row).rule.reason_codes)
    amount = validate_decision_amount(target, approved_amount, to_money(row["estimated_cost"]),
                                      adjudication_service.current_cap(conn, row))
    now = iso(clock.now())
    with conn:  # one transaction: no audit record => no override (AD-R7)
        preauth_repo.append_decision(
            conn, preauth_id=preauth_id, status=target.value,
            approved_amount=money_str(amount) if amount is not None else None, reason_codes=codes,
            decided_by=principal.username, decided_at=now, note=cleaned, expected_seq=latest["seq"],
        )
        audit_repo.insert(conn, actor=principal.username, action=ACTION, entity_type="preauth", entity_id=preauth_id,
                          from_status=current.value, to_status=target.value, reason=cleaned, occurred_at=now)
        preauth_service.record_preauth_status(conn, row["case_id"], current, target, principal.username, now, codes)
    logger.info("preauth.overridden", extra={"preauth_id": preauth_id, "from_status": current.value,
                                             "to_status": target.value})
    return preauth_service.view(conn, preauth_id)


def audit_log(conn: sqlite3.Connection) -> list[dict[str, object]]:
    """AD-R8: newest first."""
    keys = ("id", "actor", "action", "entity_type", "entity_id", "from_status", "to_status", "reason", "occurred_at")
    return [{k: row[k] for k in keys} for row in audit_repo.list_recent(conn)]
