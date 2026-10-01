"""AC-06 post-admission updates and AC-08 claim lifecycle through the API (AM-R1 .. AM-R6)."""

import pytest
from fastapi.testclient import TestClient

from tests.api.helpers import decide, submit_preauth
from tests.api.lifecycle import HOSPITAL, INSURER, admitted_case, approved_case, discharged_case, post, settled_case


def _status(client: TestClient, login, case_id: int) -> str:  # type: ignore[no-untyped-def]
    return str(client.get(f"/api/cases/{case_id}", headers=login(HOSPITAL)).json()["status"])


@pytest.mark.ac("AC-08")
def test_ac08_1_happy_path_reaches_closed(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = approved_case(client, login)
    assert _status(client, login, case_id) == "PRE_AUTH"
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/admit", {"admitted_on": "2026-06-16"})
    assert _status(client, login, case_id) == "ADMITTED"
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "90000.00"}, expected=201)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/discharge", {"discharged_on": "2026-06-19"})
    assert _status(client, login, case_id) == "DISCHARGED"
    post(client, login(INSURER), f"/api/cases/{case_id}/settle")
    assert _status(client, login, case_id) == "SETTLED"
    post(client, login(INSURER), f"/api/cases/{case_id}/close")
    assert _status(client, login, case_id) == "CLOSED"


@pytest.mark.ac("AC-08")
def test_ac08_2_dispute_then_close(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = discharged_case(client, login)
    body = post(client, login(INSURER), f"/api/cases/{case_id}/dispute", {"reason": "Bill items need review"})
    assert body["status"] == "DISPUTED"
    assert post(client, login(INSURER), f"/api/cases/{case_id}/close")["status"] == "CLOSED"


@pytest.mark.ac("AC-08")
def test_ac08_disputed_case_can_still_be_settled(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = discharged_case(client, login)
    post(client, login(INSURER), f"/api/cases/{case_id}/dispute", {"reason": "Clarify pharmacy line"})
    assert post(client, login(INSURER), f"/api/cases/{case_id}/settle")["case_status"] == "SETTLED"


@pytest.mark.ac("AC-08")
def test_ac08_3_skipping_admission_raises_invalid_claim_state(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = approved_case(client, login)
    body = post(client, login(HOSPITAL), f"/api/cases/{case_id}/discharge", {"discharged_on": "2026-06-19"},
                expected=409)
    assert body["error"]["code"] == "INVALID_CLAIM_STATE"


@pytest.mark.ac("AC-08")
def test_ac08_5_admit_with_pending_preauth_is_422(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login(HOSPITAL), diagnosis="I21.9")
    body = post(client, login(HOSPITAL), f"/api/cases/{pre['case_id']}/admit", {"admitted_on": "2026-06-16"},
                expected=422)
    assert body["error"]["code"] == "PREAUTH_NOT_APPROVED"


@pytest.mark.ac("AC-08")
def test_ac08_rejected_preauth_case_can_close_but_approved_cannot(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login(HOSPITAL), diagnosis="I21.9")
    decide(client, login(INSURER), pre["preauth_id"], "REJECTED", ["PA-REJECTED-MANUAL"])
    assert post(client, login(INSURER), f"/api/cases/{pre['case_id']}/close")["status"] == "CLOSED"
    other = approved_case(client, login)
    body = post(client, login(INSURER), f"/api/cases/{other}/close", expected=409)  # AM-R6 (amended, FL-001)
    assert body["error"]["code"] == "INVALID_CLAIM_STATE"


@pytest.mark.ac("AC-06")
def test_ac06_1_procedure_added_while_admitted(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = admitted_case(client, login)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/procedures",
         {"procedure_code": "02703ZZ", "description": "Coronary angioplasty"}, expected=201)
    detail = client.get(f"/api/cases/{case_id}", headers=login(HOSPITAL)).json()
    assert [p["procedure_code"] for p in detail["procedures"]] == ["02703ZZ"]


@pytest.mark.ac("AC-06")
def test_ac06_2_final_bill_at_cap_is_accepted(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = admitted_case(client, login, estimate="100000.00")
    body = post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "110000.00"}, expected=201)
    assert (body["amount"], body["version"], body["cap"]) == ("110000.00", 1, "110000.00")


@pytest.mark.ac("AC-06")
def test_ac06_3_final_bill_one_paisa_over_cap_is_rejected_and_not_stored(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = admitted_case(client, login, estimate="100000.00")
    body = post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "110000.01"}, expected=422)
    assert body["error"]["code"] == "BILL_EXCEEDS_CAP"
    assert client.get(f"/api/cases/{case_id}", headers=login(HOSPITAL)).json()["final_bills"] == []


@pytest.mark.ac("AC-06")
def test_ac06_resubmitted_bill_appends_new_version(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = admitted_case(client, login)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "80000.00"}, expected=201)
    post(client, login(HOSPITAL), f"/api/cases/{case_id}/final-bill", {"amount": "85000.00"}, expected=201)
    bills = client.get(f"/api/cases/{case_id}", headers=login(HOSPITAL)).json()["final_bills"]
    assert [(b["version"], b["amount"]) for b in bills] == [(1, "80000.00"), (2, "85000.00")]


@pytest.mark.ac("AC-06")
def test_ac06_4_procedure_on_pre_auth_case_is_409(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = approved_case(client, login)
    body = post(client, login(HOSPITAL), f"/api/cases/{case_id}/procedures",
                {"procedure_code": "GEN-CONSULT", "description": "Consult"}, expected=409)
    assert body["error"]["code"] == "INVALID_CLAIM_STATE"


@pytest.mark.nfr("NFR-08")
def test_settled_case_rejects_bill_and_procedure(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = settled_case(client, login)
    for path, body in ((f"/api/cases/{case_id}/final-bill", {"amount": "1.00"}),
                       (f"/api/cases/{case_id}/procedures", {"procedure_code": "GEN-ICU", "description": "ICU"})):
        assert post(client, login(HOSPITAL), path, body, expected=409)["error"]["code"] == "CASE_SETTLED_IMMUTABLE"


@pytest.mark.nfr("NFR-04")
def test_other_hospital_cannot_touch_case(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = approved_case(client, login)
    post(client, login("sunshine.desk"), f"/api/cases/{case_id}/admit", {"admitted_on": "2026-06-16"}, expected=404)
    assert client.get(f"/api/cases/{case_id}", headers=login("sunshine.desk")).status_code == 404


@pytest.mark.nfr("NFR-04")
def test_case_lists_are_scoped(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    case_id = approved_case(client, login)
    assert [c["case_id"] for c in client.get("/api/cases", headers=login(HOSPITAL)).json()] == [case_id]
    assert client.get("/api/cases", headers=login("sunshine.desk")).json() == []
    assert [c["case_id"] for c in client.get("/api/cases", headers=login("asha.verma")).json()] == [case_id]
    assert client.get("/api/cases", headers=login("kiran.rao")).json() == []
