# Evaluator Report — Group B (Sprint 2)

Date: 2026-10-01T15:50:00Z
VERDICT: PASS

Contract: `sprint-contracts/group-B.json` (stories E2-S1..E2-S4, features F012–F019) · Specs: `specs/preauth_spec.md`,
`specs/adjudication_spec.md` AD-R1..AD-R5 (override AC-10 out of scope) · NFRs from `specs/app_spec.md`.

**Environment:** port 8000 is held by an unrelated app, so MediCard ran on **http://127.0.0.1:8011** with a fresh
throwaway DB (`$TEMP/medicard-eval-B.db`), `MEDICARD_PBKDF2_ITERATIONS=1000`, `MEDICARD_FRONTEND_DIST=""`, stderr to
`$TEMP/medicard-eval-B.log`. The first health check returned 200 `{"status":"ok","service":"medicard"}`. Server UTC
date = 2026-10-01, and that date was used as `expected_admission_date`. Every request was sent with curl, and money
was sent as JSON strings. The evaluator changed no source, test, spec, config or features.json file and ran no git
command.

## API Checks

Contract checks:

- [PASS] api-101 POST /api/preauths MBR-1001/POL-SLV-0001, I21.9, "80000.00" (with clinical_notes marker) → 201 `PENDING`, decisions `[PENDING/PA-SUBMITTED, PENDING/PA-MANUAL-REVIEW]`, `case_status: PRE_AUTH`, `rule_version {SILVER, 1}`
- [PASS] api-102 POST /api/preauths estimated_cost "0" → 422 `INVALID_ESTIMATED_COST`
- [PASS] api-103 K35.8 "40000.00" → 201 `APPROVED`, approved_amount "40000.00", `PA-AUTO-APPROVED`, decided_by SYSTEM
- [PASS] api-104 K35.8 "50000.00" (== threshold) → 201 `APPROVED` "50000.00" `PA-AUTO-APPROVED`
- [PASS] api-105 K35.8 "50000.01" → 201 `PENDING` `PA-MANUAL-REVIEW`
- [PASS] api-106 MBR-5001/POL-GLD-0005 K35.8 "60000.00" → 201 `PARTIALLY_APPROVED` "40000.00" `PA-AUTO-CAPPED` (GOLD v1)
- [PASS] api-107 Z41.1 → 201 `REJECTED` `PA-REJECTED-EXCLUSION`, decided_by `SYSTEM`
- [PASS] api-108 unknown QQ9.9 → 201 `QUERY_RAISED` `PA-QUERY-UNKNOWN-DIAGNOSIS`
- [PASS] api-109 POST /api/preauths/1/decisions (adjudicator.priya) PARTIALLY_APPROVED "30000.00" `PA-PARTIAL-MANUAL` on the 80000.00 estimate → 200 `PARTIALLY_APPROVED` "30000.00", decision seq 3 decided_by `adjudicator.priya`
- [PASS] api-110 POST /api/preauths/2/decisions on APPROVED → 409 `INVALID_PREAUTH_STATE` "cannot move from APPROVED to REJECTED"
- [PASS] api-111 POST /api/preauths/7/query-response (cityhosp.desk) → 200 `PENDING`, decision seq 3 `PA-QUERY-ANSWERED`
- [PASS] api-112 GET /api/adjudication/queue (INSURER) → 200, PENDING items only, ids [1, 4, 8] in ascending `submitted_at` order, each with hospital_code, estimated_cost, diagnosis_code, age_hours. APPROVED/REJECTED/QUERY_RAISED items are absent. Later [10, 11] were listed oldest first, and the queue was `[]` once every item was decided
- [PASS] api-113 GET /api/preauths/1 as sunshine.desk (CITYHOSP pre-auth) → 404 `PREAUTH_NOT_FOUND`

Adversarial probes:

