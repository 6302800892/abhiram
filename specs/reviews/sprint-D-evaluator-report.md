# Evaluator Report — Group D (Sprint 4)

Date: 2026-10-01

VERDICT: PASS

Contract: `sprint-contracts/group-D.json` (E4-S1 audited override, AC-10 / AD-R6..AD-R8; E4-S2 reports, RP-R1..RP-R6).

I started a live server: uvicorn `src.main:create_app` on 127.0.0.1:8015 with a fresh DB at `$TEMP/medicard-eval-D.db`, `MEDICARD_PBKDF2_ITERATIONS=1000` and no frontend dist. `GET /health` returned 200 `{"status":"ok","service":"medicard"}`. Startup reported `migrations_applied: 4`.

A second fresh server on 127.0.0.1:8016 (`$TEMP/medicard-eval-D2.db`) was used only for the timed turnaround probe. Both servers were stopped after the run.

Users: cityhosp.desk, sunshine.desk, adjudicator.priya, admin.sam, asha.verma (Demo@1234). Every pre-auth used MBR-1001 / POL-SLV-0001 with admission date 2026-10-02.

## API Checks

| ID | Check | Expected | Observed | Result |
|---|---|---|---|---|
| api-301 | P1 Z41.1 50000.00. Auto-decision, then override `{"status":"APPROVED","reason":"Reconstructive after trauma - clinical review"}` as admin.sam | Auto REJECTED by SYSTEM; override 200 APPROVED with PA-OVERRIDE and an audit record | Auto-decision REJECTED `PA-REJECTED-EXCLUSION` by SYSTEM. Override 200: status APPROVED, approved_amount "50000.00", reason_codes ["PA-OVERRIDE"]. Decision seq 3 is `decided_by admin.sam`, appended after seq 1 PENDING and seq 2 REJECTED. Audit row: `{id 1, actor "admin.sam", action "PREAUTH_OVERRIDE", entity_type "preauth", entity_id 1, from_status "REJECTED", to_status "APPROVED", reason <verbatim>, occurred_at "2026-10-01T16:21:48+00:00"}` (ISO, timezone-aware). Audit count went from 0 to 1 | PASS |
| api-302 | P2 ZZZ.9 1000.00. Auto-decision, then override PARTIALLY_APPROVED 600.00 | Auto QUERY_RAISED; override 200 and audited | Auto-decision QUERY_RAISED. Override 200 PARTIALLY_APPROVED "600.00". Audit row from QUERY_RAISED to PARTIALLY_APPROVED, entity_id 2 | PASS |
| api-303 | Override P6 (auto-rejected) as adjudicator.priya | 403, no audit row | 403. Audit count unchanged | PASS |
| api-304 | A failed audit write rolls back the decision | 500, decision not persisted | `tests/architecture/test_override_audited.py::test_failed_audit_write_rolls_back_the_override` PASSED. It monkeypatches `audit_repo.insert` to raise, gets a 500, and the last decision row stays REJECTED. Code reasoning is under Architecture Checks | PASS |
| api-305 | Reason `""` | 422 OVERRIDE_REASON_REQUIRED | 422 OVERRIDE_REASON_REQUIRED. Audit count unchanged | PASS |
| api-306 | P4 I21.9 manually REJECTED (PA-REJECTED-MANUAL); P5 K35.8 auto-APPROVED | 422 OVERRIDE_NOT_ALLOWED | 422 OVERRIDE_NOT_ALLOWED for both. P4 stays REJECTED. No audit rows | PASS |
| api-307 | `GET /api/admin/audit` | Newest first, ADMIN only | 5 rows with ids [5,4,3,2,1] and occurred_at non-increasing. INSURER, HOSPITAL and CUSTOMER each got 403 | PASS |
| api-308 | `GET /api/reports/summary` as admin | 200, all metrics, money/ratios as strings | 200 with all 6 keys. Every value matched the known dataset (see Adversarial Probes, reports). No JSON floats anywhere in the body | PASS |
| api-309 | Summary as cityhosp.desk | 403 | 403. CUSTOMER also 403, no token 401, INSURER 200 | PASS |

