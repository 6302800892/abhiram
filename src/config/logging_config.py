"""Structured JSON logging with correlation/case ids (NFR-06) and PHI redaction (NFR-03)."""

from __future__ import annotations

import contextvars
import datetime as dt
import json
import logging
from typing import Any

PHI_KEYS = frozenset(
    {
        "diagnosis", "diagnosis_code", "diagnosis_label", "procedure", "procedure_code", "description",
        "clinical_notes", "health_history", "date_of_birth", "response_note",
    }
)
REDACTED = "[REDACTED]"
_STANDARD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message", "asctime", "color_message",  # uvicorn adds an ANSI-coloured duplicate of the message
}

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)
_case_id: contextvars.ContextVar[int | None] = contextvars.ContextVar("case_id", default=None)


def bind_correlation_id(value: str | None) -> None:
    _correlation_id.set(value)


def bind_case_id(value: int | None) -> None:
    _case_id.set(value)


def current_correlation_id() -> str | None:
    return _correlation_id.get()


class PhiRedactionFilter(logging.Filter):
    """Replace any PHI-named attribute on a record with [REDACTED] (defence in depth)."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in PHI_KEYS:
            if key in record.__dict__:
                setattr(record, key, REDACTED)
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger, message, correlation_id, case_id, extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": dt.datetime.fromtimestamp(record.created, dt.UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": _correlation_id.get(),
            "case_id": getattr(record, "case_id", None) or _case_id.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = REDACTED if key in PHI_KEYS else value
        if record.exc_info:
            payload["exception"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, default=str)


def uvicorn_log_config(level: str = "INFO") -> dict[str, Any]:
    """dictConfig for uvicorn so server error/access lines are JSON as well (NFR-06)."""
    handler = {"class": "logging.StreamHandler", "formatter": "json", "filters": ["phi"]}
    logger = {"handlers": ["default"], "level": level, "propagate": False}
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": f"{__name__}.JsonFormatter"}},
        "filters": {"phi": {"()": f"{__name__}.PhiRedactionFilter"}},
        "handlers": {"default": handler},
        "loggers": {"uvicorn": logger, "uvicorn.error": logger, "uvicorn.access": logger},
    }


def configure_logging(level: str = "INFO") -> None:
    """Install the JSON handler on the 'medicard' logger tree (idempotent)."""
    root = logging.getLogger("medicard")
    root.setLevel(level)
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.addFilter(PhiRedactionFilter())
        root.addHandler(handler)
    root.propagate = True
