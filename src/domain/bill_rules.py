"""AC-06 / ST-R1 final-bill cap: final_bill <= pre_auth_amount + pre_auth_amount x buffer_pct / 100."""

from __future__ import annotations

from decimal import Decimal

from src.domain.exceptions import BusinessRuleError
from src.domain.money import money_str, percent_of, quantize, require_decimal


def bill_cap(pre_auth_amount: Decimal, buffer_pct: Decimal) -> Decimal:
    require_decimal(pre_auth_amount, buffer_pct)
    return quantize(pre_auth_amount + percent_of(pre_auth_amount, buffer_pct))


def bill_within_cap(pre_auth_amount: Decimal, buffer_pct: Decimal, final_bill: Decimal) -> bool:
    require_decimal(final_bill)
    return final_bill <= bill_cap(pre_auth_amount, buffer_pct)


def ensure_bill_within_cap(pre_auth_amount: Decimal, buffer_pct: Decimal, final_bill: Decimal) -> Decimal:
    """Return the cap, or raise BILL_EXCEEDS_CAP (422) — boundary inclusive."""
    cap = bill_cap(pre_auth_amount, buffer_pct)
    if not bill_within_cap(pre_auth_amount, buffer_pct, final_bill):
        raise BusinessRuleError(
            "BILL_EXCEEDS_CAP",
            f"final bill exceeds pre_auth_amount + {buffer_pct}% buffer",
            {"cap": money_str(cap), "final_bill": money_str(final_bill)},
        )
    return cap
