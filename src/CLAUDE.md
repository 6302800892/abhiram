# src/ — MediCard backend (Python 3.12, FastAPI, SQLite)

Package root `src`. Layers (imports flow **down only**; enforced by `lint-imports` + `tests/architecture/test_layering.py`):

| Rank | Package | May import | Never imports |
|---|---|---|---|
| 6 | `src/main.py` | everything | — |
| 5 | `src/api/` (controllers) | service, repository, config, domain | — |
| 4 | `src/service/` | repository, config, domain | api, fastapi |
| 3 | `src/repository/` | config, domain | service, api, fastapi |
| 2 | `src/config/` | domain | repository, service, api |
| 1 | `src/domain/` | stdlib only (no `logging`, `os`, `sqlite3`, pydantic) | everything above |

## Rules for generators
- New business rule → pure function in `src/domain/`, unit-tested first, then call it from a service.
- Services own transactions (`with conn:`); repositories never commit.
- Every new route: role guard alias from `src/api/deps.py` (`HospitalUser`, `AdminUser`, …).
- Money: `src.domain.money` helpers only. Store as TEXT via `money_str`.
- Raise typed errors from `src.domain.exceptions`; never `HTTPException` below the API layer.
- Read the module `CLAUDE.md` of the folder you are editing before writing code.
