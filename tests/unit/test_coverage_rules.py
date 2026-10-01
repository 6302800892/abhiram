"""NA-R3 / NA-R5 coverage-rule version validation."""

from decimal import Decimal

import pytest

from src.domain.coverage_rules import REQUIRED_REASON_CODES, CoverageRule, validate_coverage_rule
from src.domain.exceptions import BusinessRuleError


def _rule(**overrides: object) -> CoverageRule:
    base: dict[str, object] = {
        "auto_approve_threshold": Decimal("50000.00"),
        "auto_approved_diagnoses": ("K35.8", "J18.9"),
        "excluded_diagnoses": ("Z41.1",),
        "per_claim_cap": Decimal("200000.00"),
        "buffer_pct": Decimal("10"),
        "deductible": Decimal("5000.00"),
        "copay_pct": Decimal("10"),
        "reason_codes": tuple(sorted(REQUIRED_REASON_CODES)),
    }
    base.update(overrides)
    return CoverageRule(**base)  # type: ignore[arg-type]


def test_valid_rule_passes() -> None:
    validate_coverage_rule(_rule())


def test_overlapping_auto_and_excluded_lists_rejected() -> None:
    with pytest.raises(BusinessRuleError) as err:
        validate_coverage_rule(_rule(excluded_diagnoses=("K35.8",)))
    assert err.value.code == "INVALID_COVERAGE_RULE"


def test_unknown_icd_code_rejected() -> None:
    with pytest.raises(BusinessRuleError):
        validate_coverage_rule(_rule(auto_approved_diagnoses=("ZZZ.9",)))


@pytest.mark.parametrize("buffer_pct", ["-1", "50.01"])
def test_buffer_pct_bounds(buffer_pct: str) -> None:
    with pytest.raises(BusinessRuleError):
        validate_coverage_rule(_rule(buffer_pct=Decimal(buffer_pct)))


def test_copay_pct_above_100_rejected() -> None:
    with pytest.raises(BusinessRuleError):
        validate_coverage_rule(_rule(copay_pct=Decimal("100.01")))


def test_incomplete_reason_catalogue_rejected() -> None:
    with pytest.raises(BusinessRuleError) as err:
        validate_coverage_rule(_rule(reason_codes=("PA-SUBMITTED",)))
    assert err.value.code == "REASON_CATALOGUE_INCOMPLETE"


def test_non_positive_cap_rejected() -> None:
    with pytest.raises(BusinessRuleError):
        validate_coverage_rule(_rule(per_claim_cap=Decimal("0.00")))
