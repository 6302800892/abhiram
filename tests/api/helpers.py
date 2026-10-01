"""Small request helpers shared by API tests (keeps AC tests readable)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

TOMORROW = "2026-06-16"  # conftest pins today to 2026-06-15


def submit_preauth(
    client: TestClient,
    headers: dict[str, str],
    *,
    diagnosis: str = "I21.9",
    estimate: str = "80000.00",
    member: str = "MBR-1001",
    policy: str = "POL-SLV-0001",
    admission: str = TOMORROW,
    notes: str | None = None,
    expected: int = 201,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "member_id": member, "policy_number": policy, "diagnosis_code": diagnosis,
        "estimated_cost": estimate, "expected_admission_date": admission,
    }
    if notes is not None:
        body["clinical_notes"] = notes
    resp = client.post("/api/preauths", json=body, headers=headers)
    assert resp.status_code == expected, resp.text
    return resp.json()  # type: ignore[no-any-return]


def decide(
    client: TestClient,
    headers: dict[str, str],
    preauth_id: int,
    status: str,
    reasons: list[str],
    amount: str | None = None,
    expected: int = 200,
) -> dict[str, Any]:
    body: dict[str, Any] = {"status": status, "reason_codes": reasons}
    if amount is not None:
        body["approved_amount"] = amount
    resp = client.post(f"/api/preauths/{preauth_id}/decisions", json=body, headers=headers)
    assert resp.status_code == expected, resp.text
    return resp.json()  # type: ignore[no-any-return]
