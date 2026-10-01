"""Reports summary through the API (RP-R1 .. RP-R6)."""

import datetime as dt

from fastapi.testclient import TestClient

from tests.api.helpers import decide, submit_preauth
from tests.api.lifecycle import settled_case


def test_reports_summary_contains_every_metric(client: TestClient, login, clock) -> None:  # type: ignore[no-untyped-def]
    hospital, insurer = login("cityhosp.desk"), login("adjudicator.priya")
    submit_preauth(client, hospital, diagnosis="K35.8", estimate="40000.00")       # auto-approved, 0 h
    queried = submit_preauth(client, hospital, diagnosis="ZZZ.9", estimate="1000.00")  # auto-queried, 0 h
    manual = submit_preauth(client, hospital, diagnosis="I21.9", estimate="80000.00")
    clock.advance(dt.timedelta(hours=3))
    decide(client, insurer, manual["preauth_id"], "APPROVED", ["PA-APPROVED-MANUAL"])  # 3 h
    settled_case(client, login, bill="90000.00")  # settles 76500.00 on SILVER; decided at +0 h after its submit
    report = client.get("/api/reports/summary", headers=login("admin.sam"))
    assert report.status_code == 200
    body = report.json()
    assert body["preauth_turnaround_hours"] == "0.75"  # (0 + 0 + 3 + 0) / 4
    assert body["settlement_volume"] == {"count": 1, "total_amount": "76500.00"}
    city = next(h for h in body["query_rate_by_hospital"] if h["hospital_code"] == "CITYHOSP")
    assert (city["preauths"], city["queried"], city["rate"]) == (4, 1, "0.2500")
    assert body["top_diagnoses"][0] == {"diagnosis_code": "I21.9", "label": "Acute myocardial infarction", "count": 2}
    silver = next(p for p in body["loss_ratio_by_product"] if p["product_code"] == "SILVER")
    assert (silver["settled_amount"], silver["premium_total"], silver["loss_ratio"]) == ("76500.00", "36000.00",
                                                                                         "2.1250")
    assert body["average_loss_ratio"] == "1.0625"  # (2.1250 + GOLD 0.0000) / 2
    assert queried["status"] == "QUERY_RAISED"


def test_reports_on_empty_data(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    body = client.get("/api/reports/summary", headers=login("adjudicator.priya")).json()
    assert body["preauth_turnaround_hours"] is None
    assert body["settlement_volume"] == {"count": 0, "total_amount": "0.00"}
    assert body["top_diagnoses"] == []


def test_rp_ac5_hospital_cannot_read_reports(client: TestClient, login) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/api/reports/summary", headers=login("cityhosp.desk")).status_code == 403
