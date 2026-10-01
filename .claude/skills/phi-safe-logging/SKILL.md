---
name: phi-safe-logging
description: PHI-safe structured logging for MediCard (NFR-03, NFR-06). Load before adding any logger call, middleware, or exception handler.
---

# PHI-Safe Logging

## PHI fields (never logged in plaintext)
`diagnosis_code`, `diagnosis`, `diagnosis_label`, `procedure_code`, `procedure`, `description`,
`clinical_notes`, `health_history`, `date_of_birth`, `response_note`.

## How to log
```python
logger = logging.getLogger("medicard.preauth")
logger.info("preauth.submitted", extra={"case_id": case_id, "preauth_id": pid, "status": status})
```
- Use event-style messages with `extra=` fields. Never put f-string payloads in the message.
- `PhiRedactionFilter` in `src/config/logging_config.py` replaces any PHI key in `extra` with
  `"[REDACTED]"`. It is defence in depth, not permission to pass PHI.
- `JsonFormatter` emits `timestamp, level, logger, message, correlation_id, case_id` plus the
  safe extras.
- `correlation_id` comes from the `X-Correlation-ID` header or a generated UUID4 (middleware).
  `case_id` is bound with `bind_case_id(case_id)`.

## Enforcement
- The `phi-redaction-check.sh` hook blocks a `logger.*(` / `logging.*(` line that mentions a PHI
  field name.
- The NFR-03 test submits a pre-auth with a distinctive clinical note and asserts it is absent from
  captured log output.
