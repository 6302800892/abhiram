"""Shared fixtures: an isolated app per test (temp SQLite DB, pinned clock, fast hashing)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.domain.clock import FixedClock
from src.main import create_app

PINNED_NOW = dt.datetime(2026, 6, 15, 10, 0, tzinfo=dt.UTC)
DEMO_PASSWORD = "Demo@1234"  # synthetic seed credential (seed/seed_data.json)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(PINNED_NOW)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=str(tmp_path / "medicard-test.db"),
        secret="test-only-secret",
        pbkdf2_iterations=1_000,
        seed_on_startup=True,
        frontend_dist=None,
    )


@pytest.fixture
def client(settings: Settings, clock: FixedClock) -> Iterator[TestClient]:
    app = create_app(settings=settings, clock=clock)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Return a function username -> Authorization header for a seeded user."""
    cache: dict[str, dict[str, str]] = {}

    def _login(username: str, password: str = DEMO_PASSWORD) -> dict[str, str]:
        if username not in cache:
            resp = client.post("/api/auth/login", json={"username": username, "password": password})
            assert resp.status_code == 200, resp.text
            cache[username] = {"Authorization": f"Bearer {resp.json()['token']}"}
        return cache[username]

    return _login
