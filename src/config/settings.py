"""Runtime settings, read from MEDICARD_* environment variables. No secrets are hardcoded."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in {"1", "true", "yes"}


@dataclass(frozen=True)
class Settings:
    db_path: str = str(PROJECT_ROOT / "data" / "medicard.db")
    # A per-process random secret when MEDICARD_SECRET is unset: tokens simply expire on restart.
    secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    token_ttl_hours: int = 12
    pbkdf2_iterations: int = 200_000
    seed_on_startup: bool = True
    seed_file: str = str(PROJECT_ROOT / "seed" / "seed_data.json")
    migrations_dir: str = str(PROJECT_ROOT / "migrations")
    frontend_dist: str | None = str(PROJECT_ROOT / "frontend" / "dist")
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        base = cls()
        return cls(
            db_path=os.environ.get("MEDICARD_DB_PATH", base.db_path),
            secret=os.environ.get("MEDICARD_SECRET", base.secret),
            token_ttl_hours=int(os.environ.get("MEDICARD_TOKEN_TTL_HOURS", base.token_ttl_hours)),
            pbkdf2_iterations=int(os.environ.get("MEDICARD_PBKDF2_ITERATIONS", base.pbkdf2_iterations)),
            seed_on_startup=_env_bool("MEDICARD_SEED", base.seed_on_startup),
            frontend_dist=os.environ.get("MEDICARD_FRONTEND_DIST", base.frontend_dist),
            host=os.environ.get("MEDICARD_HOST", base.host),
            port=int(os.environ.get("MEDICARD_PORT", base.port)),
            log_level=os.environ.get("MEDICARD_LOG_LEVEL", base.log_level),
        )
