"""Network & coverage admin (NA-AC1 .. NA-AC7, NFR-05 policy versions append-only)."""

import pytest
from fastapi.testclient import TestClient

REQUIRED = [
    "PA-SUBMITTED", "PA-MANUAL-REVIEW", "PA-AUTO-APPROVED", "PA-AUTO-CAPPED", "PA-REJECTED-EXCLUSION",
    "PA-QUERY-UNKNOWN-DIAGNOSIS", "PA-QUERY-ANSWERED", "PA-QUERY-DOCUMENTS", "PA-APPROVED-MANUAL",
    "PA-PARTIAL-MANUAL", "PA-REJECTED-MANUAL", "PA-OVERRIDE",
]
NEW_RULE = {
    "auto_approve_threshold": "60000.00",
    "auto_approved_diagnoses": ["K35.8", "J18.9"],
    "excluded_diagnoses": ["Z41.1"],
    "per_claim_cap": "250000.00",
    "buffer_pct": "5",
    "deductible": "2500.00",
    "copay_pct": "10",
    "reason_codes": REQUIRED,
}


def test_na_ac1_created_hospital_is_listed_in_network(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    admin = login("admin.sam")
    resp = client.post("/api/admin/hospitals", headers=admin,
                       json={"code": "SUNRISE", "name": "Sunrise Hospital", "city": "Mysuru", "in_network": True})
    assert resp.status_code == 201
    listed = client.get("/api/network-hospitals", headers=login("asha.verma")).json()
    assert "SUNRISE" in {h["code"] for h in listed}


def test_duplicate_hospital_code_is_409(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/admin/hospitals", headers=login("admin.sam"),
                       json={"code": "CITYHOSP", "name": "Dup", "city": "X", "in_network": True})
    assert resp.status_code == 409


@pytest.mark.ac("AC-02")
def test_na_ac2_removing_hospital_from_network_blocks_eligibility(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.patch("/api/admin/hospitals/CITYHOSP", json={"in_network": False}, headers=login("admin.sam"))
    assert resp.status_code == 200 and resp.json()["in_network"] is False
    body = client.post("/api/eligibility", json={"member_id": "MBR-1001", "policy_number": "POL-SLV-0001"},
                       headers=login("cityhosp.desk")).json()
    assert body["reason_codes"] == ["ELG-HOSPITAL-NOT-NETWORK"]


@pytest.mark.nfr("NFR-05")
def test_na_ac3_publish_creates_new_version_and_keeps_old(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    admin = login("admin.sam")
    before = client.get("/api/admin/products/SILVER/coverage-rules", headers=admin).json()
    resp = client.post("/api/admin/products/SILVER/coverage-rules", json=NEW_RULE, headers=admin)
    assert resp.status_code == 201
    assert resp.json()["version"] == 2
    after = client.get("/api/admin/products/SILVER/coverage-rules", headers=admin).json()
    assert [v["version"] for v in after] == [1, 2]
    assert after[0] == before[0]
    products = client.get("/api/admin/products", headers=admin).json()
    assert next(p for p in products if p["code"] == "SILVER")["current_version"] == 2


def test_na_ac4_overlapping_lists_rejected(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    bad = {**NEW_RULE, "excluded_diagnoses": ["K35.8"]}
    resp = client.post("/api/admin/products/SILVER/coverage-rules", json=bad, headers=login("admin.sam"))
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_COVERAGE_RULE"


@pytest.mark.nfr("NFR-01")
def test_float_money_in_rule_is_rejected(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    bad = {**NEW_RULE, "per_claim_cap": 250000.5}
    resp = client.post("/api/admin/products/SILVER/coverage-rules", json=bad, headers=login("admin.sam"))
    assert resp.status_code == 422


def test_create_product(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/admin/products", headers=login("admin.sam"),
                       json={"code": "PLAT", "name": "Platinum", "sum_insured": "2000000.00",
                             "annual_premium": "30000.00"})
    assert resp.status_code == 201
    assert resp.json()["current_version"] is None


@pytest.mark.nfr("NFR-04")
@pytest.mark.parametrize("path", ["/api/admin/hospitals", "/api/admin/products"])
def test_na_ac7_admin_endpoints_reject_hospital(client: TestClient, login, path: str) -> None:  # type: ignore[no-untyped-def]
    assert client.get(path, headers=login("cityhosp.desk")).status_code == 403
