# Evaluator Report — Group C (Sprint 3), round 2 (fix loop FL-001)

Date: 2026-10-01

VERDICT: PASS

Contract: `sprint-contracts/group-C.json`. Round 1: `specs/reviews/sprint-C-evaluator-report.md` and `specs/reviews/eval-failures-C.json` (C-01a, C-01b, C-02).
I started a live server: uvicorn `src.main:create_app` on 127.0.0.1:8013, fresh DB `$TEMP/medicard-eval-C2.db`, `MEDICARD_PBKDF2_ITERATIONS=1000`, no frontend dist. `GET /health` returned 200 `{"status":"ok","service":"medicard"}`.
Users: cityhosp.desk, adjudicator.priya, admin.sam (Demo@1234). Member MBR-1001 / POL-SLV-0001, diagnosis I21.9.

## Re-verified failures

Setup: I created cases A, B, C and D under SILVER v1 (buffer 10, deductible 5000.00, co-pay 10). For each one, `POST /api/preauths` returned 201. The manual decision `{"status":"APPROVED","reason_codes":["PA-APPROVED-MANUAL"]}` gave APPROVED 100000.00 with `rule_version {SILVER, 1}`. Each case was then admitted (200).

To publish SILVER v2, I copied every field of v1 from `GET /api/admin/products/SILVER/coverage-rules` and set `buffer_pct "5"`. The publish returned 201 with version 2.

| ID | Check | Expected | Observed | Result |
|---|---|---|---|---|
| C-01a | Case A (v1 pre-auth, bill not yet filed). Publish v2, then `POST /final-bill {"amount":"108000.00"}` | 201, cap 110000.00 | 201 `{"case_id":1,"version":1,"amount":"108000.00","cap":"110000.00"}`. Pre-auth still reports `rule_version {SILVER,1}` | PASS |
| C-01b | Case B: bill 108000.00 under v1 (201, cap 110000.00). Publish v2, discharge, settle | buffer 10, cap 110000.00, admissible 108000.00, deductible 5000.00, copay 10300.00, settlement 92700.00 | 200 `buffer_pct "10", cap "110000.00", final_bill "108000.00", admissible "108000.00", deductible "5000.00", copay "10300.00", settlement_amount "92700.00", payment_reference PAYSTUB-2-1` | PASS |
| C-01b (deductible/co-pay variant) | Publish SILVER v3 with buffer 5, deductible "0.00", copay_pct "0" (201, version 3). Then settle case C (bill 108000.00 filed under v1) and case A (bill filed after v2) | v1 terms: deductible 5000.00, co-pay 10 %, settlement 92700.00 | Case C: 200 buffer 10 / cap 110000.00 / admissible 108000.00 / deductible 5000.00 / copay 10300.00 / 92700.00. Case A: the same values | PASS |
| C-02 | `POST /api/cases/{id}/close` on a PRE_AUTH case with a PENDING pre-auth (insurer) | 409 INVALID_CLAIM_STATE | 409 `{"error":{"code":"INVALID_CLAIM_STATE","message":"case cannot move from PRE_AUTH to CLOSED (pre-auth not rejected)"}}`. Case stays PRE_AUTH | PASS |
| C-02 | Same check with an APPROVED pre-auth (insurer, then admin) | 409 INVALID_CLAIM_STATE | 409 INVALID_CLAIM_STATE for both roles. Case stays PRE_AUTH | PASS |

## Regression checks

| Check | Observed | Result |
|---|---|---|
| A new pre-auth created after v2 records v2 | Case E pre-auth `rule_version {SILVER, 2}` | PASS |
| v2 pre-auth, bill 105000.01 | 422 BILL_EXCEEDS_CAP, details cap "105000.00" | PASS |
| v2 pre-auth, bill 105000.00 (cap boundary) | 201 cap "105000.00" | PASS |
| Case E is a v2 pre-auth. Settle it after v3 was published | 200: buffer 5, cap 105000.00, admissible 105000.00, deductible 5000.00, copay 10000.00, settlement 90000.00 (v2 terms, not v3) | PASS |
| A new pre-auth after v3 uses v3 (case F, 50000.00, bill 50000.00) | Pre-auth rule_version 3. Bill cap 52500.00. Settlement: buffer 5, deductible 0.00, copay 0.00, settlement 50000.00 | PASS |
| Happy path: case D, bill 90000.00 under v1, settled after v3 | 200: admissible 90000.00, deductible 5000.00, copay 8500.00, settlement 76500.00 | PASS |
| Settle twice (case B) | 409 CASE_SETTLED_IMMUTABLE | PASS |
| Final bill on a settled case (case A) | 409 CASE_SETTLED_IMMUTABLE | PASS |
| Close a PRE_AUTH case whose pre-auth is REJECTED (PA-REJECTED-MANUAL) | 200 status CLOSED | PASS |
| Close a SETTLED case (case B) | 200 CLOSED | PASS |
| v1 is unchanged after the v2 and v3 publishes (NA-R4) | `GET` returns v1 exactly as before | PASS |
| Timeline for case A | PREAUTH null→PENDING, PENDING→APPROVED, CASE PRE_AUTH→ADMITTED, FINAL_BILL, ADMITTED→DISCHARGED, DISCHARGED→SETTLED | PASS |
| Server log | 0 tracebacks or errors | PASS |

