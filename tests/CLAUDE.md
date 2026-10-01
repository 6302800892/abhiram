# tests/ — pytest suites

| Folder | Kind | Rules |
|---|---|---|
| `unit/` | Pure domain and service helpers | No HTTP. Use a temp SQLite DB only when testing repositories or migrations |
| `api/` | Behaviour through HTTP (`TestClient`) | Use the `client` and `login` fixtures from `conftest.py` |
| `architecture/` | Structural rules | See `architecture/CLAUDE.md` |

- **Tag every acceptance test** with `@pytest.mark.ac("AC-NN")` and put `acNN` in the test name.
  Tag NFR tests with `@pytest.mark.nfr("NFR-NN")`. `scripts/ac_trace.py` fails CI on gaps.
- TDD: commit the failing test first (`test: … (red)`), then the code. Save red runs to
  `specs/test_artefacts/`.
- The clock is pinned to 2026-06-15T10:00Z (`conftest.PINNED_NOW`). Seed dates are offsets from
  it.
- Seeded users share the password `Demo@1234` (synthetic). See `seed/seed_data.json` for IDs.
- Coverage: `pytest --cov=src --cov-report=xml` writes `coverage.xml`. The floor is 80 %.
