"""Reports math (RP-R1 .. RP-R5): Decimal, deterministic rounding."""

import datetime as dt
from decimal import Decimal

from src.domain.report_metrics import average, loss_ratio, mean_turnaround_hours, query_rate, top_diagnoses

T0 = dt.datetime(2026, 6, 15, 8, 0, tzinfo=dt.UTC)


def test_rp_ac1_mean_turnaround_hours() -> None:
    pairs = [(T0, T0 + dt.timedelta(hours=2)), (T0, T0 + dt.timedelta(hours=4))]
    assert mean_turnaround_hours(pairs) == Decimal("3.00")


def test_turnaround_none_when_nothing_decided() -> None:
    assert mean_turnaround_hours([]) is None


def test_turnaround_rounds_to_hundredths() -> None:
    assert mean_turnaround_hours([(T0, T0 + dt.timedelta(minutes=20))]) == Decimal("0.33")


def test_rp_ac2_query_rate() -> None:
    assert query_rate(4, 1) == Decimal("0.2500")
    assert query_rate(3, 1) == Decimal("0.3333")
    assert query_rate(0, 0) == Decimal("0.0000")


def test_rp_ac3_loss_ratio() -> None:
    assert loss_ratio(Decimal("100000.00"), Decimal("200000.00")) == Decimal("0.5000")


def test_loss_ratio_none_without_premium() -> None:
    assert loss_ratio(Decimal("10.00"), Decimal("0.00")) is None


def test_average_of_ratios() -> None:
    assert average([Decimal("0.5000"), Decimal("0.2500")]) == Decimal("0.3750")
    assert average([]) is None


def test_rp_ac4_top_five_by_count_then_code() -> None:
    counts = {"K35.8": 3, "J18.9": 3, "I21.9": 5, "O80": 1, "S52.5": 2, "N20.0": 1}
    assert top_diagnoses(counts) == [("I21.9", 5), ("J18.9", 3), ("K35.8", 3), ("S52.5", 2), ("N20.0", 1)]
