"""Read-only aggregation queries over the append-only tables (reports_spec)."""

from __future__ import annotations

import sqlite3


def first_decisions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Per pre-auth: submission time and the first non-PENDING decision time (if any)."""
    return list(
        conn.execute(
            "SELECT p.id, p.submitted_at, (SELECT MIN(d.decided_at) FROM preauth_decisions d "
            "WHERE d.preauth_id = p.id AND d.status <> 'PENDING') AS first_decided_at FROM preauths p"
        )
    )


def settlement_amounts(conn: sqlite3.Connection) -> list[str]:
    return [row[0] for row in conn.execute("SELECT settlement_amount FROM settlements")]


def query_counts_by_hospital(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT h.code AS hospital_code, COUNT(p.id) AS preauths, "
            "SUM(CASE WHEN EXISTS (SELECT 1 FROM preauth_decisions d WHERE d.preauth_id = p.id "
            "AND d.status = 'QUERY_RAISED') THEN 1 ELSE 0 END) AS queried "
            "FROM preauths p JOIN claim_cases c ON c.id = p.case_id JOIN hospitals h ON h.id = c.hospital_id "
            "GROUP BY h.code ORDER BY h.code"
        )
    )


def diagnosis_counts(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT diagnosis_code, COUNT(*) AS n FROM preauths GROUP BY diagnosis_code"))


def premiums_by_product(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT pr.code AS product_code, pol.annual_premium AS premium FROM policies pol "
            "JOIN policy_products pr ON pr.id = pol.product_id"
        )
    )


def settled_by_product(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            "SELECT pr.code AS product_code, s.settlement_amount AS amount FROM settlements s "
            "JOIN claim_cases c ON c.id = s.case_id JOIN policies pol ON pol.id = c.policy_id "
            "JOIN policy_products pr ON pr.id = pol.product_id"
        )
    )
