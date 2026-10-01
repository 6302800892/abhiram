"""Reports math (RP-R1 .. RP-R5). Decimal only; HALF_UP at the documented precision."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping
from decimal import ROUND_HALF_UP, Decimal

HOURS = Decimal("0.01")
RATIO = Decimal("0.0001")
SECONDS_PER_HOUR = Decimal(3600)
TOP_N = 5


def mean_turnaround_hours(pairs: Iterable[tuple[dt.datetime, dt.datetime]]) -> Decimal | None:
    """RP-R1: mean (decided - submitted) in hours, 0.01; None when nothing was decided."""
    seconds = [Decimal(int((decided - submitted).total_seconds())) for submitted, decided in pairs]
    if not seconds:
        return None
    total = sum(seconds, Decimal(0))
    return (total / Decimal(len(seconds)) / SECONDS_PER_HOUR).quantize(HOURS, rounding=ROUND_HALF_UP)


def query_rate(preauths: int, queried: int) -> Decimal:
    """RP-R3: queried / preauths at 0.0001 (0 when no pre-auths)."""
    if preauths == 0:
        return Decimal("0").quantize(RATIO)
    return (Decimal(queried) / Decimal(preauths)).quantize(RATIO, rounding=ROUND_HALF_UP)


def loss_ratio(settled: Decimal, premiums: Decimal) -> Decimal | None:
    """RP-R5: settled / premiums at 0.0001; None (omitted) when there is no premium."""
    if premiums <= 0:
        return None
    return (settled / premiums).quantize(RATIO, rounding=ROUND_HALF_UP)


def average(values: Iterable[Decimal]) -> Decimal | None:
    items = list(values)
    if not items:
        return None
    return (sum(items, Decimal(0)) / Decimal(len(items))).quantize(RATIO, rounding=ROUND_HALF_UP)


def top_diagnoses(counts: Mapping[str, int]) -> list[tuple[str, int]]:
    """RP-R4: top 5 by count desc, ties by code asc."""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TOP_N]
