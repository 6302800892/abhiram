# src/config/ — settings and logging

- `settings.py`: `Settings.from_env()` reads `MEDICARD_*` variables. Never hardcode secrets. The
  token secret defaults to a per-process random value.
- `logging_config.py`: `JsonFormatter` (NFR-06) adds `correlation_id` and `case_id` from context
  vars. `PhiRedactionFilter` (NFR-03) redacts PHI keys.
- To add a PHI field, add it to `PHI_KEYS` **and** to the `phi-redaction-check.sh` hook pattern.
  Record the change in `docs/knowledge-deposits.md`.
- Log with event names and `extra={...}` ids only. See the `phi-safe-logging` skill.