## Adversarial Probes

### Override (AC-10 / AD-R6..AD-R8)

| Probe | Expected | Observed | Result |
|---|---|---|---|
| Override as cityhosp.desk, as sunshine.desk (the hospital that raised P6), as asha.verma (the member) | 403, no audit row | 403 for each. Audit count delta 0 | PASS |
| Override with no token | 401 | 401 | PASS |
| Whitespace-only reason `"   \t  "` | 422 OVERRIDE_REASON_REQUIRED | 422 OVERRIDE_REASON_REQUIRED | PASS |
| Reason key missing | 422 | 422 VALIDATION_ERROR | PASS |
| Reason of 501 chars | 422 | 422 OVERRIDE_REASON_REQUIRED | PASS |
| Reason of 1001 chars | 422 | 422 VALIDATION_ERROR (schema max 1000) | PASS |
| Reason of exactly 500 chars (boundary) | 200 | 200, audited, full reason stored | PASS |
| Override of a PENDING pre-auth (P3 I21.9 80000.00) | 422 OVERRIDE_NOT_ALLOWED | 422 OVERRIDE_NOT_ALLOWED, no audit row | PASS |
| Adjudicator-raised query: P3 decided QUERY_RAISED with PA-QUERY-DOCUMENTS, then override APPROVED | 200 | 200 APPROVED. Audit row from QUERY_RAISED to APPROVED | PASS |
| Second override of P1, which is already APPROVED by override and admitted | 422 OVERRIDE_NOT_ALLOWED | 422 OVERRIDE_NOT_ALLOWED | PASS |
| P7 Z41.1 300000.00 (cap = per_claim_cap 200000.00): PARTIALLY_APPROVED 300000.00 (= estimate), 300000.01, 200000.01 (above cap), 0.00, or no amount | 422 | 422 INVALID_APPROVED_AMOUNT for each. No audit rows | PASS |
| P7: APPROVED where estimate > cap | 422 | 422 INVALID_APPROVED_AMOUNT | PASS |
| P7: target REJECTED or QUERY_RAISED | 422 | 422 VALIDATION_ERROR | PASS |
| P7: JSON float amount 1000.5 | 422 | 422 VALIDATION_ERROR | PASS |
| P7: PARTIALLY_APPROVED exactly at cap 200000.00 | 200 | 200, audited | PASS |
| Override of unknown id 999999 | 404 | 404 PREAUTH_NOT_FOUND | PASS |
| After the P1 override, `POST /api/cases/1/admit` as hospital | 200 | 200 ADMITTED | PASS |
| Customer notification for the override transition (`GET /api/customers/me/notifications` as asha.verma) | Notification for REJECTED→APPROVED | Case 1 notifications in order: PENDING, REJECTED, APPROVED ("CASE-000001: your pre-authorization status is now APPROVED."), ADMITTED. My driver's first assertion marked this FAIL because it searched for both statuses in one notification object. The API emits one notification per `to_status`, which is the documented shape. Re-judged by hand as PASS | PASS |
| Direct SQL on a copy of the live DB (`$TEMP/medicard-eval-D-copy.db`): `UPDATE audit_records SET reason='tampered' WHERE id=1`, `DELETE ... WHERE id=1`, `UPDATE audit_records SET actor='x'` | Abort "append-only" | Each raised `IntegrityError: append-only: audit_records`. Row 1 is unchanged | PASS |

### Reports (RP-R1..RP-R6)

Known dataset, 11 pre-auths:

- CITYHOSP (7): Z41.1 ×2, ZZZ.9 (auto-queried), I21.9 ×3 (one adjudicator-queried, one manually rejected, one approved and settled), K35.8
- SUNSHINE (4): Z41.1, ZZZ.9 (auto-queried), J18.9, O80

