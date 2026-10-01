"""AC-06 / AC-08: admission, procedures, final bill (capped), discharge, dispute, close, case read models."""

from __future__ import annotations

import datetime as dt
import logging
import sqlite3
from decimal import Decimal

from src.config.logging_config import bind_case_id
from src.domain.bill_rules import ensure_bill_within_cap
from src.domain.claim_state_machine import require_status, transition
from src.domain.clock import Clock, iso
from src.domain.coverage_rules import CoverageRule
from src.domain.enums import CaseStatus, PreAuthStatus, Role
from src.domain.exceptions import BusinessRuleError, InvalidClaimStateException, NotFoundError, ValidationError
from src.domain.money import ZERO, money_str
from src.domain.preauth_state_machine import APPROVAL_STATUSES
from src.domain.principal import Principal
from src.repository import bill_repo, case_repo, preauth_repo
from src.service import preauth_service, timeline_service

logger = logging.getLogger("medicard.case")


def load_visible(conn: sqlite3.Connection, principal: Principal, case_id: int) -> sqlite3.Row:
    """AM-R8 / NFR-04: hospitals see own cases, customers see their members' cases, staff see all."""
    case = case_repo.get_case(conn, case_id)
    hidden = case is None or (
        (principal.role is Role.HOSPITAL and case["hospital_id"] != principal.hospital_id)
        or (principal.role is Role.CUSTOMER
            and (principal.customer_id is None or case["customer_id"] != principal.customer_id))
    )
    if hidden or case is None:
        raise NotFoundError("CASE_NOT_FOUND", "case not found")
    bind_case_id(case_id)
    return case


def _preauth(conn: sqlite3.Connection, case_id: int) -> sqlite3.Row:
    row = preauth_repo.get_by_case(conn, case_id)
    assert row is not None, "every case is created with its pre-auth"
    return row


def _preauth_status(conn: sqlite3.Connection, case_id: int) -> PreAuthStatus:
    return PreAuthStatus(preauth_service.current_decision(conn, _preauth(conn, case_id)["id"])["status"])


def case_rule(conn: sqlite3.Connection, case: sqlite3.Row) -> CoverageRule:
    """ST-R1/ST-R2 (FL-001): the rule version recorded on the case's pre-auth, never the current one."""
    return preauth_service.rule_version_of(conn, _preauth(conn, case["id"])).rule


def bill_terms(conn: sqlite3.Connection, case: sqlite3.Row) -> tuple[Decimal, Decimal]:
    """(pre_auth_amount, buffer_pct) used for the AC-06 cap and the AC-07 settlement."""
    amount = preauth_service.approved_amount(conn, _preauth(conn, case["id"])["id"])
    return amount if amount is not None else ZERO, case_rule(conn, case).buffer_pct


def move(
    conn: sqlite3.Connection, case: sqlite3.Row, target: CaseStatus, actor: str, now: str,
    event_date: str | None = None, note: str | None = None,
) -> None:
    """Validate the edge, update the projection and append event + notification (caller owns the transaction)."""
    current = CaseStatus(case["status"])
    transition(current, target)
    case_repo.set_status(conn, case["id"], target.value, now)
    timeline_service.record_status_change(conn, case["id"], event=timeline_service.CASE_STATUS,
                                          from_status=current.value, to_status=target.value, actor=actor, now=now,
                                          event_date=event_date, note=note)


def _moved(conn: sqlite3.Connection, case: sqlite3.Row, target: CaseStatus, principal: Principal, clock: Clock,
           event_date: str | None = None, note: str | None = None) -> dict[str, object]:
    with conn:
        move(conn, case, target, principal.username, iso(clock.now()), event_date, note)
    logger.info("case.transition", extra={"case_id": case["id"], "to_status": target.value})
    return detail(conn, case["id"])


def admit(conn: sqlite3.Connection, principal: Principal, case_id: int, admitted_on: dt.date,
          clock: Clock) -> dict[str, object]:
    """AM-R2: PRE_AUTH -> ADMITTED only with an APPROVED / PARTIALLY_APPROVED pre-auth."""
    case = load_visible(conn, principal, case_id)
    transition(CaseStatus(case["status"]), CaseStatus.ADMITTED)
    if _preauth_status(conn, case_id) not in APPROVAL_STATUSES:
        raise BusinessRuleError("PREAUTH_NOT_APPROVED", "admission needs an approved pre-authorization")
    return _moved(conn, case, CaseStatus.ADMITTED, principal, clock, event_date=admitted_on.isoformat())


def add_procedure(conn: sqlite3.Connection, principal: Principal, case_id: int, procedure_code: str,
                  description: str, clock: Clock) -> dict[str, object]:
    """AM-R3: procedures only while ADMITTED."""
    case = load_visible(conn, principal, case_id)
    require_status(CaseStatus(case["status"]), CaseStatus.ADMITTED)
    now = iso(clock.now())
    with conn:
        bill_repo.add_procedure(conn, case_id=case_id, procedure_code=procedure_code, description=description,
                                recorded_by=principal.username, recorded_at=now)
        timeline_service.record_info(conn, case_id, event_type="PROCEDURE", actor=principal.username, now=now,
                                     note=f"procedure {procedure_code} recorded")
    logger.info("case.procedure_added", extra={"case_id": case_id})
    return detail(conn, case_id)


