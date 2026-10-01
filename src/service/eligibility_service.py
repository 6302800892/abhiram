"""AC-02: gather facts for a member + policy + requesting hospital and apply the eligibility rule."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from decimal import Decimal

from src.domain.clock import Clock
from src.domain.eligibility_rules import EligibilityInput, EligibilityResult, resolve_eligibility
from src.domain.money import ZERO, money_str
from src.domain.principal import Principal
from src.repository import hospital_repo, policy_repo
from src.service import coverage_service

logger = logging.getLogger("medicard.eligibility")


@dataclass(frozen=True)
class EligibilityOutcome:
    result: EligibilityResult
    policy: sqlite3.Row | None
    member: sqlite3.Row | None
    remaining_sum_insured: Decimal | None


def evaluate(
    conn: sqlite3.Connection, *, member_id: str, policy_number: str, hospital_id: int | None, clock: Clock
) -> EligibilityOutcome:
    """Build EligibilityInput from the DB. The hospital always comes from the principal (EL-R6)."""
    policy = policy_repo.find_policy(conn, policy_number)
    member = policy_repo.find_member(conn, member_id)
    hospital = hospital_repo.find_by_id(conn, hospital_id) if hospital_id is not None else None
    remaining = coverage_service.remaining_sum_insured(conn, policy) if policy is not None else None
    result = resolve_eligibility(
        EligibilityInput(
            policy=coverage_service.snapshot(policy) if policy is not None else None,
            member_on_policy=bool(policy is not None and member is not None and member["policy_id"] == policy["id"]),
            remaining_sum_insured=remaining if remaining is not None else ZERO,
            hospital_in_network=bool(hospital is not None and hospital["in_network"]),
            today=clock.today(),
        )
    )
    return EligibilityOutcome(result, policy, member, remaining)


def check(
    conn: sqlite3.Connection, principal: Principal, *, member_id: str, policy_number: str, clock: Clock
) -> dict[str, object]:
    outcome = evaluate(
        conn, member_id=member_id, policy_number=policy_number, hospital_id=principal.hospital_id, clock=clock
    )
    logger.info(
        "eligibility.checked",
        extra={"hospital": principal.hospital_code, "status": outcome.result.status.value,
               "reason_codes": list(outcome.result.reason_codes)},
    )
    member_covered = (
        outcome.policy is not None and outcome.member is not None
        and outcome.member["policy_id"] == outcome.policy["id"]
    )
    remaining = outcome.remaining_sum_insured if member_covered else None  # EL-R7: no leak
    return {
        "status": outcome.result.status.value,
        "reason_codes": list(outcome.result.reason_codes),
        "policy_number": policy_number,
        "member_id": member_id,
        "remaining_sum_insured": money_str(remaining) if remaining is not None else None,
    }
