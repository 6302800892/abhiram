"""Regression tests for specs/reviews/security-review.md findings SEC-06, -07, -08, -09, -12, -17."""

import datetime as dt
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.domain.clock import FixedClock
from src.main import create_app
from tests.api.helpers import submit_preauth
from tests.api.lifecycle import INSURER, discharged_case, post


@pytest.mark.nfr("NFR-04")
def test_sec06_non_ascii_token_is_401_not_500(client: TestClient) -> None:
    raw = "Bearer abc.déf".encode("latin-1")  # raw latin-1 bytes, as the security probe sent
    resp = client.get("/api/auth/me", headers={"Authorization": raw})  # type: ignore[dict-item]
    assert resp.status_code == 401


@pytest.mark.nfr("NFR-01")
@pytest.mark.parametrize("amount", ["1e30", "1e999999", "99999999999999.00"])
def test_sec07_absurd_money_is_422_invalid_money(client: TestClient, login, amount: str) -> None:  # type: ignore[no-untyped-def]
    case_id = discharged_case(client, login)
    resp = client.post(f"/api/cases/{case_id}/final-bill", json={"amount": amount}, headers=login("cityhosp.desk"))
    assert resp.status_code == 422


@pytest.mark.nfr("NFR-08")
def test_sec08_duplicate_settlement_insert_is_409_not_500(  # type: ignore[no-untyped-def]
    client: TestClient, login, monkeypatch
) -> None:
    """A racing second settle that passes the status check must lose on UNIQUE(case_id) with a 409."""
    from src.service import settlement_service

    case_id = discharged_case(client, login)
    post(client, login(INSURER), f"/api/cases/{case_id}/settle")
    monkeypatch.setattr(settlement_service, "ensure_case_mutable", lambda _status: None)
    monkeypatch.setattr(settlement_service, "transition", lambda _cur, target: target)
    body = post(client, login(INSURER), f"/api/cases/{case_id}/settle", expected=409)
    assert body["error"]["code"] == "CASE_SETTLED_IMMUTABLE"


@pytest.mark.ac("AC-10")
def test_sec09_override_requires_case_still_in_pre_auth(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    post(client, login(INSURER), f"/api/cases/{pre['case_id']}/close")
    resp = client.post(f"/api/admin/preauths/{pre['preauth_id']}/override",
                       json={"status": "APPROVED", "reason": "late"}, headers=login("admin.sam"))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_CLAIM_STATE"
    assert client.get("/api/admin/audit", headers=login("admin.sam")).json() == []


def test_sec12_short_secret_is_rejected(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="MEDICARD_SECRET"):
        create_app(Settings(db_path=str(tmp_path / "x.db"), secret="short", frontend_dist=None),
                   FixedClock(dt.datetime(2026, 6, 15, tzinfo=dt.UTC)))


@pytest.mark.nfr("NFR-04")
def test_sec17_customer_without_profile_sees_no_unlinked_cases(  # type: ignore[no-untyped-def]
    client: TestClient, login, settings: Settings
) -> None:
    pre = submit_preauth(client, login("cityhosp.desk"), member="MBR-1002")  # unlinked dependant
    conn = sqlite3.connect(settings.db_path)
    conn.execute("DELETE FROM customers WHERE user_id = (SELECT id FROM users WHERE username = 'kiran.rao')")
    conn.execute("UPDATE members SET customer_id = NULL WHERE member_id = 'MBR-2001'")
    conn.commit()
    conn.close()
    token = client.post("/api/auth/login", json={"username": "kiran.rao", "password": "Demo@1234"}).json()["token"]
    resp = client.get(f"/api/cases/{pre['case_id']}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
