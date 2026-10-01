"""Operational reports (RP-R1 .. RP-R5): turnaround, settlement volume, query rate, diagnoses, loss ratio."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections import defaultdict
from decimal import Decimal

from src.domain.icd_stub import diagnosis_label
from src.domain.money import ZERO, money_str, to_money
from src.domain.report_metrics import average, loss_ratio, mean_turnaround_hours, query_rate, top_diagnoses
from src.repository import report_repo


def _turnaround(conn: sqlite3.Connection) -> str | None:
    pairs = [
        (dt.datetime.fromisoformat(r["submitted_at"]), dt.datetime.fromisoformat(r["first_decided_at"]))
        for r in report_repo.first_decisions(conn) if r["first_decided_at"] is not None
    ]
    hours = mean_turnaround_hours(pairs)
    return money_str(hours) if hours is not None else None


def _settlement_volume(conn: sqlite3.Connection) -> dict[str, object]:
    amounts = [to_money(a) for a in report_repo.settlement_amounts(conn)]
    return {"count": len(amounts), "total_amount": money_str(sum(amounts, ZERO))}


def _query_rates(conn: sqlite3.Connection) -> list[dict[str, object]]:
    return [
        {"hospital_code": r["hospital_code"], "preauths": r["preauths"], "queried": r["queried"],
         "rate": str(query_rate(r["preauths"], r["queried"]))}
        for r in report_repo.query_counts_by_hospital(conn)
    ]


def _top_diagnoses(conn: sqlite3.Connection) -> list[dict[str, object]]:
    counts = {r["diagnosis_code"]: int(r["n"]) for r in report_repo.diagnosis_counts(conn)}
    return [{"diagnosis_code": code, "label": diagnosis_label(code), "count": n} for code, n in top_diagnoses(counts)]


def _loss_ratios(conn: sqlite3.Connection) -> tuple[list[dict[str, object]], str | None]:
    premiums: dict[str, Decimal] = defaultdict(lambda: ZERO)
    settled: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for r in report_repo.premiums_by_product(conn):
        premiums[r["product_code"]] += to_money(r["premium"])
    for r in report_repo.settled_by_product(conn):
        settled[r["product_code"]] += to_money(r["amount"])
    rows: list[dict[str, object]] = []
    ratios: list[Decimal] = []
    for code in sorted(premiums):
        ratio = loss_ratio(settled[code], premiums[code])
        if ratio is None:
            continue
        ratios.append(ratio)
        rows.append({"product_code": code, "settled_amount": money_str(settled[code]),
                     "premium_total": money_str(premiums[code]), "loss_ratio": str(ratio)})
    avg = average(ratios)
    return rows, (str(avg) if avg is not None else None)


def summary(conn: sqlite3.Connection) -> dict[str, object]:
    by_product, avg = _loss_ratios(conn)
    return {
        "preauth_turnaround_hours": _turnaround(conn),
        "settlement_volume": _settlement_volume(conn),
        "query_rate_by_hospital": _query_rates(conn),
        "top_diagnoses": _top_diagnoses(conn),
        "loss_ratio_by_product": by_product,
        "average_loss_ratio": avg,
    }
