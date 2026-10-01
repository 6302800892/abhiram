"""AC-05 auto-decider and AD-R3/AD-R4 decision validation (pre-auth-auto-decider skill vectors)."""

from decimal import Decimal

import pytest

from src.domain.coverage_rules import REQUIRED_REASON_CODES, CoverageRule
from src.domain.enums import PreAuthStatus
from src.domain.exceptions import BusinessRuleError
from src.domain.preauth_rules import decide_auto, ensure_reason_codes, policy_cap, validate_decision_amount

RULE = CoverageRule(
    auto_approve_threshold=Decimal("50000.00"),
    auto_approved_diagnoses=("K35.8", "J18.9"),
    excluded_diagnoses=("Z41.1",),
    per_claim_cap=Decimal("500000.00"),
    buffer_pct=Decimal("10"),
    deductible=Decimal("5000.00"),
    copay_pct=Decimal("10"),
    reason_codes=tuple(sorted(REQUIRED_REASON_CODES)),
)
PLENTY = Decimal("1000000.00")


@pytest.mark.ac("AC-05")
@pytest.mark.parametrize(
    ("estimate", "diagnosis", "remaining", "status", "amount", "reason"),
    [
        ("40000.00", "K35.8", PLENTY, PreAuthStatus.APPROVED, "40000.00", "PA-AUTO-APPROVED"),
        ("50000.00", "K35.8", PLENTY, PreAuthStatus.APPROVED, "50000.00", "PA-AUTO-APPROVED"),
        ("50000.01", "K35.8", PLENTY, PreAuthStatus.PENDING, None, "PA-MANUAL-REVIEW"),
        ("30000.00", "I21.9", PLENTY, PreAuthStatus.PENDING, None, "PA-MANUAL-REVIEW"),
        ("30000.00", "Z41.1", PLENTY, PreAuthStatus.REJECTED, None, "PA-REJECTED-EXCLUSION"),
        ("30000.00", "ZZZ.9", PLENTY, PreAuthStatus.QUERY_RAISED, None, "PA-QUERY-UNKNOWN-DIAGNOSIS"),
        ("30000.00", "K35.8", Decimal("20000.00"), PreAuthStatus.PARTIALLY_APPROVED, "20000.00", "PA-AUTO-CAPPED"),
    ],
)
def test_ac05_auto_decider_vectors(
    estimate: str, diagnosis: str, remaining: Decimal, status: PreAuthStatus, amount: str | None, reason: str
) -> None:
    decision = decide_auto(Decimal(estimate), diagnosis, RULE, remaining)
    assert decision.status is status
    assert decision.approved_amount == (Decimal(amount) if amount else None)
    assert decision.reason_code == reason


@pytest.mark.ac("AC-05")
def test_ac05_policy_cap_is_min_of_per_claim_cap_and_remaining() -> None:
    assert policy_cap(RULE, Decimal("20000.00")) == Decimal("20000.00")
    assert policy_cap(RULE, PLENTY) == Decimal("500000.00")


@pytest.mark.ac("AC-05")
def test_ac05_unknown_diagnosis_checked_before_exclusion() -> None:
    assert decide_auto(Decimal("1.00"), "ZZZ.9", RULE, PLENTY).status is PreAuthStatus.QUERY_RAISED


@pytest.mark.ac("AC-04")
def test_ac04_approved_amount_must_equal_estimate() -> None:
    est, cap = Decimal("80000.00"), Decimal("500000.00")
    assert validate_decision_amount(PreAuthStatus.APPROVED, None, est, cap) == est
    with pytest.raises(BusinessRuleError):
        validate_decision_amount(PreAuthStatus.APPROVED, Decimal("70000.00"), est, cap)


@pytest.mark.ac("AC-04")
def test_ac04_partial_amount_bounds() -> None:
    est, cap = Decimal("80000.00"), Decimal("50000.00")
    assert validate_decision_amount(PreAuthStatus.PARTIALLY_APPROVED, Decimal("30000.00"), est, cap) == Decimal(
        "30000.00"
    )
    for bad in ("0.00", "80000.00", "60000.00"):
        with pytest.raises(BusinessRuleError) as err:
            validate_decision_amount(PreAuthStatus.PARTIALLY_APPROVED, Decimal(bad), est, cap)
        assert err.value.code == "INVALID_APPROVED_AMOUNT"


@pytest.mark.ac("AC-04")
def test_ac04_approved_over_cap_rejected() -> None:
    with pytest.raises(BusinessRuleError):
        validate_decision_amount(PreAuthStatus.APPROVED, None, Decimal("90000.00"), Decimal("50000.00"))


@pytest.mark.ac("AC-04")
def test_ac04_reject_and_query_carry_no_amount() -> None:
    assert validate_decision_amount(PreAuthStatus.REJECTED, None, Decimal("1.00"), Decimal("9.00")) is None
    with pytest.raises(BusinessRuleError):
        validate_decision_amount(PreAuthStatus.QUERY_RAISED, Decimal("1.00"), Decimal("1.00"), Decimal("9.00"))


@pytest.mark.ac("AC-04")
def test_ac04_reason_codes_must_be_in_catalogue() -> None:
    ensure_reason_codes(["PA-APPROVED-MANUAL"], RULE.reason_codes)
    with pytest.raises(BusinessRuleError) as err:
        ensure_reason_codes(["PA-MADE-UP"], RULE.reason_codes)
    assert err.value.code == "UNKNOWN_REASON_CODE"
    with pytest.raises(BusinessRuleError):
        ensure_reason_codes([], RULE.reason_codes)
