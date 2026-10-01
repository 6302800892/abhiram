"""NFR-03 PHI redaction and NFR-06 structured JSON log lines."""

import io
import json
import logging

import pytest

from src.config.logging_config import JsonFormatter, PhiRedactionFilter, bind_case_id, bind_correlation_id


def _capture() -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(PhiRedactionFilter())
    logger = logging.getLogger("medicard.test.capture")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger, stream


@pytest.mark.nfr("NFR-06")
def test_log_line_is_json_with_correlation_and_case_ids() -> None:
    logger, stream = _capture()
    bind_correlation_id("corr-xyz")
    bind_case_id(42)
    logger.info("preauth.submitted", extra={"status": "PENDING"})
    record = json.loads(stream.getvalue().strip())
    assert record["message"] == "preauth.submitted"
    assert record["correlation_id"] == "corr-xyz"
    assert record["case_id"] == 42
    assert record["status"] == "PENDING"
    assert record["level"] == "INFO"
    assert record["timestamp"].endswith("+00:00")  # UTC, same as API timestamps


@pytest.mark.nfr("NFR-06")
def test_uvicorn_server_logs_are_json_too() -> None:
    """Sprint 1 evaluator note: uvicorn's own error/access lines must also be structured JSON."""
    import logging.config

    from src.config.logging_config import uvicorn_log_config

    config = uvicorn_log_config("INFO")
    logging.config.dictConfig(config)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        handlers = logging.getLogger(name).handlers
        assert handlers and all(isinstance(h.formatter, JsonFormatter) for h in handlers), name
    stream = io.StringIO()
    logging.getLogger("uvicorn.access").handlers[0].setStream(stream)  # type: ignore[attr-defined]
    logging.getLogger("uvicorn.access").info("GET /health 200", extra={"color_message": "[36mGET[0m"})
    line = json.loads(stream.getvalue())
    assert line["logger"] == "uvicorn.access"
    assert "color_message" not in line  # terminal-only ANSI copy of the message is dropped


@pytest.mark.nfr("NFR-03")
def test_phi_fields_in_extra_are_redacted() -> None:
    logger, stream = _capture()
    secret_note = "patient reports chest pain since Tuesday"
    logger.info("debug.dump", extra={"clinical_notes": secret_note, "diagnosis_code": "I21.9"})
    out = stream.getvalue()
    assert secret_note not in out
    assert "I21.9" not in out
    assert json.loads(out)["clinical_notes"] == "[REDACTED]"
