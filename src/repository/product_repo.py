"""Policy products and their append-only coverage-rule versions (NA-R2 .. NA-R4)."""

from __future__ import annotations

import json
import sqlite3

from src.domain.coverage_rules import CoverageRule, CoverageRuleVersion
from src.domain.money import money_str, to_money, to_percent


def list_products(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT p.*, (SELECT MAX(version) FROM coverage_rule_versions r WHERE r.product_id = p.id) "
            "AS current_version FROM policy_products p ORDER BY p.code"
        )
    )


def find_product(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute("SELECT * FROM policy_products WHERE code = ?", (code,)).fetchone()
    return row


def insert_product(
    conn: sqlite3.Connection, *, code: str, name: str, sum_insured: str, annual_premium: str, created_at: str
) -> int:
    cur = conn.execute(
        "INSERT INTO policy_products (code, name, sum_insured, annual_premium, created_at) VALUES (?, ?, ?, ?, ?)",
        (code, name, sum_insured, annual_premium, created_at),
    )
    return int(cur.lastrowid or 0)


def _to_version(row: sqlite3.Row, product_code: str) -> CoverageRuleVersion:
    rule = CoverageRule(
        auto_approve_threshold=to_money(row["auto_approve_threshold"]),
        auto_approved_diagnoses=tuple(json.loads(row["auto_approved_diagnoses"])),
        excluded_diagnoses=tuple(json.loads(row["excluded_diagnoses"])),
        per_claim_cap=to_money(row["per_claim_cap"]),
        buffer_pct=to_percent(row["buffer_pct"]),
        deductible=to_money(row["deductible"]),
        copay_pct=to_percent(row["copay_pct"]),
        reason_codes=tuple(json.loads(row["reason_codes"])),
    )
    return CoverageRuleVersion(product_code, int(row["version"]), rule, row["published_by"], row["published_at"])


def list_versions(conn: sqlite3.Connection, product_id: int, product_code: str) -> list[CoverageRuleVersion]:
    rows = conn.execute(
        "SELECT * FROM coverage_rule_versions WHERE product_id = ? ORDER BY version", (product_id,)
    )
    return [_to_version(row, product_code) for row in rows]


def get_version(conn: sqlite3.Connection, product_id: int, product_code: str, version: int) -> CoverageRuleVersion:
    row = conn.execute(
        "SELECT * FROM coverage_rule_versions WHERE product_id = ? AND version = ?", (product_id, version)
    ).fetchone()
    if row is None:
        raise LookupError(f"coverage rule {product_code} v{version} not found")
    return _to_version(row, product_code)


def current_version(conn: sqlite3.Connection, product_id: int, product_code: str) -> CoverageRuleVersion | None:
    versions = list_versions(conn, product_id, product_code)
    return versions[-1] if versions else None


def insert_version(
    conn: sqlite3.Connection, *, product_id: int, version: int, rule: CoverageRule, published_by: str, published_at: str
) -> None:
    conn.execute(
        "INSERT INTO coverage_rule_versions (product_id, version, auto_approve_threshold, auto_approved_diagnoses, "
        "excluded_diagnoses, per_claim_cap, buffer_pct, deductible, copay_pct, reason_codes, published_by, "
        "published_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            product_id, version, money_str(rule.auto_approve_threshold), json.dumps(list(rule.auto_approved_diagnoses)),
            json.dumps(list(rule.excluded_diagnoses)), money_str(rule.per_claim_cap), str(rule.buffer_pct),
            money_str(rule.deductible), str(rule.copay_pct), json.dumps(list(rule.reason_codes)), published_by,
            published_at,
        ),
    )
