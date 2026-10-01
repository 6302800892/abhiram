"""NFR-07 health, NFR-04 authentication boundary, NFR-06 correlation ids."""

import time

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.domain.clock import FixedClock
from src.main import create_app


@pytest.mark.nfr("NFR-07")
def test_health_returns_200_within_one_second_of_startup(settings: Settings, clock: FixedClock) -> None:
    started = time.perf_counter()
    with TestClient(create_app(settings=settings, clock=clock)) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert time.perf_counter() - started < 1.0


def test_login_success_returns_token_and_role(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"username": "cityhosp.desk", "password": "Demo@1234"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "HOSPITAL" and body["token"]


def test_login_wrong_password_is_401(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"username": "cityhosp.desk", "password": "nope-nope"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.nfr("NFR-04")
def test_protected_route_without_token_is_401(client: TestClient) -> None:
    assert client.get("/api/customers/me/coverage").status_code == 401


@pytest.mark.nfr("NFR-04")
def test_garbage_token_is_401(client: TestClient) -> None:
    resp = client.get("/api/customers/me/coverage", headers={"Authorization": "Bearer abc.def"})
    assert resp.status_code == 401


@pytest.mark.nfr("NFR-06")
def test_correlation_id_is_echoed_or_generated(client: TestClient) -> None:
    echoed = client.get("/health", headers={"X-Correlation-ID": "corr-123"})
    assert echoed.headers["X-Correlation-ID"] == "corr-123"
    generated = client.get("/health")
    assert len(generated.headers["X-Correlation-ID"]) >= 16


def test_me_returns_principal(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/api/auth/me", headers=login("cityhosp.desk"))
    assert resp.status_code == 200
    assert resp.json()["hospital_code"] == "CITYHOSP"
