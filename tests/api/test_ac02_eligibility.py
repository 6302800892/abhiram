"""AC-02: hospital eligibility lookup by member_id + policy (EL-R4 .. EL-R6)."""

import pytest
from fastapi.testclient import TestClient


def _check(client: TestClient, headers: dict[str, str], member: str, policy: str) -> dict[str, object]:
    resp = client.post("/api/eligibility", json={"member_id": member, "policy_number": policy}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()  # type: ignore[no-any-return]


@pytest.mark.ac("AC-02")
def test_ac02_1_eligible_member(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("cityhosp.desk"), "MBR-1001", "POL-SLV-0001")
    assert body["status"] == "ELIGIBLE"
    assert body["reason_codes"] == ["ELG-OK"]
    assert body["remaining_sum_insured"] == "500000.00"


@pytest.mark.ac("AC-02")
def test_ac02_2_unknown_policy(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("cityhosp.desk"), "MBR-1001", "POL-NOPE-9999")
    assert body == {**body, "status": "NOT_ELIGIBLE", "reason_codes": ["ELG-POLICY-NOT-FOUND"]}


@pytest.mark.ac("AC-02")
def test_ac02_3_member_not_on_policy(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("cityhosp.desk"), "MBR-2001", "POL-SLV-0001")
    assert body["reason_codes"] == ["ELG-MEMBER-NOT-COVERED"]


@pytest.mark.ac("AC-02")
def test_ac02_8_no_cover_amount_leaks_for_foreign_member(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("cityhosp.desk"), "MBR-2001", "POL-SLV-0001")
    assert body["remaining_sum_insured"] is None


@pytest.mark.ac("AC-02")
def test_ac02_4_lapsed_policy_returns_both_codes(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("cityhosp.desk"), "MBR-3001", "POL-SLV-0003")
    assert body["status"] == "NOT_ELIGIBLE"
    assert body["reason_codes"] == ["ELG-POLICY-INACTIVE", "ELG-OUTSIDE-COVER-PERIOD"]


@pytest.mark.ac("AC-02")
def test_ac02_5_exhausted_sum_insured(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("cityhosp.desk"), "MBR-4001", "POL-SLV-0004")
    assert "ELG-SUM-INSURED-EXHAUSTED" in body["reason_codes"]  # type: ignore[operator]


@pytest.mark.ac("AC-02")
def test_ac02_6_non_network_hospital(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = _check(client, login("greenfield.desk"), "MBR-1001", "POL-SLV-0001")
    assert body["reason_codes"] == ["ELG-HOSPITAL-NOT-NETWORK"]


@pytest.mark.ac("AC-02")
def test_ac02_7_customer_cannot_call_eligibility(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    resp = client.post("/api/eligibility", json={"member_id": "MBR-1001", "policy_number": "POL-SLV-0001"},
                       headers=login("asha.verma"))
    assert resp.status_code == 403
