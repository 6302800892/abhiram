"""Fix loop FL-001 (docs/fix-loops/FL-001-rule-version-mid-cycle.md).

The Sprint 3 evaluator published a new coverage-rule version mid-cycle. The bill cap and the
settlement then used the *current* rule version instead of the one the pre-auth recorded
(PA-R3, NA-R4, ST-R1 as amended). These tests reproduce failures C-01a, C-01b and C-02.
"""

import pytest
from fastapi.testclient import TestClient

from tests.api.lifecycle import HOSPITAL, INSURER, admitted_case, approved_case, post

ADMIN = "admin.sam"


def _publish_silver_v2(client: TestClient, login, **changes: str) -> None:  # type: ignore[no-untyped-def]
    v1 = client.get("/api/admin/products/SILVER/coverage-rules", headers=login(ADMIN)).json()[0]
    keys = ("auto_approve_threshold", "auto_approved_diagnoses", "excluded_diagnoses", "per_claim_cap",
            "buffer_pct", "deductible", "copay_pct", "reason_codes")
    body = {k: v1[k] for k in keys} | changes
    resp = client.post("/api/admin/products/SILVER/coverage-rules", json=body, headers=login(ADMIN))
    assert resp.status_code == 201 and resp.json()["version"] == 2


@pytest.mark.ac("AC-06")
def test_c01a_bill_cap_keeps_the_preauth_rule_version(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = admitted_case(client, login, estimate="100000.00")  # approved under SILVER v1, buffer 10 %
    _publish_silver_v2(client, login, buffer_pct="5")
    body = post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "108000.00"}, expected=201)
    assert body["cap"] == "110000.00"


@pytest.mark.ac("AC-07")
def test_c01b_settlement_uses_the_preauth_rule_version(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = admitted_case(client, login, estimate="100000.00")
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "108000.00"}, expected=201)
    _publish_silver_v2(client, login, buffer_pct="5", deductible="0.00", copay_pct="0")
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/discharge", {"discharged_on": "2026-06-19"})
    s = post(client, login(INSURER), f"/api/cases/{case_id}/settle")
    assert (s["buffer_pct"], s["cap"], s["admissible"], s["deductible"], s["copay"], s["settlement_amount"]) == (
        "10", "110000.00", "108000.00", "5000.00", "10300.00", "92700.00")


@pytest.mark.ac("AC-07")
def test_c01_new_preauths_after_publish_use_the_new_version(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    _publish_silver_v2(client, login, buffer_pct="5")
    case_id = admitted_case(client, login, estimate="100000.00")
    body = post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "105000.01"}, expected=422)
    assert body["error"]["details"]["cap"] == "105000.00"


@pytest.mark.ac("AC-08")
def test_c02_closing_pre_auth_case_with_live_preauth_is_invalid_claim_state(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = approved_case(client, login)
    body = post(client, login(INSURER), f"/api/cases/{case_id}/close", expected=409)
    assert body["error"]["code"] == "INVALID_CLAIM_STATE"
