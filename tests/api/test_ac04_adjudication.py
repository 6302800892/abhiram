"""AC-04 manual adjudication workbench and query workflow (AD-R1 .. AD-R5, PA-R7)."""

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import decide, submit_preauth


@pytest.mark.ac("AC-04")
def test_ac04_6_insurer_approves_from_queue(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9", estimate="80000.00")
    queue = client.get("/api/adjudication/queue", headers=login("adjudicator.priya")).json()
    assert pre["preauth_id"] in [q["preauth_id"] for q in queue]
    item = next(q for q in queue if q["preauth_id"] == pre["preauth_id"])
    assert item["diagnosis_code"] == "I21.9" and item["estimated_cost"] == "80000.00"
    assert item["case_number"] == pre["case_number"]
    body = decide(client, login("adjudicator.priya"), pre["preauth_id"], "APPROVED", ["PA-APPROVED-MANUAL"])
    assert (body["status"], body["approved_amount"]) == ("APPROVED", "80000.00")
    assert body["decisions"][-1]["decided_by"] == "adjudicator.priya"
    queue_after = client.get("/api/adjudication/queue", headers=login("adjudicator.priya")).json()
    assert pre["preauth_id"] not in [q["preauth_id"] for q in queue_after]


@pytest.mark.ac("AC-04")
def test_ac04_queue_is_oldest_first(client: TestClient, login, clock) -> None:  # type: ignore[no-untyped-def]
    import datetime as dt

    first = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    clock.advance(dt.timedelta(hours=2))
    second = submit_preauth(client, login("cityhosp.desk"), diagnosis="C50.9")
    queue = client.get("/api/adjudication/queue", headers=login("adjudicator.priya")).json()
    ids = [q["preauth_id"] for q in queue]
    assert ids.index(first["preauth_id"]) < ids.index(second["preauth_id"])
    assert queue[0]["age_hours"] == "2.00"


@pytest.mark.ac("AC-04")
def test_ac04_7_partial_approval(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9", estimate="80000.00")
    body = decide(client, login("adjudicator.priya"), pre["preauth_id"], "PARTIALLY_APPROVED",
                  ["PA-PARTIAL-MANUAL"], amount="30000.00")
    assert (body["status"], body["approved_amount"]) == ("PARTIALLY_APPROVED", "30000.00")


@pytest.mark.ac("AC-04")
def test_ac04_partial_amount_not_below_estimate_is_422(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9", estimate="80000.00")
    resp = client.post(f"/api/preauths/{pre['preauth_id']}/decisions", headers=login("adjudicator.priya"),
                       json={"status": "PARTIALLY_APPROVED", "approved_amount": "80000.00",
                             "reason_codes": ["PA-PARTIAL-MANUAL"]})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_APPROVED_AMOUNT"


@pytest.mark.ac("AC-04")
def test_ac04_8_raise_query_then_hospital_answers(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    queried = decide(client, login("adjudicator.priya"), pre["preauth_id"], "QUERY_RAISED", ["PA-QUERY-DOCUMENTS"])
    assert queried["status"] == "QUERY_RAISED"
    resp = client.post(f"/api/preauths/{pre['preauth_id']}/query-response",
                       json={"response_note": "ECG report attached"}, headers=login("cityhosp.desk"))
    assert resp.status_code == 200
    body = resp.json()
    assert (body["status"], body["reason_codes"]) == ("PENDING", ["PA-QUERY-ANSWERED"])  # AC-04.3


@pytest.mark.ac("AC-04")
def test_ac04_query_response_on_pending_is_409(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    resp = client.post(f"/api/preauths/{pre['preauth_id']}/query-response",
                       json={"response_note": "n/a"}, headers=login("cityhosp.desk"))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_PREAUTH_STATE"


@pytest.mark.ac("AC-04")
def test_ac04_other_hospital_cannot_answer_query(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="ZZZ.9")
    resp = client.post(f"/api/preauths/{pre['preauth_id']}/query-response",
                       json={"response_note": "x"}, headers=login("sunshine.desk"))
    assert resp.status_code == 404


@pytest.mark.ac("AC-04")
def test_ac04_9_unknown_reason_code_is_422(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    resp = client.post(f"/api/preauths/{pre['preauth_id']}/decisions", headers=login("adjudicator.priya"),
                       json={"status": "REJECTED", "reason_codes": ["PA-BECAUSE-I-SAID-SO"]})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNKNOWN_REASON_CODE"


@pytest.mark.ac("AC-04")
def test_ac04_4_decision_on_decided_preauth_is_409(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="40000.00")
    assert pre["status"] == "APPROVED"
    decide(client, login("adjudicator.priya"), pre["preauth_id"], "REJECTED", ["PA-REJECTED-MANUAL"], expected=409)


@pytest.mark.ac("AC-04")
def test_ac04_10_hospital_cannot_decide(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    decide(client, login("cityhosp.desk"), pre["preauth_id"], "APPROVED", ["PA-APPROVED-MANUAL"], expected=403)


@pytest.mark.ac("AC-04")
def test_ac04_reason_codes_validated_against_preauth_version_not_latest(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    """A pre-auth keeps the rule version it was submitted under (PA-R3/PA-R6)."""
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    rule = client.get("/api/admin/products/SILVER/coverage-rules", headers=login("admin.sam")).json()[0]
    new_rule = {k: rule[k] for k in ("auto_approve_threshold", "auto_approved_diagnoses", "excluded_diagnoses",
                                     "per_claim_cap", "buffer_pct", "deductible", "copay_pct")}
    new_rule["reason_codes"] = [*rule["reason_codes"], "PA-NEW-IN-V2"]
    assert client.post("/api/admin/products/SILVER/coverage-rules", json=new_rule,
                       headers=login("admin.sam")).status_code == 201
    resp = client.post(f"/api/preauths/{pre['preauth_id']}/decisions", headers=login("adjudicator.priya"),
                       json={"status": "REJECTED", "reason_codes": ["PA-NEW-IN-V2"]})
    assert resp.status_code == 422
    assert client.get(f"/api/preauths/{pre['preauth_id']}", headers=login("adjudicator.priya")).json()[
        "rule_version"]["version"] == 1
