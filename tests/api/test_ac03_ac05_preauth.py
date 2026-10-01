"""AC-03 submission enters PENDING, AC-04 system outcomes, AC-05 auto-approval (PA-R1 .. PA-R8)."""

import logging

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import submit_preauth


@pytest.mark.ac("AC-03")
def test_ac03_1_manual_review_preauth_stays_pending(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9", estimate="80000.00")
    assert body["status"] == "PENDING"
    assert [(d["status"], d["reason_codes"]) for d in body["decisions"]] == [
        ("PENDING", ["PA-SUBMITTED"]),
        ("PENDING", ["PA-MANUAL-REVIEW"]),
    ]
    assert body["approved_amount"] is None
    assert body["rule_version"] == {"product_code": "SILVER", "version": 1}


@pytest.mark.ac("AC-03")
def test_ac03_2_first_decision_is_pending_and_case_is_pre_auth(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="40000.00")
    first = body["decisions"][0]
    assert (first["status"], first["reason_codes"], first["decided_by"]) == ("PENDING", ["PA-SUBMITTED"], "SYSTEM")
    assert body["case_status"] == "PRE_AUTH"
    assert body["case_number"].startswith("CASE-")


@pytest.mark.ac("AC-03")
@pytest.mark.parametrize(("estimate", "admission"), [("0.00", "2026-06-16"), ("-5.00", "2026-06-16"),
                                                     ("1000.00", "2026-06-14")])
def test_ac03_3_invalid_estimate_or_past_date_is_422(  # type: ignore[no-untyped-def]
    client: TestClient, login, estimate: str, admission: str
) -> None:
    submit_preauth(client, login("cityhosp.desk"), estimate=estimate, admission=admission, expected=422)


@pytest.mark.ac("AC-03")
def test_ac03_float_estimate_is_422(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/preauths", headers=login("cityhosp.desk"), json={
        "member_id": "MBR-1001", "policy_number": "POL-SLV-0001", "diagnosis_code": "K35.8",
        "estimated_cost": 40000.5, "expected_admission_date": "2026-06-16"})
    assert resp.status_code == 422


@pytest.mark.ac("AC-03")
def test_ac03_4_ineligible_member_is_422_with_reasons(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/preauths", headers=login("cityhosp.desk"), json={
        "member_id": "MBR-3001", "policy_number": "POL-SLV-0003", "diagnosis_code": "K35.8",
        "estimated_cost": "1000.00", "expected_admission_date": "2026-06-16"})
    assert resp.status_code == 422
    error = resp.json()["error"]
    assert error["code"] == "NOT_ELIGIBLE"
    assert "ELG-POLICY-INACTIVE" in error["details"]["reason_codes"]


@pytest.mark.ac("AC-05")
def test_ac05_1_within_threshold_auto_approved(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="40000.00")
    assert (body["status"], body["approved_amount"], body["reason_codes"]) == (
        "APPROVED", "40000.00", ["PA-AUTO-APPROVED"])
    assert body["decisions"][-1]["decided_by"] == "SYSTEM"


@pytest.mark.ac("AC-05")
def test_ac05_2_estimate_equal_to_threshold_auto_approves(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="J18.9", estimate="50000.00")
    assert body["status"] == "APPROVED"


@pytest.mark.ac("AC-05")
def test_ac05_3_one_paisa_above_threshold_stays_pending(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="50000.01")
    assert body["status"] == "PENDING"
    assert body["reason_codes"] == ["PA-MANUAL-REVIEW"]


@pytest.mark.ac("AC-05")
def test_ac05_4_capped_at_remaining_sum_insured(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="60000.00",
                          member="MBR-5001", policy="POL-GLD-0005")
    assert (body["status"], body["approved_amount"], body["reason_codes"]) == (
        "PARTIALLY_APPROVED", "40000.00", ["PA-AUTO-CAPPED"])


@pytest.mark.ac("AC-05")
def test_ac05_5_diagnosis_not_on_auto_list_stays_pending(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="N20.0", estimate="10000.00")
    assert body["status"] == "PENDING"


@pytest.mark.ac("AC-04")
def test_ac04_1_unknown_diagnosis_raises_query(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="ZZZ.9", estimate="10000.00")
    assert (body["status"], body["reason_codes"]) == ("QUERY_RAISED", ["PA-QUERY-UNKNOWN-DIAGNOSIS"])


@pytest.mark.ac("AC-04")
def test_ac04_2_excluded_diagnosis_auto_rejected(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    assert (body["status"], body["reason_codes"]) == ("REJECTED", ["PA-REJECTED-EXCLUSION"])
    assert body["decisions"][-1]["decided_by"] == "SYSTEM"


@pytest.mark.ac("AC-04")
def test_ac04_5_reason_codes_come_from_rule_version_catalogue(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="40000.00")
    catalogue = client.get("/api/admin/products/SILVER/coverage-rules", headers=login("admin.sam")).json()[0]
    for decision in body["decisions"]:
        assert set(decision["reason_codes"]) <= set(catalogue["reason_codes"])


@pytest.mark.nfr("NFR-04")
def test_pa_r8_other_hospital_cannot_read_preauth(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = submit_preauth(client, login("cityhosp.desk"))
    assert client.get(f"/api/preauths/{body['preauth_id']}", headers=login("sunshine.desk")).status_code == 404
    assert client.get(f"/api/preauths/{body['preauth_id']}", headers=login("cityhosp.desk")).status_code == 200
    assert client.get(f"/api/preauths/{body['preauth_id']}", headers=login("asha.verma")).status_code == 403


@pytest.mark.nfr("NFR-04")
def test_hospital_lists_only_its_own_preauths(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    submit_preauth(client, login("cityhosp.desk"))
    submit_preauth(client, login("sunshine.desk"), member="MBR-2001", policy="POL-GLD-0002")
    mine = client.get("/api/preauths", headers=login("sunshine.desk")).json()
    assert [p["hospital_code"] for p in mine] == ["SUNSHINE"]
    assert len(client.get("/api/preauths", headers=login("adjudicator.priya")).json()) == 2


@pytest.mark.nfr("NFR-03")
def test_clinical_notes_and_diagnosis_never_logged(client: TestClient, login, caplog) -> None:  # type: ignore[no-untyped-def]
    marker = "patient-reports-crushing-chest-pain-7731"
    with caplog.at_level(logging.DEBUG, logger="medicard"):
        submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9", notes=marker)
    text = "\n".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert caplog.records, "expected service log records"
    assert marker not in text
    assert "I21.9" not in text and "myocardial" not in text.lower()
