"""AC-07 settlement through the API, stub payment and remaining-cover reduction (ST-R5 .. ST-R8)."""

import pytest
from fastapi.testclient import TestClient

from tests.api.lifecycle import HOSPITAL, INSURER, discharged_case, post, settled_case


@pytest.mark.ac("AC-07")
def test_ac07_6_settle_returns_breakdown_and_payment_reference(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = discharged_case(client, login, bill="90000.00")
    body = post(client, login(INSURER), f"/api/cases/{case_id}/settle")
    assert body["case_status"] == "SETTLED"
    assert {k: body[k] for k in ("pre_auth_amount", "buffer_pct", "cap", "final_bill", "admissible",
                                 "deductible", "copay", "settlement_amount")} == {
        "pre_auth_amount": "100000.00", "buffer_pct": "10", "cap": "110000.00", "final_bill": "90000.00",
        "admissible": "90000.00", "deductible": "5000.00", "copay": "8500.00", "settlement_amount": "76500.00",
    }
    assert body["payment_reference"] == f"PAYSTUB-{case_id}-1"
    assert body["settled_by"] == "adjudicator.priya"


@pytest.mark.ac("AC-07")
def test_ac07_6_settlement_reduces_remaining_sum_insured(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    settled_case(client, login, bill="90000.00")
    policy = client.get("/api/customers/me/coverage", headers=login("asha.verma")).json()["policies"][0]
    assert policy["remaining_sum_insured"] == "423500.00"  # 500000.00 - 76500.00


@pytest.mark.ac("AC-07")
def test_ac07_7_settling_twice_is_409(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = settled_case(client, login)
    body = post(client, login(INSURER), f"/api/cases/{case_id}/settle", expected=409)
    assert body["error"]["code"] == "CASE_SETTLED_IMMUTABLE"


@pytest.mark.ac("AC-07")
def test_ac07_settle_requires_discharge(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    from tests.api.lifecycle import admitted_case

    case_id = admitted_case(client, login)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "1000.00"}, expected=201)
    assert post(client, login(INSURER), f"/api/cases/{case_id}/settle", expected=409)["error"]["code"] == (
        "INVALID_CLAIM_STATE")


@pytest.mark.ac("AC-07")
def test_ac07_settle_requires_final_bill(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    from tests.api.lifecycle import admitted_case

    case_id = admitted_case(client, login)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/discharge", {"discharged_on": "2026-06-19"})
    assert post(client, login(INSURER), f"/api/cases/{case_id}/settle", expected=422)["error"]["code"] == (
        "FINAL_BILL_REQUIRED")


@pytest.mark.ac("AC-07")
def test_ac07_small_bill_below_deductible_settles_to_zero(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = discharged_case(client, login, bill="3000.00")
    assert post(client, login(INSURER), f"/api/cases/{case_id}/settle")["settlement_amount"] == "0.00"


@pytest.mark.ac("AC-07")
def test_ac07_customer_sees_post_discharge_summary(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = settled_case(client, login)
    summary = client.get(f"/api/cases/{case_id}/settlement", headers=login("asha.verma"))
    assert summary.status_code == 200
    assert summary.json()["settlement_amount"] == "76500.00"
    assert client.get(f"/api/cases/{case_id}/settlement", headers=login("kiran.rao")).status_code == 404


@pytest.mark.nfr("NFR-04")
def test_only_insurer_can_settle(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = discharged_case(client, login)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/settle", expected=403)
    post(client, login("admin.sam"), f"/api/cases/{case_id}/settle", expected=403)