- [PASS] AC-05.5 I21.9 "20000.00" (within threshold, not in auto list) → 201 `PENDING` `PA-MANUAL-REVIEW`
- [PASS] NFR-01 estimated_cost JSON float `40000.5` → 422 `VALIDATION_ERROR` "money must be a decimal string"
- [PASS] PA-R1 estimated_cost "-5.00" → 422 `INVALID_ESTIMATED_COST`; "100.005" → 422 (at most 2 dp); "abc" → 422; "NaN" / "Infinity" → 422 "amount must be finite"
- [PASS] AC-03.3 expected_admission_date 2026-09-30 → 422 `ADMISSION_DATE_IN_PAST`
- [PASS] PA-R1 missing diagnosis_code → 422 `VALIDATION_ERROR` (Field required)
- [PASS] AC-03.4 MBR-3001/POL-SLV-0003 → 422 `NOT_ELIGIBLE`, `error.details.reason_codes = ["ELG-POLICY-INACTIVE","ELG-OUTSIDE-COVER-PERIOD"]`
- [PASS] AC-03.4 MBR-2001 on POL-SLV-0001 → 422 `NOT_ELIGIBLE` `["ELG-MEMBER-NOT-COVERED"]`
- [PASS] hospital spoofing: an extra body field `hospital_code: "SUNSHINE"` → 422 "Extra inputs are not permitted"
- [PASS] POST /api/preauths as INSURER → 403; as CUSTOMER → 403; with no token → 401 `UNAUTHENTICATED`
- [PASS] AC-04.9 decision with `PA-MADE-UP` → 422 `UNKNOWN_REASON_CODE`
- [PASS] AD-R4 decision with `reason_codes: []` → 422 `VALIDATION_ERROR` (min 1 item)
- [PASS] AD-R3 APPROVED with "70000.00" on an 80000.00 estimate → 422 `INVALID_APPROVED_AMOUNT`
- [PASS] AD-R3 PARTIALLY_APPROVED "80000.00" (== estimate), "90000.00" (> estimate), "0.00", and with the amount missing → 422 `INVALID_APPROVED_AMOUNT` each time
- [PASS] AD-R3 REJECTED with approved_amount "100.00" → 422 `INVALID_APPROVED_AMOUNT`
- [PASS] AD-R3 decision approved_amount JSON float `30000.0` → 422 `VALIDATION_ERROR`
- [PASS] decision with status `PENDING` → 422 (enum APPROVED/PARTIALLY_APPROVED/REJECTED/QUERY_RAISED)
- [PASS] none of the rejected probes wrote anything: pre-auth 1 was still `PENDING` with 2 decisions before api-109
- [PASS] AD-R3 policy cap: GOLD-0005 (cap 40000.00) I21.9 60000.00 → APPROVED → 422 "estimate exceeds the policy cap 40000.00"; PARTIALLY_APPROVED "45000.00" → 422 "exceeds the policy cap"; "40000.00" → 200
- [PASS] AC-04.10 HOSPITAL token posting a decision → 403 `FORBIDDEN`; ADMIN token posting a decision → 403 (INSURER only, per the API table)
- [PASS] AC-04.4 decision on PARTIALLY_APPROVED → 409; on a SYSTEM-REJECTED pre-auth → 409 `INVALID_PREAUTH_STATE`; on an unknown id 9999 → 404
- [PASS] AC-04.6 INSURER APPROVED `PA-APPROVED-MANUAL` on pre-auth 4 (50000.01) → 200 APPROVED "50000.01". Without approved_amount (pre-auth 8) → 200, amount defaults to the estimate "20000.00". Both left the queue
- [PASS] AC-04.8 INSURER QUERY_RAISED `PA-QUERY-DOCUMENTS` on the answered pre-auth 7 → 200 `QUERY_RAISED`
- [PASS] E2-S4 query-response on PENDING pre-auth 4 → 409 `INVALID_PREAUTH_STATE`; on APPROVED pre-auth 2 → 409
- [PASS] E2-S4 sunshine.desk query-response on the CITYHOSP pre-auth 7 → 404; INSURER query-response → 403; blank `response_note` → 422
- [PASS] PA-R8 cityhosp.desk reading SUNSHINE pre-auth 10 → 404; sunshine.desk reading its own 10 → 200; INSURER and ADMIN reading pre-auth 1 → 200; CUSTOMER GET /api/preauths/1 → 403
- [PASS] CUSTOMER GET /api/preauths → 403. sunshine.desk GET /api/preauths before it submitted anything → `[]` (scoped to its own)
- [PASS] queue as ADMIN → 200; as HOSPITAL → 403
- [PASS] PA-R6 rule-version scoping: SILVER v2 was published with an extra catalogue code `PA-EVAL-EXTRA` (and threshold 30000.00). A **v1** pre-auth (12) deciding with `PA-EVAL-EXTRA` → 422 `UNKNOWN_REASON_CODE`. A new pre-auth (13) recorded `rule_version {SILVER, 2}` and was PENDING (40000.00 > the v2 threshold). REJECTED with `PA-REJECTED-MANUAL, PA-EVAL-EXTRA` → 200
- [PASS] AC-04.5 every one of the 53 decision rows in the DB (copy) has a non-empty reason-code set that is a subset of its own pre-auth's rule-version catalogue (0 violations). Every SILVER v1 decision is ⊆ the 12-code SILVER v1 catalogue from GET /api/admin/products/SILVER/coverage-rules
- [PASS] AC-03.2 every seq=1 decision row is `PENDING` / `["PA-SUBMITTED"]`; 23 pre-auths ↔ 23 claim_cases, all `PRE_AUTH`
- [PASS] NFR-03 two pre-auths carried clinical_notes containing `EVALMARKER-B-7731` and diagnosis I21.9 (label "Acute myocardial infarction"). The stderr log (138 lines) has 0 hits for `EVALMARKER`, `I21.9`, `myocardial` (case-insensitive), `K35.8`, `Z41.1`, `QQ9.9`, `appendicitis`, the query-response note text, `MBR-`, `Verma`, `Demo@1234`. 0 Tracebacks, 0 ERROR lines. Log events carry only ids/status (`preauth.submitted {case_id, preauth_id, status}`)
- [PASS] NFR-02 on a COPY of the temp DB: `UPDATE preauth_decisions` → `IntegrityError: append-only: preauth_decisions`; `DELETE preauth_decisions` → same; `UPDATE preauths` / `DELETE preauths` → `IntegrityError: append-only: preauths`

