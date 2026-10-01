"""SQLite connection factory and append-only migration runner with a checksum ledger (NFR-05)."""

from __future__ import annotations

import datetime as dt
import hashlib
import sqlite3
from pathlib import Path

from src.config.settings import PROJECT_ROOT

DEFAULT_MIGRATIONS = PROJECT_ROOT / "migrations"


class MigrationTamperedError(RuntimeError):
    """An already-applied migration file changed on disk (migrations are append-only)."""


def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with row access by name and foreign keys enforced."""
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _ensure_ledger(conn: sqlite3.Connection) -> dict[str, str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "filename TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )
    rows = conn.execute("SELECT filename, checksum FROM schema_migrations")
    return {row["filename"]: row["checksum"] for row in rows}


def apply_migrations(conn: sqlite3.Connection, folder: Path | None = None) -> list[str]:
    """Apply pending NNNN_*.sql files in order; verify checksums of applied ones. Returns applied names."""
    folder = folder or DEFAULT_MIGRATIONS
    applied = _ensure_ledger(conn)
    newly_applied: list[str] = []
    for path in sorted(folder.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        checksum = _checksum(path)
        if path.name in applied:
            if applied[path.name] != checksum:
                raise MigrationTamperedError(f"{path.name} was modified after being applied")
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (filename, checksum, applied_at) VALUES (?, ?, ?)",
            (path.name, checksum, dt.datetime.now(dt.UTC).isoformat(timespec="seconds")),
        )
        conn.commit()
        newly_applied.append(path.name)
    return newly_applied
