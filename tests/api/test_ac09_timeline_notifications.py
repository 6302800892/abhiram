"""AC-09 stub notifications at every state transition + shared case timeline (AM-R7, AM-R8)."""

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import submit_preauth
from tests.api.lifecycle import HOSPITAL, settled_case


@pytest.mark.ac("AC-09")
def test_ac09_1_one_notification_per_transition_in_order(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = settled_case(client, login)
    notes = client.get("/api/customers/me/notifications", headers=login("asha.verma")).json()
    mine = [(n["event"], n["to_status"]) for n in notes if n["case_id"] == case_id]
    assert mine == [
        ("PREAUTH_STATUS", "PENDING"),
        ("PREAUTH_STATUS", "APPROVED"),
        ("CASE_STATUS", "ADMITTED"),
        ("CASE_STATUS", "DISCHARGED"),
        ("CASE_STATUS", "SETTLED"),
    ]
    assert all(n["channel"] == "STUB" for n in notes)


@pytest.mark.ac("AC-09")
def test_ac09_2_hospital_and_customer_see_same_timeline(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = settled_case(client, login)
    hospital_view = client.get(f"/api/cases/{case_id}/timeline", headers=login(HOSPITAL)).json()
    customer_view = client.get(f"/api/cases/{case_id}/timeline", headers=login("asha.verma")).json()
    assert hospital_view == customer_view
    kinds = [e["event_type"] for e in hospital_view]
    assert kinds[0] == "PREAUTH_STATUS" and "FINAL_BILL" in kinds and kinds[-1] == "CASE_STATUS"
    times = [e["occurred_at"] for e in hospital_view]
    assert times == sorted(times)


@pytest.mark.ac("AC-09")
def test_ac09_3_other_hospital_and_other_customer_get_404(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = settled_case(client, login)
    assert client.get(f"/api/cases/{case_id}/timeline", headers=login("sunshine.desk")).status_code == 404
    assert client.get(f"/api/cases/{case_id}/timeline", headers=login("kiran.rao")).status_code == 404


@pytest.mark.ac("AC-09")
def test_ac09_auto_rejection_notifies_customer(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login(HOSPITAL), diagnosis="Z41.1", estimate="5000.00")
    notes = client.get("/api/customers/me/notifications", headers=login("asha.verma")).json()
    assert [n["to_status"] for n in notes if n["case_id"] == pre["case_id"]] == ["PENDING", "REJECTED"]


@pytest.mark.nfr("NFR-03")
def test_ac09_notifications_carry_no_diagnosis(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    submit_preauth(client, login(HOSPITAL), diagnosis="I21.9")
    notes = client.get("/api/customers/me/notifications", headers=login("asha.verma")).json()
    text = " ".join(n["message"] for n in notes)
    assert "I21.9" not in text and "myocardial" not in text.lower()