There was one settlement: I21.9 100000.00 approved, bill 90000.00, settled at 76500.00. I computed the expected values independently, from per-pre-auth `GET /api/preauths/{id}` decisions and from the ICD stub.

| Metric | Expected | Observed | Result |
|---|---|---|---|
| RP-R1 turnaround | Mean of (first non-PENDING decided_at − submitted_at) from API data = "0.00", a non-negative string with 2 decimal places | "0.00" | PASS |
| RP-R1 non-zero (isolated server 8016) | Empty DB → null; one PENDING only → null; decided 66.0 s after submit → 66/3600 = 0.0183 → "0.02" | null, null, "0.02" | PASS |
| RP-R2 settlement_volume | `{count 1, total_amount "76500.00"}` | Exactly that | PASS |
| RP-R3 query_rate_by_hospital | CITYHOSP (7, 2, "0.2857"); SUNSHINE (4, 1, "0.2500"). Both auto-queried and adjudicator-queried pre-auths count as "ever queried", even after override | Exactly that | PASS |
| RP-R4 top_diagnoses | 6 distinct codes, so 5 are returned: I21.9 (3), Z41.1 (3), ZZZ.9 (2), J18.9 (1), K35.8 (1). O80 is cut by the code-asc tie-break. Labels come from the stub, and ZZZ.9 gets "Unknown diagnosis" | Exactly that | PASS |
| RP-R5 loss_ratio_by_product | SILVER 76500.00 / 36000.00 = "2.1250"; GOLD 0.00 / 40000.00 = "0.0000" | Exactly that. Fields settled_amount, premium_total and loss_ratio are all strings | PASS |
| RP-R5 average_loss_ratio | (2.1250 + 0.0000) / 2 = "1.0625" | "1.0625" | PASS |
| NFR-01 | No JSON numbers for money or ratios | Recursive walk found 0 floats. Counts are ints | PASS |
| Report PHI | No names, notes or override reasons in the body | None found | PASS |

### Server log (`$TEMP/medicard-eval-D.log`, 206 lines)

There are 0 tracebacks and 0 ERROR lines. I searched the log for override reason text ("Reconstructive", "Documents verified", "Escalated query", the 500-char "aaaa…", "cap boundary", "probe"), member names (Asha, Rohan), diagnosis labels, passwords and Bearer tokens, and found 0 matches.

The `preauth.overridden` lines carry only correlation_id, case_id, preauth_id, from_status and to_status. PASS.

## Performance Checks

| Endpoint | Budget | Observed | Result |
|---|---|---|---|
| GET /api/reports/summary (admin, 11 pre-auths, 1 settlement) | ≤ 500 ms | First call 35.4 ms. 20 samples: median 21.0 ms, p95 24.5 ms, max 25.5 ms | PASS |

## Architecture Checks

| Check | Observed | Result |
|---|---|---|
| override_audited | `tests/architecture/test_override_audited.py` passed 3 of 3: `test_override_route_requires_exactly_admin`, `test_failed_audit_write_rolls_back_the_override` and `test_audit_records_are_append_only`. This is the one code read allowed by the brief. In `src/service/override_service.py::override`, every validation runs before any write: visibility, `ensure_override_allowed`, the state edge, the reason-code catalogue, and `validate_decision_amount` against the current cap. The decision append, the audit insert and the timeline/notification write then all run inside a single `with conn:` block. `src/repository/db.py::connect` uses the default sqlite3 isolation (implicit deferred transaction, not autocommit), so an exception inside the block rolls back the decision. This agrees with the test result | PASS |
| append_only | Migration `0004_audit_records.sql` defines `trg_audit_records_no_update` and `trg_audit_records_no_delete` (RAISE ABORT 'append-only: audit_records'). Verified live on a DB copy (see probes) | PASS |
| migrations | `migrations/0004_audit_records.sql` was added. The normalized sha256 of 0001–0003 matches the checksums recorded in DBs built during earlier sprints: 0001 in `medicard-eval-A.db`, 0001–0002 in `-B.db`, 0001–0003 in `-C.db`. The runner's checksum ledger accepted all 4 on startup | PASS |

