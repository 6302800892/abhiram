"""Policy coverage facts shared by eligibility, pre-auth and settlement (remaining sum insured)."""

from __future__ import annotations

import datetime as dt
import sqlite3
from decimal import Decimal

from src.domain.coverage_rules import CoverageRuleVersion
from src.domain.eligibility_rules import PolicySnapshot
from src.domain.enums import PolicyStatus
from src.domain.exceptions import NotFoundError
from src.domain.icd_stub import diagnosis_label
from src.domain.money import money_str, to_money
from src.repository import policy_repo, product_repo, settlement_repo


def remaining_sum_insured(conn: sqlite3.Connection, policy: sqlite3.Row) -> Decimal:
    """sum_insured − prior_claims_paid − Σ settled amounts on this policy (ST-R7)."""
    used = to_money(policy["prior_claims_paid"])
    for amount in settlement_repo.amounts_for_policy(conn, policy["id"]):
        used += to_money(amount)
    return to_money(policy["sum_insured"]) - used


def snapshot(policy: sqlite3.Row) -> PolicySnapshot:
    return PolicySnapshot(
        status=PolicyStatus(policy["status"]),
        cover_start=dt.date.fromisoformat(policy["cover_start"]),
        cover_end=dt.date.fromisoformat(policy["cover_end"]),
    )


def current_rule(conn: sqlite3.Connection, policy: sqlite3.Row) -> CoverageRuleVersion:
    version = product_repo.current_version(conn, policy["product_id"], policy["product_code"])
    if version is None:
        raise NotFoundError("NO_COVERAGE_RULE", f"product {policy['product_code']} has no published coverage rule")
    return version


def coverage_view(conn: sqlite3.Connection, member: sqlite3.Row) -> dict[str, object]:
    """EL-R3 coverage item for one linked member."""
    policy = policy_repo.find_policy_by_id(conn, member["policy_id"])
    if policy is None:
        raise NotFoundError("POLICY_NOT_FOUND", "policy not found")
    rule = current_rule(conn, policy).rule
    return {
        "policy_number": policy["policy_number"],
        "product_code": policy["product_code"],
        "product_name": policy["product_name"],
        "status": policy["status"],
        "cover_start": policy["cover_start"],
        "cover_end": policy["cover_end"],
        "sum_insured": money_str(to_money(policy["sum_insured"])),
        "remaining_sum_insured": money_str(remaining_sum_insured(conn, policy)),
        "member_id": member["member_id"],
        "member_name": member["full_name"],
        "exclusions": [{"code": c, "label": diagnosis_label(c)} for c in rule.excluded_diagnoses],
    }