## Performance Checks

- [PASS] POST /api/preauths ≤ 500 ms. The first (cold) submission took 0.111 s. 10 consecutive J18.9 submissions took 0.020–0.042 s (median ≈ 0.023 s). Every other submission observed took 0.019–0.037 s.

## Architecture Checks

- [PASS] pytest `tests/unit tests/architecture` plus the 6 named API files → **327 passed, 1 skipped, 2 deselected**. The skip is `test_layering.py:37: not a layered module`. The sprint-B files alone: `test_ac03_ac05_preauth.py` + `test_ac04_adjudication.py` → 29 passed.
  - Excluded as later-sprint work in progress (src/service/case_service.py and settlement_service.py do not exist yet, and these files are timestamped 21:16, after the sprint-B files at 21:07): `tests/architecture/test_settled_cases_immutable.py` (collection ImportError `case_service`) and `tests/architecture/test_bill_cap_enforced.py::{test_submit_final_bill_calls_the_cap_rule, test_settle_uses_the_calculator}` (FileNotFoundError on those service files). Neither touches group B.
- [PASS] layering: `lint-imports` → "Contracts: 3 kept, 0 broken." (81 files, 336 dependencies)
- [PASS] typing: `mypy` → "Success: no issues found in 56 source files"
- [PASS] lint: `ruff check src tests/unit tests/api/test_ac03_ac05_preauth.py tests/api/test_ac04_adjudication.py` → "All checks passed!"
- [PASS] hooks: `bash scripts/test-hooks.sh` → 11/11 ok, exit 0
- [PASS] append_only: triggers `trg_preauths_no_update/no_delete`, `trg_preauth_decisions_no_update/no_delete` exist, and the live SQL probes above aborted
- [PASS] migrations: `0002_preauth_cases.sql` was added and applied. The 0001 SHA-256 checksum (`40493b15…a337d1c`) is identical in this sprint's DB ledger, in the sprint-A evaluation DB (`$TEMP/medicard-eval-A.db`, applied 15:37Z) and in a fresh hash of the file on disk. 0001 is unchanged
- [PASS] phi: see the NFR-03 probe above

## Playwright Checks

- [SKIP] None. This contract is API-only (`playwright_checks: []`, `design_checks: {}`).

## Features Updated

The evaluator was told not to edit features.json, so the verdicts below are not written there. They are for the orchestrator to apply.

- F012: PASS (api-101, AC-03.2 DB check)
- F013: PASS (api-102 + validation probes)
- F014: PASS (api-104 inclusive boundary, api-105)
- F015: PASS (api-106)
- F016: PASS (api-107)
- F017: PASS (api-109)
- F018: PASS (hospital decision → 403)
- F019: PASS (api-111)

## Evidence

- Server log: `$TEMP/medicard-eval-B.log` (138 lines, JSON structured, correlation ids present)
- Throwaway DB: `$TEMP/medicard-eval-B.db`. The SQL probes ran on a copy in the session scratchpad (`evalB-copy.db`)
- pytest output: `$TEMP/evalB-pytest.txt` (full run, showing the later-sprint errors) and `$TEMP/evalB-pytest2.txt` (scoped run, 327 passed)
- The server (PID 8140, port 8011) was stopped after the checks. Port 8011 no longer listens.

## Observations (non-failing)

1. **JSON integer money is accepted.** `estimated_cost: 40000` (a JSON integer, not a string) → 201 APPROVED "40000.00". PA-R1 says "decimal string" and NFR-01 says "JSON carries money as strings". The validator only rejects numbers *with a fraction*. No precision is lost, and this matches the Sprint-A money parser convention. Still, it is a literal deviation from the spec wording. Recommend deciding whether integers should be rejected too.
2. Queue ordering uses `submitted_at` at one-second resolution. Same-second submissions (for example 4 and the batch at 15:44:39) come out in id order. This is consistent with "oldest first", but it relies on an implicit tie-break.
3. `age_hours` is serialised as a decimal string ("0.00"). That is fine, but it is not money, so a number would also be reasonable. Document the choice.
4. A query-response decision row records `decided_by = cityhosp.desk` (the hospital user). AD-R5 only talks about insurer decisions, so this is reasonable, but it should be stated in the spec.
5. An INSURER can raise `QUERY_RAISED` again on a pre-auth whose unknown-diagnosis query was answered, and could approve an unknown-ICD pre-auth after the answer. The spec allows this.
6. ADMIN cannot post `/decisions` (403). This matches the API table (INSURER only). Admin intervention is via the Sprint-4 override.
7. Log timestamps are local (+0530) while the API returns UTC. They are consistent within each, but they differ from each other.
8. Later-sprint test files already in the tree (`test_settled_cases_immutable.py` and the `test_bill_cap_enforced.py` service checks) currently fail or error. `tests/api/test_ac06..ac09` were not run, because they are out of scope. A full-suite `pytest` is red until that sprint lands, so the sprint-PR gate must scope its test selection.
