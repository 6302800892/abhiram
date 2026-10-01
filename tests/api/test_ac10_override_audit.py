"""AC-10 insurer-admin override of auto-rejected / escalated pre-auths, audited (AD-R6 .. AD-R8)."""

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import decide, submit_preauth

ADMIN = "admin.sam"


def _override(client: TestClient, headers: dict[str, str], preauth_id: int, body: dict[str, object],
              expected: int = 200) -> dict[str, object]:
    resp = client.post(f"/api/admin/preauths/{preauth_id}/override", json=body, headers=headers)
    assert resp.status_code == expected, resp.text
    return resp.json()  # type: ignore[no-any-return]


@pytest.mark.ac("AC-10")
def test_ac10_1_override_auto_rejection_is_audited(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    assert pre["status"] == "REJECTED"
    body = _override(client, login(ADMIN), pre["preauth_id"],
                     {"status": "APPROVED", "reason": "Reconstructive after accident, not cosmetic"})
    assert (body["status"], body["approved_amount"], body["reason_codes"]) == ("APPROVED", "10000.00", ["PA-OVERRIDE"])
    assert body["decisions"][-1]["decided_by"] == ADMIN
    audit = client.get("/api/admin/audit", headers=login(ADMIN)).json()
    record = audit[0]
    assert {k: record[k] for k in ("actor", "action", "entity_type", "entity_id", "from_status", "to_status",
                                   "reason")} == {
        "actor": ADMIN, "action": "PREAUTH_OVERRIDE", "entity_type": "preauth", "entity_id": pre["preauth_id"],
        "from_status": "REJECTED", "to_status": "APPROVED", "reason": "Reconstructive after accident, not cosmetic",
    }
    assert record["occurred_at"].startswith("2026-06-15T10:00")


@pytest.mark.ac("AC-10")
def test_ac10_2_override_escalated_query_partially(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9", estimate="80000.00")
    decide(client, login("adjudicator.priya"), pre["preauth_id"], "QUERY_RAISED", ["PA-QUERY-DOCUMENTS"])
    body = _override(client, login(ADMIN), pre["preauth_id"],
                     {"status": "PARTIALLY_APPROVED", "approved_amount": "50000.00", "reason": "Escalated by hospital"})
    assert (body["status"], body["approved_amount"]) == ("PARTIALLY_APPROVED", "50000.00")
    assert client.get("/api/admin/audit", headers=login(ADMIN)).json()[0]["from_status"] == "QUERY_RAISED"


@pytest.mark.ac("AC-10")
def test_ac10_3_insurer_cannot_override_and_nothing_is_audited(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    _override(client, login("adjudicator.priya"), pre["preauth_id"], {"status": "APPROVED", "reason": "x"},
              expected=403)
    assert client.get("/api/admin/audit", headers=login(ADMIN)).json() == []
    assert client.get(f"/api/preauths/{pre['preauth_id']}", headers=login(ADMIN)).json()["status"] == "REJECTED"


@pytest.mark.ac("AC-10")
def test_ac10_4_blank_reason_is_rejected_and_not_audited(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    body = _override(client, login(ADMIN), pre["preauth_id"], {"status": "APPROVED", "reason": "   "}, expected=422)
    assert body["error"]["code"] == "OVERRIDE_REASON_REQUIRED"  # type: ignore[index]
    assert client.get("/api/admin/audit", headers=login(ADMIN)).json() == []


@pytest.mark.ac("AC-10")
def test_ac10_5_manual_rejection_cannot_be_overridden(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="I21.9")
    decide(client, login("adjudicator.priya"), pre["preauth_id"], "REJECTED", ["PA-REJECTED-MANUAL"])
    body = _override(client, login(ADMIN), pre["preauth_id"], {"status": "APPROVED", "reason": "please"},
                     expected=422)
    assert body["error"]["code"] == "OVERRIDE_NOT_ALLOWED"  # type: ignore[index]


@pytest.mark.ac("AC-10")
def test_ac10_5_approved_preauth_cannot_be_overridden(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="K35.8", estimate="40000.00")
    _override(client, login(ADMIN), pre["preauth_id"], {"status": "APPROVED", "reason": "again"}, expected=422)


@pytest.mark.ac("AC-10")
def test_ac10_override_amount_rules_apply(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    body = _override(client, login(ADMIN), pre["preauth_id"],
                     {"status": "PARTIALLY_APPROVED", "approved_amount": "10000.00", "reason": "r"}, expected=422)
    assert body["error"]["code"] == "INVALID_APPROVED_AMOUNT"  # type: ignore[index]


@pytest.mark.ac("AC-10")
def test_ac10_overridden_case_can_be_admitted_and_customer_notified(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    _override(client, login(ADMIN), pre["preauth_id"], {"status": "APPROVED", "reason": "Medical necessity"})
    resp = client.post(f"/api/cases/{pre['case_id']}/admit", json={"admitted_on": "2026-06-16"},
                       headers=login("cityhosp.desk"))
    assert resp.status_code == 200
    notes = client.get("/api/customers/me/notifications", headers=login("asha.verma")).json()
    assert [n["to_status"] for n in notes if n["case_id"] == pre["case_id"]] == [
        "PENDING", "REJECTED", "APPROVED", "ADMITTED"]


@pytest.mark.nfr("NFR-04")
def test_audit_log_is_admin_only(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/admin/audit", headers=login("adjudicator.priya")).status_code == 403


@pytest.mark.ac("AC-10")
def test_ac10_concurrent_override_loses_with_409_and_single_audit_row(  # type: ignore[no-untyped-def]
    client: TestClient, login, monkeypatch
) -> None:
    """Sprint 4 evaluator observation 3: two overrides racing on the same pre-auth must not both succeed."""
    from src.service import override_service, preauth_service

    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    real_current = preauth_service.current_decision
    stale: dict[str, object] = {}

    def stale_read(conn, preauth_id):  # type: ignore[no-untyped-def]
        # the losing request read the decision stream before the winner committed
        return stale.setdefault("row", real_current(conn, preauth_id))

    monkeypatch.setattr(override_service.preauth_service, "current_decision", stale_read)
    _override(client, login(ADMIN), pre["preauth_id"], {"status": "APPROVED", "reason": "first"})
    body = _override(client, login(ADMIN), pre["preauth_id"], {"status": "APPROVED", "reason": "second"},
                     expected=409)
    assert body["error"]["code"] == "INVALID_PREAUTH_STATE"  # type: ignore[index]
    assert [a["reason"] for a in client.get("/api/admin/audit", headers=login(ADMIN)).json()] == ["first"]
