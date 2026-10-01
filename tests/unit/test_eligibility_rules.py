"""AC-02 eligibility decision table (EL-R4, EL-R5) — pure domain rule."""

import datetime as dt
from decimal import Decimal

import pytest

from src.domain.eligibility_rules import EligibilityInput, PolicySnapshot, resolve_eligibility
from src.domain.enums import EligibilityStatus, PolicyStatus

TODAY = dt.date(2026, 6, 15)
ACTIVE = PolicySnapshot(status=PolicyStatus.ACTIVE, cover_start=dt.date(2026, 1, 1), cover_end=dt.date(2026, 12, 31))


def _input(**overrides: object) -> EligibilityInput:
    base: dict[str, object] = {
        "policy": ACTIVE,
        "member_on_policy": True,
        "remaining_sum_insured": Decimal("100000.00"),
        "hospital_in_network": True,
        "today": TODAY,
    }
    base.update(overrides)
    return EligibilityInput(**base)  # type: ignore[arg-type]


@pytest.mark.ac("AC-02")
def test_ac02_eligible_member_returns_elg_ok() -> None:
    result = resolve_eligibility(_input())
    assert result.status is EligibilityStatus.ELIGIBLE
    assert result.reason_codes == ("ELG-OK",)


@pytest.mark.ac("AC-02")
def test_ac02_unknown_policy_short_circuits() -> None:
    result = resolve_eligibility(_input(policy=None, member_on_policy=False, hospital_in_network=False))
    assert result.status is EligibilityStatus.NOT_ELIGIBLE
    assert result.reason_codes == ("ELG-POLICY-NOT-FOUND",)


@pytest.mark.ac("AC-02")
def test_ac02_member_not_on_policy_short_circuits() -> None:
    result = resolve_eligibility(_input(member_on_policy=False, hospital_in_network=False))
    assert result.reason_codes == ("ELG-MEMBER-NOT-COVERED",)


@pytest.mark.ac("AC-02")
def test_ac02_lapsed_and_expired_returns_both_codes_in_order() -> None:
    lapsed = PolicySnapshot(PolicyStatus.LAPSED, dt.date(2025, 1, 1), dt.date(2025, 12, 31))
    result = resolve_eligibility(_input(policy=lapsed))
    assert result.reason_codes == ("ELG-POLICY-INACTIVE", "ELG-OUTSIDE-COVER-PERIOD")


@pytest.mark.ac("AC-02")
@pytest.mark.parametrize("today", [dt.date(2026, 1, 1), dt.date(2026, 12, 31)])
def test_ac02_cover_period_is_inclusive_at_both_ends(today: dt.date) -> None:
    assert resolve_eligibility(_input(today=today)).status is EligibilityStatus.ELIGIBLE


@pytest.mark.ac("AC-02")
def test_ac02_zero_remaining_sum_insured_is_exhausted() -> None:
    result = resolve_eligibility(_input(remaining_sum_insured=Decimal("0.00")))
    assert result.reason_codes == ("ELG-SUM-INSURED-EXHAUSTED",)


@pytest.mark.ac("AC-02")
def test_ac02_collects_every_non_short_circuit_reason() -> None:
    lapsed = PolicySnapshot(PolicyStatus.LAPSED, dt.date(2025, 1, 1), dt.date(2025, 12, 31))
    result = resolve_eligibility(
        _input(policy=lapsed, remaining_sum_insured=Decimal("0.00"), hospital_in_network=False)
    )
    assert result.reason_codes == (
        "ELG-POLICY-INACTIVE",
        "ELG-OUTSIDE-COVER-PERIOD",
        "ELG-SUM-INSURED-EXHAUSTED",
        "ELG-HOSPITAL-NOT-NETWORK",
    )
