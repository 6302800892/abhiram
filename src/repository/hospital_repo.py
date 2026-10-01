"""Network hospitals (NA-R1). Hospitals are never deleted; only in_network may change."""

from __future__ import annotations

import sqlite3


def list_all(conn: sqlite3.Connection, *, in_network_only: bool = False) -> list[sqlite3.Row]:
    sql = "SELECT * FROM hospitals"
    if in_network_only:
        sql += " WHERE in_network = 1"
    return list(conn.execute(sql + " ORDER BY code"))


def find_by_code(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute("SELECT * FROM hospitals WHERE code = ?", (code,)).fetchone()
    return row


def find_by_id(conn: sqlite3.Connection, hospital_id: int) -> sqlite3.Row | None:
    row: sqlite3.Row | None = conn.execute("SELECT * FROM hospitals WHERE id = ?", (hospital_id,)).fetchone()
    return row


def insert(conn: sqlite3.Connection, *, code: str, name: str, city: str, in_network: bool, created_at: str) -> int:
    cur = conn.execute(
        "INSERT INTO hospitals (code, name, city, in_network, created_at) VALUES (?, ?, ?, ?, ?)",
        (code, name, city, int(in_network), created_at),
    )
    return int(cur.lastrowid or 0)


def set_in_network(conn: sqlite3.Connection, code: str, in_network: bool) -> None:
    conn.execute("UPDATE hospitals SET in_network = ? WHERE code = ?", (int(in_network), code))
