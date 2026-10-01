---
name: settlement-audit
description: Audit MediCard money paths — Decimal-only arithmetic, bill cap, settlement invariant, append-only settlement rows — and report PASS/FAIL per rule (AC-06, AC-07, NFR-01, NFR-02, NFR-08).
argument-hint: "[case_id]  (optional: also re-verify one persisted settlement)"
---

# /settlement-audit

Use the `medicard-settlement-agent` with the `settlement-calculator` skill.

## Static checks
1. `grep -rnE '\bfloat\(|: *float\b' src/domain src/service src/repository` must return nothing (NFR-01).
2. Every file matching `def calculate_settlement|admissible -` contains `assert_settlement_invariant`.
3. `src/service/case_service.py::submit_final_bill` calls `ensure_bill_within_cap`.
4. `migrations/*.sql` define `trg_settlements_no_update` and `trg_settlements_no_delete`.

## Dynamic checks
5. `poetry run pytest -q tests/unit/test_settlement_calculator.py tests/unit/test_bill_rules.py tests/api/test_ac07_settlement.py tests/architecture/test_settled_cases_immutable.py`
6. If `$ARGUMENTS` has a case id, recompute that case's breakdown from `final_bills` and the
   pre-auth decision with `src.domain.settlement_calculator.calculate_settlement`. Compare it with
   the persisted `settlements` row field by field.

## Report
Write `specs/reviews/settlement-audit.md` with one `[PASS]`/`[FAIL]` line per check and a final
`VERDICT: PASS|FAIL`. A FAIL on check 2 or 3 is a release blocker.
