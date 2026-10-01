"""AC-07 settlement: min(final_bill, pre_auth_amount + buffer) - deductible - co-pay, never negative."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.domain.bill_rules import bill_cap
from src.domain.exceptions import SettlementInvariantError
from src.domain.money import ZERO, percent_of, require_decimal


@dataclass(frozen=True)
class SettlementInput:
    pre_auth_amount: Decimal
    buffer_pct: Decimal
    final_bill: Decimal
    deductible: Decimal
    copay_pct: Decimal


@dataclass(frozen=True)
class SettlementBreakdown:
    pre_auth_amount: Decimal
    buffer_pct: Decimal
    cap: Decimal
    final_bill: Decimal
    admissible: Decimal
    deductible_applied: Decimal
    copay: Decimal
    settlement_amount: Decimal


def assert_settlement_invariant(settlement: Decimal, admissible: Decimal) -> None:
    """ST-R3: 0 <= settlement <= admissible. A breach is a defect and must never be persisted."""
    if settlement < ZERO or settlement > admissible:
        raise SettlementInvariantError(f"settlement {settlement} outside [0, {admissible}]")


def calculate_settlement(inp: SettlementInput) -> SettlementBreakdown:
    """ST-R2, quantizing only where the spec says (cap, co-pay)."""
    require_decimal(inp.pre_auth_amount, inp.buffer_pct, inp.final_bill, inp.deductible, inp.copay_pct)
    cap = bill_cap(inp.pre_auth_amount, inp.buffer_pct)
    admissible = min(inp.final_bill, cap)
    deductible_applied = min(inp.deductible, admissible)
    copay = percent_of(admissible - deductible_applied, inp.copay_pct)
    settlement = admissible - deductible_applied - copay
    assert_settlement_invariant(settlement, admissible)
    return SettlementBreakdown(
        pre_auth_amount=inp.pre_auth_amount, buffer_pct=inp.buffer_pct, cap=cap, final_bill=inp.final_bill,
        admissible=admissible, deductible_applied=deductible_applied, copay=copay, settlement_amount=settlement,
    )
