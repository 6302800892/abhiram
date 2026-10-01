"""AC-07 settlement module: compute (invariant-checked), persist append-only, stub payment, SETTLED."""

from __future__ import annotations

import logging
import sqlite3

from src.domain.claim_state_machine import ensure_case_mutable, transition
from src.domain.clock import Clock, iso
from src.domain.enums import CaseStatus
from src.domain.exceptions import BusinessRuleError
from src.domain.money import money_str, to_money
from src.domain.principal import Principal
from src.domain.settlement_calculator import SettlementBreakdown, SettlementInput, calculate_settlement
from src.repository import bill_repo, case_repo, settlement_repo
from src.service import case_service

logger = logging.getLogger("medicard.settlement")


def stub_payment_reference(case_id: int, attempt: int) -> str:
    return f"PAYSTUB-{case_id}-{attempt}"


def trigger_stub_payment(case_id: int, amount: str, reference: str) -> None:
    """Out of scope (brief 6.3): real payment rails. Fired only after the settlement row is committed."""
    logger.info("payment.stub_triggered", extra={"case_id": case_id, "amount": amount, "reference": reference})


def _settlement_input(conn: sqlite3.Connection, case: sqlite3.Row) -> SettlementInput:
    """Gather the AC-07 inputs: latest final bill, pre_auth_amount + buffer, deductible and co-pay."""
    bill = bill_repo.latest_bill(conn, case["id"])
    if bill is None:
        raise BusinessRuleError("FINAL_BILL_REQUIRED", "a final bill must be submitted before settlement")
    pre_auth_amount, buffer_pct = case_service.bill_terms(conn, case)
    rule = case_service.case_rule(conn, case)  # same recorded version as the bill cap (FL-001)
    return SettlementInput(
        pre_auth_amount=pre_auth_amount, buffer_pct=buffer_pct, final_bill=to_money(bill["amount"]),
        deductible=rule.deductible, copay_pct=rule.copay_pct,
    )


def settle(conn: sqlite3.Connection, principal: Principal, case_id: int, clock: Clock) -> dict[str, object]:
    """ST-R5/ST-R6: DISCHARGED or DISPUTED with a final bill -> one settlement row -> SETTLED."""
    case = case_service.load_visible(conn, principal, case_id)
    current = CaseStatus(case["status"])
    ensure_case_mutable(current)
    transition(current, CaseStatus.SETTLED)
    breakdown: SettlementBreakdown = calculate_settlement(_settlement_input(conn, case))  # invariant-checked
    now = iso(clock.now())
    amount = money_str(breakdown.settlement_amount)
    reference = stub_payment_reference(case_id, settlement_repo.count_for_case(conn, case_id) + 1)
    with conn:
        settlement_repo.insert(conn, case_id=case_id, breakdown=breakdown, payment_reference=reference,
                               settled_by=principal.username, settled_at=now)
        case_service.move(conn, case, CaseStatus.SETTLED, principal.username, now,
                          note=f"settled {amount}, payment {reference}")
    trigger_stub_payment(case_id, amount, reference)
    logger.info("case.settled", extra={"case_id": case_id, "settlement_amount": amount})
    view = settlement_view(conn, case_id)
    assert view is not None
    return view


def settlement_view(conn: sqlite3.Connection, case_id: int) -> dict[str, object] | None:
    """ST-R8 post-discharge summary."""
    row = settlement_repo.get(conn, case_id)
    if row is None:
        return None
    keys = ("pre_auth_amount", "buffer_pct", "cap", "final_bill", "admissible", "deductible", "copay",
            "settlement_amount", "payment_reference", "settled_by", "settled_at")
    case = case_repo.get_case(conn, case_id)
    return {"case_id": case_id, "case_status": case["status"] if case else None, **{k: row[k] for k in keys}}


def get_settlement(conn: sqlite3.Connection, principal: Principal, case_id: int) -> dict[str, object]:
    case_service.load_visible(conn, principal, case_id)
    view = settlement_view(conn, case_id)
    if view is None:
        raise BusinessRuleError("NOT_SETTLED", "case has not been settled yet")
    return view