Side observation (not a defect): the policy's remaining sum insured dropped after the 100000-scale settlements. A later 100000.00 estimate returned 422 INVALID_APPROVED_AMOUNT ("estimate exceeds the policy cap 55400.00; approve partially up to the cap"), so the later probes used smaller estimates.

## Spec verification

- `specs/settlement_spec.md` ST-R1 now says that `buffer_pct` comes from "the coverage-rule version recorded on the pre-auth (PA-R3), never from the product's current version".
- ST-R2 now says that the deductible `D` and `copay_pct` `c` come from "that same recorded rule version (so a bill is settled against the cap it was accepted under)".
- The settlement_spec change log has a 2026-10-01 entry that cites failure C-01 and FL-001 (`docs/fix-loops/FL-001-rule-version-mid-cycle.md`). Confirmed.
- `specs/admission_spec.md` AM-R6 now says: "Closing a PRE_AUTH case whose pre-auth is not REJECTED is a disallowed transition: 409 `INVALID_CLAIM_STATE`". Its change log has a 2026-10-01 entry citing C-02 and the undocumented `PREAUTH_NOT_REJECTED`. Confirmed.
- The live behaviour above matches the amended text.

## Gates

| Gate | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | 421 passed, 1 skipped, 1 warning (Starlette httpx deprecation), exit 0. `tests/api/test_fix_loop_rule_version.py`: 4 passed |
| `.venv/Scripts/lint-imports.exe` | 3 contracts kept, 0 broken |
| `.venv/Scripts/python.exe -m mypy` | Success: no issues found in 65 source files |
| `.venv/Scripts/ruff.exe check .` | All checks passed |
| `bash scripts/test-hooks.sh` | 13 ok, 0 not-ok, exit 0 |

## Features Updated

The evaluator was told not to modify `features.json`, so these are the recommended values:

- F020: PASS (round 1 failure C-02 is fixed. Closing a PRE_AUTH case with a PENDING or APPROVED pre-auth returns 409 INVALID_CLAIM_STATE)
- F021: PASS
- F022: PASS (C-01a is fixed. The cap comes from the pre-auth's recorded version. The v2 boundary of 105000.00 is accepted)
- F023: PASS (v2 bill of 105000.01 returns 422 BILL_EXCEEDS_CAP)
- F024: PASS (C-01b is fixed. The worked example still gives 76500.00. Mid-cycle cases settle at 92700.00 on v1 terms)
- F025: PASS (carried from round 1. Not re-probed live; covered by the passing suite)
- F026: PASS (settling twice returns 409 CASE_SETTLED_IMMUTABLE)
- F027: PASS (carried from round 1. Not re-probed live; covered by the passing suite)
- F028: PASS (carried from round 1. Not re-probed live; covered by the passing suite)

## Evidence

- Drivers (scratchpad): `evalc2.py` (port 8013 helpers), `r2.py` (C-01a/C-01b/v2/v3 regressions), `r2b.py` (v3 pre-auth, C-02, close checks), `r2c.py` (immutability, timeline). Results: `results_r2.json`, `results_r2b.json`.
- Server log: `$TEMP/medicard-eval-C2.log` (no tracebacks). DB: `$TEMP/medicard-eval-C2.db`. The server was stopped after the run.
- C-01a response: `201 {"case_id":1,"version":1,"amount":"108000.00","cap":"110000.00"}`
- C-01b response (case 2): `{"case_id":2,"case_status":"SETTLED","pre_auth_amount":"100000.00","buffer_pct":"10","cap":"110000.00","final_bill":"108000.00","admissible":"108000.00","deductible":"5000.00","copay":"10300.00","settlement_amount":"92700.00","payment_reference":"PAYSTUB-2-1"}`
- C-01b v3 variant (cases 3 and 1): the same values with settlement 92700.00, after v3 set deductible 0.00 and co-pay 0
- C-02 response: `409 {"error":{"code":"INVALID_CLAIM_STATE","message":"case cannot move from PRE_AUTH to CLOSED (pre-auth not rejected)"}}`
- No git commands were run. No source, tests, specs, config or features.json were modified.
