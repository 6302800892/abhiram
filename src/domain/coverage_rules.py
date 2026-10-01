"""Versioned coverage rules (NA-R3, NA-R5). A version is immutable once published."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.domain.exceptions import BusinessRuleError
from src.domain.icd_stub import is_known_diagnosis
from src.domain.money import ZERO, require_decimal

REQUIRED_REASON_CODES = frozenset(
    {
        "PA-SUBMITTED", "PA-MANUAL-REVIEW", "PA-AUTO-APPROVED", "PA-AUTO-CAPPED", "PA-REJECTED-EXCLUSION",
        "PA-QUERY-UNKNOWN-DIAGNOSIS", "PA-QUERY-ANSWERED", "PA-QUERY-DOCUMENTS", "PA-APPROVED-MANUAL",
        "PA-PARTIAL-MANUAL", "PA-REJECTED-MANUAL", "PA-OVERRIDE",
    }
)
MAX_BUFFER_PCT = Decimal("50")
MAX_COPAY_PCT = Decimal("100")


@dataclass(frozen=True)
class CoverageRule:
    auto_approve_threshold: Decimal
    auto_approved_diagnoses: tuple[str, ...]
    excluded_diagnoses: tuple[str, ...]
    per_claim_cap: Decimal
    buffer_pct: Decimal
    deductible: Decimal
    copay_pct: Decimal
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class CoverageRuleVersion:
    product_code: str
    version: int
    rule: CoverageRule
    published_by: str
    published_at: str


def _invalid(message: str) -> BusinessRuleError:
    return BusinessRuleError("INVALID_COVERAGE_RULE", message)


def _validate_amounts(rule: CoverageRule) -> None:
    require_decimal(rule.auto_approve_threshold, rule.per_claim_cap, rule.buffer_pct, rule.deductible, rule.copay_pct)
    if rule.auto_approve_threshold < ZERO:
        raise _invalid("auto_approve_threshold must be >= 0")
    if rule.per_claim_cap <= ZERO:
        raise _invalid("per_claim_cap must be > 0")
    if not ZERO <= rule.buffer_pct <= MAX_BUFFER_PCT:
        raise _invalid("buffer_pct must be within [0, 50]")
    if rule.deductible < ZERO:
        raise _invalid("deductible must be >= 0")
    if not ZERO <= rule.copay_pct <= MAX_COPAY_PCT:
        raise _invalid("copay_pct must be within [0, 100]")


def _validate_diagnoses(rule: CoverageRule) -> None:
    for code in (*rule.auto_approved_diagnoses, *rule.excluded_diagnoses):
        if not is_known_diagnosis(code):
            raise _invalid(f"diagnosis {code} is not in the ICD stub")
    overlap = set(rule.auto_approved_diagnoses) & set(rule.excluded_diagnoses)
    if overlap:
        raise _invalid(f"diagnoses cannot be both auto-approved and excluded: {sorted(overlap)}")


def validate_coverage_rule(rule: CoverageRule) -> None:
    """Raise BusinessRuleError unless the rule satisfies NA-R3 and NA-R5."""
    _validate_amounts(rule)
    _validate_diagnoses(rule)
    missing = REQUIRED_REASON_CODES - set(rule.reason_codes)
    if missing:
        raise BusinessRuleError("REASON_CATALOGUE_INCOMPLETE", f"reason catalogue lacks {sorted(missing)}")
