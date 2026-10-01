"""Network & coverage admin (NA-R1 .. NA-R5). Coverage rules are published as new versions only."""

from __future__ import annotations

import logging
import re
import sqlite3

from src.domain.clock import Clock, iso
from src.domain.coverage_rules import CoverageRule, CoverageRuleVersion, validate_coverage_rule
from src.domain.exceptions import ConflictError, NotFoundError, ValidationError
from src.domain.money import ZERO, money_str, to_money
from src.domain.principal import Principal
from src.repository import hospital_repo, product_repo

logger = logging.getLogger("medicard.admin")
HOSPITAL_CODE_RE = re.compile(r"^[A-Z0-9]{3,12}$")


def hospital_view(row: sqlite3.Row) -> dict[str, object]:
    return {"code": row["code"], "name": row["name"], "city": row["city"], "in_network": bool(row["in_network"])}


def list_hospitals(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [hospital_view(h) for h in hospital_repo.list_all(conn)]


def network_hospitals(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [hospital_view(h) for h in hospital_repo.list_all(conn, in_network_only=True)]


def create_hospital(
    conn: sqlite3.Connection, *, code: str, name: str, city: str, in_network: bool, clock: Clock
) -> dict[str, object]:
    if not HOSPITAL_CODE_RE.match(code):
        raise ValidationError("INVALID_HOSPITAL_CODE", "code must be 3-12 uppercase letters or digits")
    if hospital_repo.find_by_code(conn, code) is not None:
        raise ConflictError("HOSPITAL_EXISTS", f"hospital {code} already exists")
    with conn:
        hospital_repo.insert(conn, code=code, name=name, city=city, in_network=in_network, created_at=iso(clock.now()))
    logger.info("hospital.created", extra={"hospital": code, "in_network": in_network})
    row = hospital_repo.find_by_code(conn, code)
    assert row is not None
    return hospital_view(row)


def set_network_status(conn: sqlite3.Connection, code: str, in_network: bool) -> dict[str, object]:
    if hospital_repo.find_by_code(conn, code) is None:
        raise NotFoundError("HOSPITAL_NOT_FOUND", f"hospital {code} not found")
    with conn:
        hospital_repo.set_in_network(conn, code, in_network)
    logger.info("hospital.network_changed", extra={"hospital": code, "in_network": in_network})
    row = hospital_repo.find_by_code(conn, code)
    assert row is not None
    return hospital_view(row)


def product_view(row: sqlite3.Row) -> dict[str, object]:
    return {
        "code": row["code"], "name": row["name"], "sum_insured": row["sum_insured"],
        "annual_premium": row["annual_premium"], "current_version": row["current_version"],
    }


def list_products(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [product_view(p) for p in product_repo.list_products(conn)]


def create_product(
    conn: sqlite3.Connection, *, code: str, name: str, sum_insured: str, annual_premium: str, clock: Clock
) -> dict[str, object]:
    if product_repo.find_product(conn, code) is not None:
        raise ConflictError("PRODUCT_EXISTS", f"product {code} already exists")
    si, premium = to_money(sum_insured), to_money(annual_premium)
    if si <= ZERO or premium <= ZERO:
        raise ValidationError("INVALID_PRODUCT", "sum_insured and annual_premium must be > 0")
    with conn:
        product_repo.insert_product(conn, code=code, name=name, sum_insured=money_str(si),
                                    annual_premium=money_str(premium), created_at=iso(clock.now()))
    return next(p for p in list_products(conn) if p["code"] == code)


def _product_or_404(conn: sqlite3.Connection, code: str) -> sqlite3.Row:
    product = product_repo.find_product(conn, code)
    if product is None:
        raise NotFoundError("PRODUCT_NOT_FOUND", f"product {code} not found")
    return product


def list_rule_versions(conn: sqlite3.Connection, code: str) -> list[CoverageRuleVersion]:
    product = _product_or_404(conn, code)
    return product_repo.list_versions(conn, product["id"], code)


def publish_rule(
    conn: sqlite3.Connection, principal: Principal, code: str, rule: CoverageRule, clock: Clock
) -> CoverageRuleVersion:
    """NA-R4: validate, then append version n+1. Earlier versions are never touched."""
    product = _product_or_404(conn, code)
    validate_coverage_rule(rule)
    versions = product_repo.list_versions(conn, product["id"], code)
    next_version = versions[-1].version + 1 if versions else 1
    with conn:
        product_repo.insert_version(conn, product_id=product["id"], version=next_version, rule=rule,
                                    published_by=principal.username, published_at=iso(clock.now()))
    logger.info("coverage_rule.published", extra={"product": code, "version": next_version})
    return product_repo.get_version(conn, product["id"], code, next_version)
