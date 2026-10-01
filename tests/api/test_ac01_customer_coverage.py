"""AC-01: customer registers, links a policy and sees coverage (EL-R1 .. EL-R3)."""

import pytest
from fastapi.testclient import TestClient

NEW_USER = {"username": "ravi.k", "password": "Secret@123", "full_name": "Ravi Kumar"}
LINK_ROHAN = {"policy_number": "POL-SLV-0001", "member_id": "MBR-1002", "date_of_birth": "2015-09-03"}


def _register_and_login(client: TestClient) -> dict[str, str]:
    assert client.post("/api/customers/register", json=NEW_USER).status_code == 201
    token = client.post("/api/auth/login", json={"username": "ravi.k", "password": "Secret@123"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.ac("AC-01")
def test_ac01_1_register_then_login(client: TestClient) -> None:
    resp = client.post("/api/customers/register", json=NEW_USER)
    assert resp.status_code == 201
    assert resp.json()["customer_id"] > 0
    login = client.post("/api/auth/login", json={"username": "ravi.k", "password": "Secret@123"})
    assert login.status_code == 200 and login.json()["role"] == "CUSTOMER"


@pytest.mark.ac("AC-01")
def test_ac01_2_duplicate_username_is_409(client: TestClient) -> None:
    client.post("/api/customers/register", json=NEW_USER)
    resp = client.post("/api/customers/register", json=NEW_USER)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "USERNAME_TAKEN"


@pytest.mark.ac("AC-01")
def test_ac01_short_password_is_422(client: TestClient) -> None:
    resp = client.post("/api/customers/register", json={**NEW_USER, "password": "short"})
    assert resp.status_code == 422


@pytest.mark.ac("AC-01")
def test_ac01_3_link_policy_with_matching_identity(client: TestClient) -> None:
    headers = _register_and_login(client)
    resp = client.post("/api/customers/me/policies", json=LINK_ROHAN, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["policy_number"] == "POL-SLV-0001"
    coverage = client.get("/api/customers/me/coverage", headers=headers).json()
    assert [p["member_id"] for p in coverage["policies"]] == ["MBR-1002"]


@pytest.mark.ac("AC-01")
def test_ac01_4_wrong_date_of_birth_is_422(client: TestClient) -> None:
    headers = _register_and_login(client)
    resp = client.post("/api/customers/me/policies", json={**LINK_ROHAN, "date_of_birth": "2015-09-04"},
                       headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "POLICY_LINK_MISMATCH"


@pytest.mark.ac("AC-01")
def test_ac01_member_already_linked_is_409(client: TestClient) -> None:
    headers = _register_and_login(client)
    taken = {"policy_number": "POL-SLV-0001", "member_id": "MBR-1001", "date_of_birth": "1988-04-12"}
    resp = client.post("/api/customers/me/policies", json=taken, headers=headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "MEMBER_ALREADY_LINKED"


@pytest.mark.ac("AC-01")
def test_ac01_5_coverage_shows_sum_insured_exclusions_and_network(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    coverage = client.get("/api/customers/me/coverage", headers=login("asha.verma")).json()
    policy = coverage["policies"][0]
    assert policy["sum_insured"] == "500000.00"
    assert policy["remaining_sum_insured"] == "500000.00"
    assert {"code": "Z41.1", "label": "Cosmetic surgery"} in policy["exclusions"]
    codes = {h["code"] for h in coverage["network_hospitals"]}
    assert "CITYHOSP" in codes and "NONNET" not in codes


@pytest.mark.ac("AC-01")
def test_ac01_coverage_requires_customer_role(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/customers/me/coverage", headers=login("cityhosp.desk")).status_code == 403
