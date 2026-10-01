"""Helpers that drive a case through the lifecycle via the public API (no DB shortcuts)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from tests.api.helpers import decide, submit_preauth

Login = Callable[[str], dict[str, str]]
HOSPITAL = "cityhosp.desk"
INSURER = "adjudicator.priya"


def post(client: TestClient, headers: dict[str, str], path: str, body: dict[str, Any] | None = None,
         expected: int = 200) -> dict[str, Any]:
    resp = client.post(path, json=body or {}, headers=headers)
    assert resp.status_code == expected, resp.text
    return resp.json()  # type: ignore[no-any-return]


def approved_case(client: TestClient, login: Login, estimate: str = "100000.00") -> int:
    """Manual-review diagnosis approved in full by the adjudicator -> case in PRE_AUTH, pre_auth_amount=estimate."""
    pre = submit_preauth(client, login(HOSPITAL), diagnosis="I21.9", estimate=estimate)
    decide(client, login(INSURER), pre["preauth_id"], "APPROVED", ["PA-APPROVED-MANUAL"])
    return int(pre["case_id"])


def admitted_case(client: TestClient, login: Login, estimate: str = "100000.00") -> int:
    case_id = approved_case(client, login, estimate)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/admit", {"admitted_on": "2026-06-16"})
    return case_id


def discharged_case(client: TestClient, login: Login, bill: str = "90000.00", estimate: str = "100000.00") -> int:
    case_id = admitted_case(client, login, estimate)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": bill}, expected=201)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/discharge", {"discharged_on": "2026-06-19"})
    return case_id


def settled_case(client: TestClient, login: Login, bill: str = "90000.00") -> int:
    case_id = discharged_case(client, login, bill)
    post(client, login(INSURER), f"/api/cases/{case_id}/settle")
    return case_id
