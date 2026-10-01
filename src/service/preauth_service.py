"""AC-03 / AC-04 / AC-05: pre-auth submission, auto-decision, query response and read models."""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from src.config.logging_config import bind_case_id
from src.domain.clock import Clock, iso
from src.domain.coverage_rules import CoverageRuleVersion
from src.domain.enums import SYSTEM_ACTOR, CaseStatus, PreAuthStatus, Role
from src.domain.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.domain.icd_stub import diagnosis_label
from src.domain.money import ZERO, money_str, to_money
from src.domain.preauth_rules import PA_QUERY_ANSWERED, PA_SUBMITTED, decide_auto
from src.domain.preauth_state_machine import transition
from src.domain.principal import Principal
from src.repository import case_repo, preauth_repo, product_repo
from src.service import coverage_service, eligibility_service, timeline_service

logger = logging.getLogger("medicard.preauth")


@dataclass(frozen=True)
class PreAuthRequest:
    member_id: str
    policy_number: str
    diagnosis_code: str
    estimated_cost: Decimal
    expected_admission_date: dt.date
    clinical_notes: str | None


def _decision_view(row: sqlite3.Row) -> dict[str, object]:
    return {
        "seq": row["seq"], "status": row["status"], "approved_amount": row["approved_amount"],
        "reason_codes": json.loads(row["reason_codes"]), "decided_by": row["decided_by"],
        "decided_at": row["decided_at"],
    }


def current_decision(conn: sqlite3.Connection, preauth_id: int) -> sqlite3.Row:
    return preauth_repo.decisions(conn, preauth_id)[-1]


def approved_amount(conn: sqlite3.Connection, preauth_id: int) -> Decimal | None:
    """pre_auth_amount = amount of the latest APPROVED / PARTIALLY_APPROVED decision, if current."""
    latest = current_decision(conn, preauth_id)
    return to_money(latest["approved_amount"]) if latest["approved_amount"] is not None else None


def view(conn: sqlite3.Connection, preauth_id: int) -> dict[str, object]:
    row = preauth_repo.get_preauth(conn, preauth_id)
    if row is None:
        raise NotFoundError("PREAUTH_NOT_FOUND", "pre-auth not found")
    decisions = [_decision_view(d) for d in preauth_repo.decisions(conn, preauth_id)]
    latest = decisions[-1]
    return {
        "preauth_id": row["id"], "case_id": row["case_id"], "case_number": case_repo.case_number(row["case_id"]),
        "case_status": row["case_status"], "hospital_code": row["hospital_code"], "member_id": row["member_code"],
        "policy_number": row["policy_number"], "diagnosis_code": row["diagnosis_code"],
        "diagnosis_label": diagnosis_label(row["diagnosis_code"]), "estimated_cost": row["estimated_cost"],
        "expected_admission_date": row["expected_admission_date"], "submitted_at": row["submitted_at"],
        "status": latest["status"], "approved_amount": latest["approved_amount"],
        "reason_codes": latest["reason_codes"], "decisions": decisions,
        "rule_version": {"product_code": row["rule_product_code"], "version": row["rule_version"]},
    }


def load_visible(conn: sqlite3.Connection, principal: Principal, preauth_id: int) -> sqlite3.Row:
    """PA-R8 / NFR-04: hospitals see only their own pre-auths; others get 404, never 403."""
    row = preauth_repo.get_preauth(conn, preauth_id)
    if row is None or (principal.role is Role.HOSPITAL and row["hospital_id"] != principal.hospital_id):
        raise NotFoundError("PREAUTH_NOT_FOUND", "pre-auth not found")
    bind_case_id(row["case_id"])
    return row


def rule_version_of(conn: sqlite3.Connection, row: sqlite3.Row) -> CoverageRuleVersion:
    return product_repo.get_version(conn, row["rule_product_id"], row["rule_product_code"], row["rule_version"])


def _validate_request(req: PreAuthRequest, clock: Clock) -> None:
    if req.estimated_cost <= ZERO:
        raise ValidationError("INVALID_ESTIMATED_COST", "estimated_cost must be greater than zero")
    if req.expected_admission_date < clock.today():
        raise ValidationError("ADMISSION_DATE_IN_PAST", "expected_admission_date cannot be in the past")


def _eligible_policy(conn: sqlite3.Connection, principal: Principal, req: PreAuthRequest, clock: Clock) -> tuple[
    sqlite3.Row, sqlite3.Row, Decimal
]:
    outcome = eligibility_service.evaluate(
        conn, member_id=req.member_id, policy_number=req.policy_number, hospital_id=principal.hospital_id, clock=clock
    )
    if not outcome.result.eligible or outcome.policy is None or outcome.member is None:
        raise BusinessRuleError("NOT_ELIGIBLE", "member is not eligible for cashless treatment",
                                {"reason_codes": list(outcome.result.reason_codes)})
    assert outcome.remaining_sum_insured is not None
    return outcome.policy, outcome.member, outcome.remaining_sum_insured


