"""AC-02 eligibility decision (EL-R4/EL-R5). Pure: the service gathers facts, this decides."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal

from src.domain.enums import EligibilityStatus, PolicyStatus
from src.domain.money import ZERO

ELG_OK = "ELG-OK"
ELG_POLICY_NOT_FOUND = "ELG-POLICY-NOT-FOUND"
ELG_MEMBER_NOT_COVERED = "ELG-MEMBER-NOT-COVERED"
ELG_POLICY_INACTIVE = "ELG-POLICY-INACTIVE"
ELG_OUTSIDE_COVER_PERIOD = "ELG-OUTSIDE-COVER-PERIOD"
ELG_SUM_INSURED_EXHAUSTED = "ELG-SUM-INSURED-EXHAUSTED"
ELG_HOSPITAL_NOT_NETWORK = "ELG-HOSPITAL-NOT-NETWORK"


@dataclass(frozen=True)
class PolicySnapshot:
    status: PolicyStatus
    cover_start: dt.date
    cover_end: dt.date


@dataclass(frozen=True)
class EligibilityInput:
    policy: PolicySnapshot | None
    member_on_policy: bool
    remaining_sum_insured: Decimal
    hospital_in_network: bool
    today: dt.date


@dataclass(frozen=True)
class EligibilityResult:
    status: EligibilityStatus
    reason_codes: tuple[str, ...]

    @property
    def eligible(self) -> bool:
        return self.status is EligibilityStatus.ELIGIBLE


def _not_eligible(*codes: str) -> EligibilityResult:
    return EligibilityResult(EligibilityStatus.NOT_ELIGIBLE, codes)


def resolve_eligibility(inp: EligibilityInput) -> EligibilityResult:
    """Evaluate the EL-R4 checks in order; the first two short-circuit, the rest accumulate."""
    if inp.policy is None:
        return _not_eligible(ELG_POLICY_NOT_FOUND)
    if not inp.member_on_policy:
        return _not_eligible(ELG_MEMBER_NOT_COVERED)
    reasons: list[str] = []
    if inp.policy.status is not PolicyStatus.ACTIVE:
        reasons.append(ELG_POLICY_INACTIVE)
    if not inp.policy.cover_start <= inp.today <= inp.policy.cover_end:
        reasons.append(ELG_OUTSIDE_COVER_PERIOD)
    if inp.remaining_sum_insured <= ZERO:
        reasons.append(ELG_SUM_INSURED_EXHAUSTED)
    if not inp.hospital_in_network:
        reasons.append(ELG_HOSPITAL_NOT_NETWORK)
    if reasons:
        return _not_eligible(*reasons)
    return EligibilityResult(EligibilityStatus.ELIGIBLE, (ELG_OK,))
