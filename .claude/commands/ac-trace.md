---
name: ac-trace
description: Report acceptance-criteria traceability — every AC-NN in specs/app_spec.md mapped to its tagged tests, with gaps highlighted. Fails if any AC has zero tests.
---

# /ac-trace — Acceptance-Criteria Traceability

1. Extract the AC list:
   `grep -oE '^\| AC-[0-9]{2}' specs/app_spec.md | tr -d '| ' | sort -u`
2. For each `AC-NN`, collect the tests that reference it:
   - pytest: `grep -rlE 'ac\("AC-NN"|AC-NN|acNN' tests/`
   - Playwright: `grep -rl 'AC-NN' frontend/e2e/`
3. Run the tagged tests: `poetry run pytest -q -m ac` (the `ac` marker is registered in `pyproject.toml`).
4. Write `specs/reviews/ac-trace.md`:

   | AC | Spec | Test files | # tests | Status |
   |---|---|---|---|---|

   Status is `COVERED` (≥ 1 test, all passing), `FAILING` or `GAP` (0 tests).
5. Print a summary. If any AC is `GAP` or `FAILING`, end with `VERDICT: FAIL`. Otherwise end with
   `VERDICT: PASS`.

Programmatic equivalent (used in CI): `poetry run python scripts/ac_trace.py`.
