# tests/architecture/ — structural rules as tests (NFR-08)

Owned by `medicard-archtest-author-agent`. These tests inspect structure (AST, routes, schema),
not business outcomes.

| Test | Rule |
|---|---|
| `test_layering.py` | One-way layer imports; domain imports no framework or I/O |
| `test_controllers_guarded.py` | Every `/api` route has a role guard except the 2 public ones |
| `test_money_fixed_point.py` | No `float` in domain, service or repository; no REAL money columns |
| `test_append_only.py` | Append-only tables have UPDATE and DELETE abort triggers; migrations are contiguous |
| `test_settled_cases_immutable.py` | Mutations on a SETTLED case raise (sprint 3) |
| `test_bill_cap_enforced.py` | Final-bill paths call the cap rule (sprint 3) |
| `test_override_audited.py` | Override route requires ADMIN and writes an audit record (sprint 4) |

import-linter contracts in `pyproject.toml` are the import-graph counterpart (`poetry run lint-imports`).
