# FL-001 — Settlement-cap violation when coverage rules change mid-cycle

| | |
|---|---|
| Loop | Autonomous fix loop (harness `/auto` self-healing pattern: detect → reproduce → fix → validate → PR) |
| Detected by | Evaluator agent, Sprint 3 / group C, round 1: `specs/reviews/sprint-C-evaluator-report.md`, `specs/reviews/eval-failures-C.json` |
| Validated by | Evaluator agent, round 2: `specs/reviews/sprint-C-evaluator-report-r2.md` (**VERDICT: PASS**) |
| Branch / PR | `fix/fl-001-rule-version-snapshot` → `docs/pull-requests/PR-08-fix-fl-001.md` |
| ACs / rules | AC-06, AC-07, AC-08 · ST-R1, ST-R2, AM-R6 · PA-R3, NA-R4 |
| Severity | Major. The hospital is underpaid on settlement, and the settlement row is append-only, so it cannot be corrected afterwards |

## 1. Detect

All 361 tests were green and the contract's 14 API checks passed. The evaluator's adversarial
checklist includes the brief's §8.2 #12 scenario: *buffer percentage changed mid-cycle*. That
probe failed:

| ID | Reproduction | Observed | Expected (per spec) |
|---|---|---|---|
| C-01a | Pre-auth 100000.00 approved under SILVER v1 (buffer 10 %), case admitted. Admin publishes v2 (buffer 5 %). Bill 108000.00 | `422 BILL_EXCEEDS_CAP`, cap `105000.00` | `201`, cap `110000.00` |
| C-01b | Bill 108000.00 accepted under v1 (cap 110000.00), then v2 published, discharge, settle | buffer 5, cap 105000.00, settlement **90000.00** | buffer 10, cap 110000.00, copay 10300.00, settlement **92700.00** (underpaid by 2700.00) |
| C-02 | Close a PRE_AUTH case whose pre-auth is APPROVED | `422 PREAUTH_NOT_REJECTED` (code in no spec) | `409 INVALID_CLAIM_STATE` (AM-R1) |

## 2. Reproduce (red)

`tests/api/test_fix_loop_rule_version.py` reproduces each failure through the public API.
Output is in `docs/fix-loops/FL-001-reproduce.txt`:

```
FAILED test_c01a_bill_cap_keeps_the_preauth_rule_version  -> BILL_EXCEEDS_CAP cap "105000.00"
FAILED test_c01b_settlement_uses_the_preauth_rule_version -> ('5', '105000.00', …) != ('10', '110000.00', …)
FAILED test_c02_closing_pre_auth_case_with_live_preauth_is_invalid_claim_state -> PREAUTH_NOT_REJECTED
3 failed, 1 passed   (control: new pre-auths after the publish correctly use v2)
```

## 3. Root cause (environment and spec first, then code)

1. **Environment.** The same failure reproduces in the pytest app (pinned clock, temp DB) and on
   a live uvicorn server. So it is not a data, clock or configuration artefact.
2. **Spec.** PA-R3 ("the pre-auth records the coverage_rule_version in force") and NA-R4
   ("existing pre-auths keep the version they were decided under") were clear. ST-R1, however,
   said only "`buffer_pct` comes from the coverage rules of the policy". That ambiguous wording
   allowed reading the *current* version.
3. **Code.** `case_service.bill_terms()` and `settlement_service._settlement_input()` both
   called `coverage_service.current_rule(policy)`. That function is correct for *new* pre-auths
   and wrong for money terms of an existing case.
4. **Why tests missed it.** No test varied the rule version between approval and bill or
   settlement. C-02 came from inventing an error code during implementation instead of reading
   AM-R1.

## 4. Fix (spec first, then code)

| Step | Change |
|---|---|
| Spec | `specs/settlement_spec.md` ST-R1/ST-R2: buffer, deductible and co-pay come from the **pre-auth's recorded rule version**, never the current one. Added AC-07.8 and a change-log entry. `specs/admission_spec.md` AM-R6: a disallowed PRE_AUTH → CLOSED returns `409 INVALID_CLAIM_STATE`. Change-log entry |
| Guard (red first) | `tests/architecture/test_bill_cap_enforced.py::test_money_paths_never_read_the_current_rule_version`, which failed on `bill_terms` and `_settlement_input` before the fix |
| Code | New `case_service.case_rule(conn, case)`, which resolves `preauth_service.rule_version_of(pre-auth)`. `bill_terms` and `_settlement_input` use it. `close()` raises `InvalidClaimStateException` |
| Test | `test_ac08_rejected_preauth_case_can_close_but_approved_cannot` updated to the amended AM-R6 (the spec wins) |

## 5. Validate

- Local: `421 passed, 1 skipped` (`docs/fix-loops/FL-001-validate.txt`). ruff, mypy, lint-imports
  and the hook tests are green.
- Independent: the evaluator round 2 re-ran C-01a, C-01b and C-02 on a live server, plus a v3
  publish that changes the deductible and co-pay, plus regressions. **VERDICT: PASS.**

## 6. Knowledge deposit

- `.claude/state/learned-rules.md`, rule 1: "Money terms of an existing case come from the
  pre-auth's recorded rule version".
- `docs/knowledge-deposits.md` KD-11 and KD-12.
- Encoded as an architecture test (structural) and an AC-07.8 behavioural test, so a future agent
  cannot reintroduce `current_rule()` on a money path without a red build.