### Gates

| Gate | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` | Exit 0. Summary via `-o addopts=""`: 423 passed, 1 skipped, 1 warning (Starlette httpx deprecation). The 36 Sprint 4 tests (override, audit, reports, report_metrics, override_policy) all passed |
| `.venv/Scripts/lint-imports.exe` | 3 contracts kept, 0 broken |
| `.venv/Scripts/python.exe -m mypy` | Success: no issues found in 65 source files |
| `.venv/Scripts/ruff.exe check .` | All checks passed |
| `bash scripts/test-hooks.sh` | 13 ok, 0 not-ok, exit 0 |

## Playwright Checks

None in this contract (`playwright_checks: []`).

## Features Updated

The evaluator was told not to modify `features.json`, so these are the recommended values:

- F029: PASS. AC-10.1 and AC-10.2: overrides of auto-rejected and queried pre-auths (both auto- and adjudicator-queried) are recorded with PA-OVERRIDE and audited.
- F030: PASS. AC-10.3, AC-10.4 and AC-10.5: role 403 with no audit row, reason validation, and OVERRIDE_NOT_ALLOWED for manual rejection, APPROVED and PENDING. The AD-R7 rollback is verified by the architecture test.
- F031: PASS. AD-R8: audit log is newest first and ADMIN only. Append-only triggers verified.
- F032: PASS. RP-R1..RP-R6 match the hand-computed dataset, values are Decimal strings, and the endpoint is INSURER/ADMIN only.

## Evidence

- Drivers (scratchpad `C:/Users/Pandu/AppData/Local/Temp/claude/c--Users-Pandu-OneDrive--------abhiram/bad12ece-3b1b-4c50-90d4-17126fa5c06f/scratchpad/`):
  - `evald.py`: override, audit and role probes plus the settlement. Results in `results_d1.json`.
  - `evald_rep.py`: reports, NFR-01 and performance. Results in `results_d2.json`.
  - The turnaround timing probe on port 8016 ran inline.
- Logs: `$TEMP/medicard-eval-D.log` and `$TEMP/medicard-eval-D2.log`.
- DBs: `$TEMP/medicard-eval-D.db`, `$TEMP/medicard-eval-D-copy.db` (used for the trigger tampering), `$TEMP/medicard-eval-D2.db`.

## Observations

These are not defects against the contract:

1. Reason-length errors use two different codes. A reason of 501–1000 chars returns 422 `OVERRIDE_REASON_REQUIRED`, while one over 1000 chars returns 422 `VALIDATION_ERROR` (the schema has `max_length=1000`). Both are 422 as AD-R6 requires, but the error code for "too long" is inconsistent. A dedicated code such as `OVERRIDE_REASON_TOO_LONG` would also be clearer than "REQUIRED".
2. Non-approval targets (REJECTED, QUERY_RAISED) return `VALIDATION_ERROR` from the schema enum, not `OVERRIDE_NOT_ALLOWED`. This is acceptable because AD-R6 limits the targets.
3. In `override_service.py`, the current-status check happens before the `with conn:` write block. Two concurrent overrides of the same pre-auth could both pass validation and both append. This is unlikely with SQLite's single writer and a demo-scale admin, but a re-check inside the transaction (or `BEGIN IMMEDIATE`) would close the gap.
4. An over-cap estimate returns `INVALID_APPROVED_AMOUNT` on override, consistent with AD-R3.
5. `loss_ratio_by_product` includes products whose policies have zero settlements (GOLD "0.0000"), and these count toward `average_loss_ratio`. This matches RP-R5, which omits only products with a zero premium total. Readers should know that the average is not weighted by premium.
6. The live turnaround figure is "0.00" for the main dataset because auto-decisions are instant. The non-zero path was verified separately with a real 66 s delay ("0.02").
