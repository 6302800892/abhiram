"""Injectable clock so 'today' is deterministic in tests and never read inside rules."""

from __future__ import annotations

import datetime as dt
from typing import Protocol


class Clock(Protocol):
    def now(self) -> dt.datetime: ...

    def today(self) -> dt.date: ...


class SystemClock:
    """Wall clock in UTC."""

    def now(self) -> dt.datetime:
        return dt.datetime.now(dt.UTC)

    def today(self) -> dt.date:
        return self.now().date()


class FixedClock:
    """A clock pinned to a moment; `advance` moves it forward (used by tests and reports)."""

    def __init__(self, moment: dt.datetime) -> None:
        self._moment = moment

    def now(self) -> dt.datetime:
        return self._moment

    def today(self) -> dt.date:
        return self._moment.date()

    def advance(self, delta: dt.timedelta) -> None:
        self._moment = self._moment + delta


def iso(moment: dt.datetime) -> str:
    """Canonical timestamp string (UTC ISO-8601, seconds precision)."""
    return moment.astimezone(dt.UTC).isoformat(timespec="seconds")
