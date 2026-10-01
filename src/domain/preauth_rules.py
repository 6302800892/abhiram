"""Pre-auth engine rules: auto-decider (AC-05, PA-R4) and manual decision validation (AD-R3, AD-R4)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from src.domain.coverage_rules import CoverageRule
from src.domain.enums import PreAuthStatus
from src.domain.exceptions import BusinessRuleError
from src.domain.icd_stub import is_known_diagnosis
from src.domain.money import ZERO, require_decimal

PA_SUBMITTED = "PA-SUBMITTED"
PA_MANUAL_REVIEW = "PA-MANUAL-REVIEW"
PA_AUTO_APPROVED = "PA-AUTO-APPROVED"
PA_AUTO_CAPPED = "PA-AUTO-CAPPED"
PA_REJECTED_EXCLUSION = "PA-REJECTED-EXCLUSION"
PA_QUERY_UNKNOWN_DIAGNOSIS = "PA-QUERY-UNKNOWN-DIAGNOSIS"
PA_QUERY_ANSWERED = "PA-QUERY-ANSWERED"
PA_OVERRIDE = "PA-OVERRIDE"


@dataclass(frozen=True)
class AutoDecision:
    status: PreAuthStatus
    approved_amount: Decimal | None
    reason_code: str


def policy_cap(rule: CoverageRule, remaining_sum_insured: Decimal) -> Decimal:
    """BRD D-1: the cap is min(per_claim_cap, remaining_sum_insured), never below zero."""
    require_decimal(rule.per_claim_cap, remaining_sum_insured)
    return max(ZERO, min(rule.per_claim_cap, remaining_sum_insured))


def decide_auto(estimate: Decimal, diagnosis: str, rule: CoverageRule, remaining_sum_insured: Decimal) -> AutoDecision:
    """PA-R4, in order: unknown diagnosis -> exclusion -> threshold + auto list (capped) -> manual review."""
    require_decimal(estimate, rule.auto_approve_threshold)
    if not is_known_diagnosis(diagnosis):
        return AutoDecision(PreAuthStatus.QUERY_RAISED, None, PA_QUERY_UNKNOWN_DIAGNOSIS)
    if diagnosis in rule.excluded_diagnoses:
        return AutoDecision(PreAuthStatus.REJECTED, None, PA_REJECTED_EXCLUSION)
    if estimate <= rule.auto_approve_threshold and diagnosis in rule.auto_approved_diagnoses:
        cap = policy_cap(rule, remaining_sum_insured)
        if estimate <= cap:
            return AutoDecision(PreAuthStatus.APPROVED, estimate, PA_AUTO_APPROVED)
        return AutoDecision(PreAuthStatus.PARTIALLY_APPROVED, cap, PA_AUTO_CAPPED)
    return AutoDecision(PreAuthStatus.PENDING, None, PA_MANUAL_REVIEW)


def _bad_amount(message: str) -> BusinessRuleError:
    return BusinessRuleError("INVALID_APPROVED_AMOUNT", message)


def validate_decision_amount(
    status: PreAuthStatus, amount: Decimal | None, estimate: Decimal, cap: Decimal
) -> Decimal | None:
    """AD-R3: return the amount to record for a manual decision or raise INVALID_APPROVED_AMOUNT."""
    if status is PreAuthStatus.APPROVED:
        if amount is not None and amount != estimate:
            raise _bad_amount("APPROVED must approve the full estimated cost; use PARTIALLY_APPROVED otherwise")
        if estimate > cap:
            raise _bad_amount(f"estimate exceeds the policy cap {cap}; approve partially up to the cap")
        return estimate
    if status is PreAuthStatus.PARTIALLY_APPROVED:
        if amount is None or not ZERO < amount < estimate:
            raise _bad_amount("PARTIALLY_APPROVED needs 0 < approved_amount < estimated_cost")
        if amount > cap:
            raise _bad_amount(f"approved_amount exceeds the policy cap {cap}")
        return amount
    if amount is not None:
        raise _bad_amount(f"{status.value} decisions carry no approved_amount")
    return None


def ensure_reason_codes(codes: Iterable[str], catalogue: Iterable[str]) -> list[str]:
    """AD-R4 / PA-R6: at least one code, every code from the pre-auth's rule-version catalogue."""
    selected = list(dict.fromkeys(codes))
    if not selected:
        raise BusinessRuleError("REASON_CODE_REQUIRED", "at least one reason code is required")
    unknown = [c for c in selected if c not in set(catalogue)]
    if unknown:
        raise BusinessRuleError("UNKNOWN_REASON_CODE", f"reason codes not in the rule version catalogue: {unknown}")
    return selected
