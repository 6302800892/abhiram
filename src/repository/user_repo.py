"""Users and customer profiles."""

from __future__ import annotations

import sqlite3


def find_by_username(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return row


def find_principal_row(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    """User joined with its hospital code and customer id (for Principal construction)."""
    row: sqlite3.Row | None = conn.execute(
        "SELECT u.*, h.code AS hospital_code, c.id AS customer_id FROM users u "
        "LEFT JOIN hospitals h ON h.id = u.hospital_id LEFT JOIN customers c ON c.user_id = u.id WHERE u.id = ?",
        (user_id,),
    ).fetchone()
    return row


def insert_user(
    conn: sqlite3.Connection,
    *,
    username: str,
    password_hash: str,
    role: str,
    display_name: str,
    created_at: str,
    hospital_id: int | None = None,
) -> int:
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, role, display_name, hospital_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (username, password_hash, role, display_name, hospital_id, created_at),
    )
    return int(cur.lastrowid or 0)


def insert_customer(conn: sqlite3.Connection, *, user_id: int, full_name: str, created_at: str) -> int:
    cur = conn.execute(
        "INSERT INTO customers (user_id, full_name, created_at) VALUES (?, ?, ?)", (user_id, full_name, created_at)
    )
    return int(cur.lastrowid or 0)


def count_users(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM users").fetchone()[0])
