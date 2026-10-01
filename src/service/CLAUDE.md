# src/service/ — business orchestration

- Services load facts through repositories, call pure domain rules, and persist results inside
  `with conn:` (one transaction per use case).
- Services receive the `Principal` and enforce **data ownership**: a hospital sees only its own
  cases (404 otherwise), and a customer sees only cases of their members. Role checks happen at
  the controller.
- Status changes go through the state machines (`transition()`), never direct assignment. Each one
  appends a timeline event and a notification (AC-09).
- No `fastapi` / `starlette` imports (import-linter contract).
- Settlement code paths must call `assert_settlement_invariant` (the `settlement-cap-check` hook).
  Final-bill paths must call `ensure_bill_within_cap`.
- Logging: event names plus ids/status only. PHI never appears (the `phi-redaction-check` hook).