def record_preauth_status(
    conn: sqlite3.Connection, case_id: int, from_status: PreAuthStatus | None, to_status: PreAuthStatus, actor: str,
    now: str, reason_codes: list[str],
) -> None:
    """AM-R7: a pre-auth status change is a timeline event + customer notification."""
    timeline_service.record_status_change(
        conn, case_id, event=timeline_service.PREAUTH_STATUS, from_status=from_status.value if from_status else None,
        to_status=to_status.value, actor=actor, now=now, note=",".join(reason_codes),
    )


def _record_auto_decision(
    conn: sqlite3.Connection, case_id: int, preauth_id: int, req: PreAuthRequest, version: CoverageRuleVersion,
    remaining: Decimal, now: str,
) -> None:
    auto = decide_auto(req.estimated_cost, req.diagnosis_code, version.rule, remaining)
    if auto.status is not PreAuthStatus.PENDING:
        transition(PreAuthStatus.PENDING, auto.status)
    amount = money_str(auto.approved_amount) if auto.approved_amount is not None else None
    preauth_repo.append_decision(conn, preauth_id=preauth_id, status=auto.status.value, approved_amount=amount,
                                 reason_codes=[auto.reason_code], decided_by=SYSTEM_ACTOR, decided_at=now)
    if auto.status is not PreAuthStatus.PENDING:
        record_preauth_status(conn, case_id, PreAuthStatus.PENDING, auto.status, SYSTEM_ACTOR, now, [auto.reason_code])


def submit(conn: sqlite3.Connection, principal: Principal, req: PreAuthRequest, clock: Clock) -> dict[str, object]:
    """PA-R1..PA-R5: validate, check eligibility, create case + pre-auth, append PENDING then auto decision."""
    _validate_request(req, clock)
    policy, member, remaining = _eligible_policy(conn, principal, req, clock)
    version = coverage_service.current_rule(conn, policy)
    now = iso(clock.now())
    assert principal.hospital_id is not None
    with conn:
        case_id = case_repo.insert_case(conn, policy_id=policy["id"], member_row_id=member["id"],
                                        hospital_id=principal.hospital_id, status=CaseStatus.PRE_AUTH.value, now=now)
        preauth_id = preauth_repo.insert_preauth(
            conn, case_id=case_id, diagnosis_code=req.diagnosis_code, estimated_cost=money_str(req.estimated_cost),
            expected_admission_date=req.expected_admission_date.isoformat(), clinical_notes=req.clinical_notes,
            rule_product_id=policy["product_id"], rule_version=version.version, submitted_by=principal.username,
            submitted_at=now,
        )
        preauth_repo.append_decision(conn, preauth_id=preauth_id, status=PreAuthStatus.PENDING.value,
                                     approved_amount=None, reason_codes=[PA_SUBMITTED], decided_by=SYSTEM_ACTOR,
                                     decided_at=now)
        record_preauth_status(conn, case_id, None, PreAuthStatus.PENDING, principal.username, now, [PA_SUBMITTED])
        _record_auto_decision(conn, case_id, preauth_id, req, version, remaining, now)
    bind_case_id(case_id)
    result = view(conn, preauth_id)
    logger.info("preauth.submitted", extra={"preauth_id": preauth_id, "status": result["status"]})
    return result


def answer_query(
    conn: sqlite3.Connection, principal: Principal, preauth_id: int, response_note: str, clock: Clock
) -> dict[str, object]:
    """PA-R7: QUERY_RAISED -> PENDING with PA-QUERY-ANSWERED (own hospital only)."""
    row = load_visible(conn, principal, preauth_id)
    latest = current_decision(conn, preauth_id)
    current = PreAuthStatus(latest["status"])
    transition(current, PreAuthStatus.PENDING)
    now = iso(clock.now())
    with conn:
        preauth_repo.append_decision(conn, preauth_id=preauth_id, status=PreAuthStatus.PENDING.value,
                                     approved_amount=None, reason_codes=[PA_QUERY_ANSWERED],
                                     decided_by=principal.username, decided_at=now, note=response_note,
                                     expected_seq=latest["seq"])
        record_preauth_status(conn, row["case_id"], current, PreAuthStatus.PENDING, principal.username, now,
                              [PA_QUERY_ANSWERED])
    logger.info("preauth.query_answered", extra={"preauth_id": preauth_id})
    return view(conn, preauth_id)


def list_for(conn: sqlite3.Connection, principal: Principal) -> list[dict[str, object]]:
    hospital = principal.hospital_id if principal.role is Role.HOSPITAL else None
    return [view(conn, row["id"]) for row in preauth_repo.list_preauths(conn, hospital_id=hospital)]


