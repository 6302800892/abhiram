"""Load synthetic seed data (policies, network hospitals, sample customers) into an empty database."""

from __future__ import annotations

import datetime as dt
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from src.domain.clock import Clock, iso
from src.domain.coverage_rules import REQUIRED_REASON_CODES, CoverageRule
from src.domain.money import to_money, to_percent
from src.repository import hospital_repo, policy_repo, product_repo, user_repo
from src.service.auth_service import hash_password

logger = logging.getLogger("medicard.seed")


def _rule(raw: dict[str, Any]) -> CoverageRule:
    return CoverageRule(
        auto_approve_threshold=to_money(raw["auto_approve_threshold"]),
        auto_approved_diagnoses=tuple(raw["auto_approved_diagnoses"]),
        excluded_diagnoses=tuple(raw["excluded_diagnoses"]),
        per_claim_cap=to_money(raw["per_claim_cap"]),
        buffer_pct=to_percent(raw["buffer_pct"]),
        deductible=to_money(raw["deductible"]),
        copay_pct=to_percent(raw["copay_pct"]),
        reason_codes=tuple(sorted(REQUIRED_REASON_CODES)),
    )


def _seed_products(conn: sqlite3.Connection, products: list[dict[str, Any]], now: str) -> dict[str, int]:
    ids: dict[str, int] = {}
    for p in products:
        ids[p["code"]] = product_repo.insert_product(
            conn, code=p["code"], name=p["name"], sum_insured=p["sum_insured"],
            annual_premium=p["annual_premium"], created_at=now,
        )
        product_repo.insert_version(conn, product_id=ids[p["code"]], version=1, rule=_rule(p["rule"]),
                                    published_by="seed", published_at=now)
    return ids


def _seed_users(conn: sqlite3.Connection, data: dict[str, Any], iterations: int, now: str) -> dict[str, int]:
    password_hash = hash_password(data["demo_password"], iterations=iterations)
    customers: dict[str, int] = {}
    for u in data["users"]:
        hospital = hospital_repo.find_by_code(conn, u["hospital"]) if "hospital" in u else None
        user_id = user_repo.insert_user(
            conn, username=u["username"], password_hash=password_hash, role=u["role"],
            display_name=u["display_name"], created_at=now, hospital_id=hospital["id"] if hospital else None,
        )
        if u["role"] == "CUSTOMER":
            customers[u["username"]] = user_repo.insert_customer(
                conn, user_id=user_id, full_name=u["display_name"], created_at=now
            )
    return customers


def _seed_policies(
    conn: sqlite3.Connection, data: dict[str, Any], products: dict[str, int], customers: dict[str, int],
    today: dt.date, now: str,
) -> None:
    sums = {p["code"]: (p["sum_insured"], p["annual_premium"]) for p in data["products"]}
    for pol in data["policies"]:
        sum_insured, premium = sums[pol["product"]]
        policy_id = policy_repo.insert_policy(
            conn, policy_number=pol["policy_number"], product_id=products[pol["product"]], status=pol["status"],
            cover_start=(today + dt.timedelta(days=pol["cover_start_offset_days"])).isoformat(),
            cover_end=(today + dt.timedelta(days=pol["cover_end_offset_days"])).isoformat(),
            sum_insured=sum_insured, annual_premium=premium, prior_claims_paid=pol["prior_claims_paid"], created_at=now,
        )
        for m in pol["members"]:
            policy_repo.insert_member(
                conn, member_id=m["member_id"], policy_id=policy_id, full_name=m["full_name"],
                date_of_birth=m["date_of_birth"], relationship=m["relationship"],
                customer_id=customers.get(m.get("customer", "")),
            )


def seed_if_empty(conn: sqlite3.Connection, seed_file: str, *, clock: Clock, iterations: int) -> bool:
    """Insert the seed dataset once. Returns True when data was loaded."""
    if user_repo.count_users(conn) > 0:
        return False
    data = json.loads(Path(seed_file).read_text(encoding="utf-8"))
    now = iso(clock.now())
    with conn:
        for h in data["hospitals"]:
            hospital_repo.insert(conn, code=h["code"], name=h["name"], city=h["city"],
                                 in_network=h["in_network"], created_at=now)
        products = _seed_products(conn, data["products"], now)
        customers = _seed_users(conn, data, iterations, now)
        _seed_policies(conn, data, products, customers, clock.today(), now)
    logger.info("seed.loaded", extra={"hospitals": len(data["hospitals"]), "policies": len(data["policies"])})
    return True