def submit_final_bill(conn: sqlite3.Connection, principal: Principal, case_id: int, amount: Decimal,
                      clock: Clock) -> dict[str, object]:
    """AM-R4 / AC-06: ADMITTED or DISCHARGED; final_bill <= pre_auth_amount + buffer; appended as a new version."""
    case = load_visible(conn, principal, case_id)
    require_status(CaseStatus(case["status"]), CaseStatus.ADMITTED, CaseStatus.DISCHARGED)
    if amount <= ZERO:
        raise ValidationError("INVALID_BILL_AMOUNT", "final bill must be greater than zero")
    pre_auth_amount, buffer_pct = bill_terms(conn, case)
    cap = ensure_bill_within_cap(pre_auth_amount, buffer_pct, amount)
    now = iso(clock.now())
    with conn:
        version = bill_repo.append_bill(conn, case_id=case_id, amount=money_str(amount), cap=money_str(cap),
                                        submitted_by=principal.username, submitted_at=now)
        timeline_service.record_info(conn, case_id, event_type="FINAL_BILL", actor=principal.username, now=now,
                                     note=f"final bill v{version}: {money_str(amount)} (cap {money_str(cap)})")
    logger.info("case.final_bill_submitted", extra={"case_id": case_id, "version": version})
    return {"case_id": case_id, "version": version, "amount": money_str(amount), "cap": money_str(cap)}


def discharge(conn: sqlite3.Connection, principal: Principal, case_id: int, discharged_on: dt.date,
              clock: Clock) -> dict[str, object]:
    case = load_visible(conn, principal, case_id)
    return _moved(conn, case, CaseStatus.DISCHARGED, principal, clock, event_date=discharged_on.isoformat())


def dispute(conn: sqlite3.Connection, principal: Principal, case_id: int, reason: str,
            clock: Clock) -> dict[str, object]:
    case = load_visible(conn, principal, case_id)
    if not reason.strip():
        raise ValidationError("DISPUTE_REASON_REQUIRED", "a dispute reason is required")
    return _moved(conn, case, CaseStatus.DISPUTED, principal, clock, note=reason.strip()[:500])


def close(conn: sqlite3.Connection, principal: Principal, case_id: int, clock: Clock) -> dict[str, object]:
    """AM-R6: SETTLED / DISPUTED -> CLOSED; PRE_AUTH -> CLOSED only when the pre-auth is REJECTED."""
    case = load_visible(conn, principal, case_id)
    current = CaseStatus(case["status"])
    transition(current, CaseStatus.CLOSED)
    if current is CaseStatus.PRE_AUTH and _preauth_status(conn, case_id) is not PreAuthStatus.REJECTED:
        raise InvalidClaimStateException(current.value, f"{CaseStatus.CLOSED.value} (pre-auth not rejected)")
    return _moved(conn, case, CaseStatus.CLOSED, principal, clock)


def summary(case: sqlite3.Row) -> dict[str, object]:
    return {
        "case_id": case["id"], "case_number": case_repo.case_number(case["id"]), "status": case["status"],
        "hospital_code": case["hospital_code"], "hospital_name": case["hospital_name"],
        "member_id": case["member_code"], "member_name": case["member_name"], "policy_number": case["policy_number"],
        "created_at": case["created_at"], "updated_at": case["updated_at"],
    }


def detail(conn: sqlite3.Connection, case_id: int) -> dict[str, object]:
    from src.service import settlement_service  # local import: settlement_service depends on this module

    case = case_repo.get_case(conn, case_id)
    assert case is not None
    pre = preauth_service.view(conn, _preauth(conn, case_id)["id"])
    return {
        **summary(case),
        "preauth": {k: pre[k] for k in ("preauth_id", "status", "estimated_cost", "approved_amount",
                                        "diagnosis_code", "reason_codes")},
        "procedures": [{"procedure_code": p["procedure_code"], "description": p["description"],
                        "recorded_at": p["recorded_at"]} for p in bill_repo.procedures(conn, case_id)],
        "final_bills": [{"version": b["version"], "amount": b["amount"], "cap": b["cap"],
                         "submitted_at": b["submitted_at"]} for b in bill_repo.bills(conn, case_id)],
        "settlement": settlement_service.settlement_view(conn, case_id),
    }


def list_cases(conn: sqlite3.Connection, principal: Principal) -> list[dict[str, object]]:
    hospital = principal.hospital_id if principal.role is Role.HOSPITAL else None
    customer = principal.customer_id if principal.role is Role.CUSTOMER else None
    if principal.role is Role.CUSTOMER and customer is None:
        return []
    return [summary(c) for c in case_repo.list_cases(conn, hospital_id=hospital, customer_id=customer)]
