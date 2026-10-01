"""Policies and members (the insured persons on a policy)."""

from __future__ import annotations

import sqlite3

POLICY_SELECT = (
    "SELECT pol.*, p.code AS product_code, p.name AS product_name FROM policies pol "
    "JOIN policy_products p ON p.id = pol.product_id"
)


def find_policy(conn: sqlite3.Connection, policy_number: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(f"{POLICY_SELECT} WHERE pol.policy_number = ?", (policy_number,)).fetchone()
    return row


def find_policy_by_id(conn: sqlite3.Connection, policy_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute(f"{POLICY_SELECT} WHERE pol.id = ?", (policy_id,)).fetchone()
    return row


def find_member(conn: sqlite3.Connection, member_id: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute("SELECT * FROM members WHERE member_id = ?", (member_id,)).fetchone()
    return row


def members_of_customer(conn: sqlite3.Connection, customer_id: int) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM members WHERE customer_id = ? ORDER BY member_id", (customer_id,)))


def link_member(conn: sqlite3.Connection, member_row_id: int, customer_id: int) -> None:
    conn.execute("UPDATE members SET customer_id = ? WHERE id = ?", (customer_id, member_row_id))


def insert_policy(conn: sqlite3.Connection, **values: object) -> int:
    cur = conn.execute(
        "INSERT INTO policies (policy_number, product_id, status, cover_start, cover_end, sum_insured, "
        "annual_premium, prior_claims_paid, created_at) VALUES (:policy_number, :product_id, :status, "
        ":cover_start, :cover_end, :sum_insured, :annual_premium, :prior_claims_paid, :created_at)",
        values,
    )
    return int(cur.lastrowid or 0)


def insert_member(conn: sqlite3.Connection, **values: object) -> int:
    cur = conn.execute(
        "INSERT INTO members (member_id, policy_id, full_name, date_of_birth, relationship, customer_id) "
        "VALUES (:member_id, :policy_id, :full_name, :date_of_birth, :relationship, :customer_id)",
        values,
    )
    return int(cur.lastrowid or 0)

