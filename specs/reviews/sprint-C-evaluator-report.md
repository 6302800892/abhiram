# Evaluator Report — Group C (Sprint 3)

Date: 2026-10-01T16:05:00Z
VERDICT: FAIL

Scope: `sprint-contracts/group-C.json` (E3-S1..E3-S4; F020–F028). Specs: `specs/admission_spec.md`,
`specs/settlement_spec.md`, `specs/app_spec.md §6.2`, NFR-02/03/04/08.
Environment: local mode, `uvicorn src.main:create_app --factory --port 8012`, fresh DB
`$TEMP/medicard-eval-C.db`, `MEDICARD_PBKDF2_ITERATIONS=1000`, no frontend. Health check
`GET /health` -> 200 `{"status":"ok","service":"medicard"}` on attempt 1. Server stopped after the
run. No source, test, spec, config or `features.json` file was modified. No git commands were run.

Two failures:
1. **C-01 (major):** the bill cap and the settlement use the *current* coverage-rule version instead
   of the version the pre-auth recorded (brief §8.2 #12).
2. **C-02 (minor):** a disallowed PRE_AUTH -> CLOSED returns 422 `PREAUTH_NOT_REJECTED` instead of
   409 `INVALID_CLAIM_STATE`.

## API Checks

Every contract check ran live against port 8012. Main case = CASE-000002: SILVER v1, pre-auth
I21.9 for 100000.00, approved manually.

- [PASS] api-201 POST /api/cases/2/admit (APPROVED pre-auth) -> 200, status ADMITTED
- [PASS] api-202 POST /api/cases/3/admit (PENDING pre-auth) -> 422 PREAUTH_NOT_APPROVED; case stays PRE_AUTH
- [PASS] api-203 POST /api/cases/2/discharge while PRE_AUTH -> 409 INVALID_CLAIM_STATE
- [PASS] api-204 POST /api/cases/2/procedures while ADMITTED -> 201; procedure PCI-01 is listed on GET /api/cases/2
- [PASS] api-205 POST /api/cases/2/final-bill 110000.00 (exactly at the cap) -> 201 `{version:1, cap:"110000.00"}`
- [PASS] api-206 POST /api/cases/2/final-bill 110000.01 -> 422 BILL_EXCEEDS_CAP; `final_bills` still `[]`
- [PASS] api-207 POST /api/cases/2/settle (latest bill v2 = 90000.00) -> 200: admissible 90000.00, deductible 5000.00, copay 8500.00, settlement 76500.00, `payment_reference` PAYSTUB-2-1; case SETTLED
- [PASS] api-208 GET /api/customers/me/coverage -> remaining_sum_insured 500000.00 -> 423500.00 (down by 76500.00)
- [PASS] api-209 POST /api/cases/2/close (SETTLED, insurer) -> 200 CLOSED
- [PASS] api-210 case 6: DISCHARGED -> DISPUTED (200) -> CLOSED (admin, 200)
- [PASS] api-211 GET /api/cases/2/timeline: the hospital, customer and insurer responses are byte-identical and ordered; sunshine.desk -> 404, kiran.rao -> 404
- [PASS] api-212 second POST /api/cases/2/settle -> 409 CASE_SETTLED_IMMUTABLE
- [PASS] api-213 GET /api/customers/me/notifications for case 2: PENDING, APPROVED, ADMITTED, DISCHARGED, SETTLED (then CLOSED). One STUB notification per transition, in ascending time order
- [PASS] api-214 GET /api/cases/2/settlement -> 200 for asha.verma, cityhosp.desk, adjudicator.priya and admin.sam, with pre-auth amount, final bill, deductible, co-pay and paid amount

## Adversarial Probes

### State machine (AM-R1, §6.2)
- [PASS] PRE_AUTH: procedures, final-bill, discharge and dispute -> 409 INVALID_CLAIM_STATE; settle -> 409
- [FAIL] **C-02**: close on PRE_AUTH whose pre-auth is APPROVED -> **422 PREAUTH_NOT_REJECTED** (expected 409 INVALID_CLAIM_STATE). Same result for a PENDING pre-auth (case 3). The case does stay PRE_AUTH.
- [PASS] PRE_AUTH (REJECTED pre-auth) -> CLOSED by admin -> 200; hospital close -> 403
- [PASS] ADMITTED: admit again, settle, dispute, close (insurer and admin) -> 409 INVALID_CLAIM_STATE
- [PASS] DISCHARGED: admit, discharge, close and procedures -> 409 INVALID_CLAIM_STATE
- [PASS] DISPUTED: dispute, discharge, admit, procedures and final-bill -> 409 INVALID_CLAIM_STATE; settle without a bill -> 422 FINAL_BILL_REQUIRED; DISPUTED -> SETTLED with a bill of 50000.00 -> 40500.00
- [PASS] SETTLED: final-bill and procedures -> 409 CASE_SETTLED_IMMUTABLE; admit, discharge and dispute -> 409 INVALID_CLAIM_STATE; case stays SETTLED with 2 bills and 1 procedure
- [PASS] CLOSED: close, settle, final-bill, dispute and admit -> 409 INVALID_CLAIM_STATE

### Admission guards
- [PASS] admit with REJECTED pre-auth -> 422 PREAUTH_NOT_APPROVED
- [PASS] admit with PARTIALLY_APPROVED 80000.00 -> 200; cap 88000.00 (88000.01 -> 422, 88000.00 -> 201)
- [PASS] other-hospital admit and final-bill -> 404; insurer admit -> 403

### Bill and settlement
- [PASS] invalid amounts "0", "-5.00", "abc", "100.001" and the JSON number 110000.0 -> 422; nothing stored
- [PASS] resubmission on DISCHARGED -> 201 version 2; the case lists versions [1, 2]; settlement used v2 (90000.00)
- [PASS] settle DISCHARGED without a bill -> 422 FINAL_BILL_REQUIRED; case stays DISCHARGED
- [PASS] bill 3000.00 below deductible 5000.00 -> deductible 3000.00, copay 0.00, settlement 0.00; remaining sum insured unchanged
- [PASS] bill 6000.05 -> copay 100.01 (HALF_UP), settlement 900.04
- [PASS] settle by hospital, admin or customer -> 403
- [PASS] dispute by hospital -> 403; dispute with no reason or a blank reason -> 422

### Visibility, notifications, PHI
- [PASS] sunshine.desk and kiran.rao on GET case, timeline and settlement -> 404
- [PASS] 47 notifications across 11 cases: one per status change, none for rejected attempts, ascending order. No diagnosis code (I21.9), label ("Acute myocardial infarction") or procedure text in any message. kiran.rao sees 0; a hospital calling the endpoint gets 403
- [PASS] server log (311 lines) has 0 matches for I21.9, myocardial, Acute, Coronary, stenting, angioplasty or PCI-01, and no tracebacks

### Append-only (NFR-02), run on a copy of the DB
- [PASS] UPDATE and DELETE on settlements, final_bills, case_events, notifications and procedures -> `IntegrityError: append-only: <table>`; row counts unchanged

### Rule change mid-cycle (brief §8.2 #12)
Expected result, from the specs:
- PA-R3: the pre-auth records the `coverage_rule_version` in force.
- PA-R4 and PA-R6: the pre-auth is evaluated against *that* version.
- NA-R4: old versions are kept and never change.
- ST-R1: the cap is built from the *pre-auth amount*.

So a pre-auth decided under SILVER v1 must keep the v1 buffer of 10 %, which gives cap 110000.00. A bill that was accepted against a cap must also be settled against that same cap. Otherwise the cap rule (ST-R1) and the settlement calculation (ST-R2) disagree for the same case.

- [PASS] admin publishes SILVER v2 (all v1 fields, `buffer_pct` "5") -> 201 version 2; v1 unchanged (buffer 10)
- [PASS] pre-auth 1 still reports `rule_version {SILVER, 1}` after the publish
- [FAIL] **C-01a**: case 1 (approved 100000.00 under v1, admitted before the publish). POST final-bill 108000.00 after the publish -> **422 BILL_EXCEEDS_CAP, `details.cap` "105000.00"**. Expected 201 with cap 110000.00. The follow-up settle then returned 422 FINAL_BILL_REQUIRED, because no bill could be stored.
- [FAIL] **C-01b**: case 10. Bill 108000.00 was accepted under v1 with `cap: "110000.00"`. After the v2 publish, settle -> 200 with `buffer_pct "5", cap "105000.00", admissible "105000.00", copay "10000.00", settlement_amount "90000.00"`. Expected buffer 10, cap 110000.00, admissible 108000.00, copay 10300.00, settlement 92700.00. The hospital was underpaid by 2700.00, and the persisted settlement row is immutable.
- [PASS] a new pre-auth created after the publish records version 2 and gets cap 105000.00 (105000.01 -> 422, 105000.00 -> 201)

## Performance Checks

- [PASS] POST /api/cases/{id}/settle: 48 ms in the scripted run; curl `time_total` on cases 12–16 = 22, 21, 22, 29, 25 ms. All under the 500 ms limit.

## Architecture Checks

- [PASS] `tests/architecture/test_settled_cases_immutable.py` and `tests/architecture/test_bill_cap_enforced.py` exist and pass
- [PASS] append-only triggers on case_events, procedures, final_bills, settlements and notifications, verified live (above)
- [PASS] money: settlement math is Decimal (HALF_UP probe above); `tests/unit/test_settlement_calculator.py` passes (float -> TypeError)
- [PASS] `pytest -q -p no:cacheprovider` -> 414 passed, 1 skipped (`test_layering.py:37` "not a layered module")
- [PASS] `lint-imports` -> 3 contracts kept, 0 broken
- [PASS] `mypy` -> no issues in 65 source files
- [PASS] `ruff check .` -> all checks passed
- [PASS] `bash scripts/test-hooks.sh` -> exit 0, all cases ok
- Note: the green suite does not cover C-01. No test publishes a new coverage-rule version between pre-auth approval and bill or settlement.

## Playwright Checks

- None. This contract is API-only (`playwright_checks: []`).

## Features Updated

The evaluator was told not to modify `features.json`, so these are the recommended values:

- F020: FAIL (api: PRE_AUTH -> CLOSED with a non-REJECTED pre-auth returns 422 PREAUTH_NOT_REJECTED, expected 409 INVALID_CLAIM_STATE)
- F021: PASS
- F022: FAIL (api: bill 108000.00 within the v1 cap of 110000.00 is rejected after a v2 publish; the cap is taken from the current rule version, not the pre-auth's)
- F023: PASS
- F024: FAIL (api: settlement uses the current rule's buffer; case 10 settled 90000.00 instead of 92700.00)
- F025: PASS
- F026: PASS
- F027: PASS
- F028: PASS

## Evidence

- Drivers (scratchpad): `evalc.py`, `mainC.py`, `probesC.py`, `rulechangeC.py`, `notif.py`, `dbC.py`, `perfprep.py`
- Server log: `$TEMP/medicard-eval-C.log`. DB: `$TEMP/medicard-eval-C.db`. Trigger test copy: `$TEMP/medicard-eval-C-copy.db`
- C-01a response: `{"error":{"code":"BILL_EXCEEDS_CAP","message":"final bill exceeds pre_auth_amount + 5% buffer","details":{"cap":"105000.00","final_bill":"108000.00"}}}`
- C-01b response: `{"case_id":10,"case_status":"SETTLED","pre_auth_amount":"100000.00","buffer_pct":"5","cap":"105000.00","final_bill":"108000.00","admissible":"105000.00","deductible":"5000.00","copay":"10000.00","settlement_amount":"90000.00","payment_reference":"PAYSTUB-10-1"}`. The same case's bill v1 was accepted earlier with `"cap":"110000.00"`.
- Timeline for case 2 (9 events): PREAUTH_STATUS null->PENDING, PENDING->APPROVED, CASE_STATUS PRE_AUTH->ADMITTED, PROCEDURE, FINAL_BILL v1, ADMITTED->DISCHARGED, FINAL_BILL v2, DISCHARGED->SETTLED, SETTLED->CLOSED

## Observations

- C-01 also affects deductible and co-pay: settlement and the cap read whichever rule version is current, not the pre-auth's `rule_version`. Only `buffer_pct` changed in this probe. Fixing it means resolving the coverage rules from the pre-auth's recorded version in both bill-cap validation and settlement.
- C-02: `PREAUTH_NOT_REJECTED` appears nowhere in the specs. AM-R1 and §6.2 say a disallowed transition raises InvalidClaimStateException -> 409 INVALID_CLAIM_STATE. The guard itself works: the case is not closed. Only the status and error code differ.
- The timeline shows procedure codes and bill amounts to the customer, but not procedure descriptions or the diagnosis.
- An admin can close a case: allowed by AM-R6.
- Notifications are not sent for PROCEDURE or FINAL_BILL events. This matches AM-R7, which covers status transitions only.
