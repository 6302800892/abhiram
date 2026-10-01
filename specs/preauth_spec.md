# Feature Spec — Pre-Authorization

Owns: **AC-03**, **AC-04** (system outcomes), **AC-05** · Sprint: 2 ·
Domain modules: `src/domain/preauth_rules.py`, `src/domain/preauth_state_machine.py`

## Overview

A network hospital raises a pre-auth for an eligible member. The pre-auth engine decides
rule-eligible cases instantly. Everything else goes to the adjudicator queue.

## Business Rules

| ID | Rule |
|---|---|
| PA-R1 | Submission requires `member_id`, `policy_number`, `diagnosis_code`, `estimated_cost` (> 0, decimal string), and `expected_admission_date` (today or later). `clinical_notes` is optional |
| PA-R2 | The member must be ELIGIBLE (eligibility spec EL-R4) at submission. Otherwise 422 `NOT_ELIGIBLE` with the reason codes |
| PA-R3 | On submission a pre-auth is created in **PENDING** with reason `PA-SUBMITTED`. A claim case is created in `PRE_AUTH` (BRD D-5). The pre-auth records the `coverage_rule_version` in force |
| PA-R4 | Directly after creation the auto-decider evaluates the pre-auth against that rule version, in this order: |
| | 1. diagnosis not in the ICD stub ⇒ **QUERY_RAISED**, `PA-QUERY-UNKNOWN-DIAGNOSIS` (BRD D-4) |
| | 2. diagnosis in the product's exclusions ⇒ **REJECTED**, `PA-REJECTED-EXCLUSION` (BRD D-3) |
| | 3. `estimated_cost ≤ auto_approve_threshold` AND diagnosis in `auto_approved_diagnoses` ⇒ approve up to `policy_cap = min(per_claim_cap, remaining_sum_insured)`: |
| | — `estimated_cost ≤ policy_cap` ⇒ **APPROVED**, amount = estimated_cost, `PA-AUTO-APPROVED` |
| | — otherwise ⇒ **PARTIALLY_APPROVED**, amount = policy_cap, `PA-AUTO-CAPPED` |
| | 4. otherwise stays **PENDING** with `PA-MANUAL-REVIEW` (goes to the adjudicator queue) |
| PA-R5 | System decisions are recorded with `decided_by = "SYSTEM"` as append-only decision rows (NFR-02) |
| PA-R6 | Every reason code on a decision must exist in the `reason_codes` catalogue of the pre-auth's coverage-rule version. Otherwise 422 `UNKNOWN_REASON_CODE` |
| PA-R7 | In `QUERY_RAISED` the hospital answers with `POST /api/preauths/{id}/query-response` `{response_note}`. The pre-auth goes back to **PENDING** with `PA-QUERY-ANSWERED` |
| PA-R8 | A hospital can read only pre-auths it raised (others → 404) |

## Pre-auth state transitions (AC-04)

Allowed: PENDING→{APPROVED, PARTIALLY_APPROVED, REJECTED, QUERY_RAISED}; QUERY_RAISED→PENDING;
override (adjudication spec) REJECTED|QUERY_RAISED→{APPROVED, PARTIALLY_APPROVED}. Anything else
⇒ `InvalidPreAuthStateException` (409 `INVALID_PREAUTH_STATE`).

## API

| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/api/preauths` | HOSPITAL | → 201 pre-auth view `{preauth_id, case_id, status, approved_amount, reason_codes, decisions[], rule_version}` |
| GET | `/api/preauths/{id}` | HOSPITAL (own), INSURER, ADMIN | pre-auth view |
| POST | `/api/preauths/{id}/query-response` | HOSPITAL (own) | → 200 pre-auth view |

## Acceptance Criteria

### AC-03 — Submit pre-auth enters PENDING
- **AC-03.1** Given an eligible member and a diagnosis needing manual review, When the hospital submits, Then 201, status `PENDING`, and decisions `[PENDING/PA-SUBMITTED, PENDING/PA-MANUAL-REVIEW]`.
- **AC-03.2** Given any submission, Then the first decision row is always `PENDING` with `PA-SUBMITTED`, and a case exists in `PRE_AUTH`.
- **AC-03.3** Given `estimated_cost` ≤ 0 or an admission date in the past, Then 422.
- **AC-03.4** Given a NOT_ELIGIBLE member, Then 422 `NOT_ELIGIBLE`.

### AC-04 — Lifecycle with versioned reason codes
- **AC-04.1** Given an unknown diagnosis code, Then `QUERY_RAISED` with `PA-QUERY-UNKNOWN-DIAGNOSIS`.
- **AC-04.2** Given an excluded diagnosis, Then `REJECTED` with `PA-REJECTED-EXCLUSION`, `decided_by=SYSTEM`.
- **AC-04.3** Given a pre-auth in QUERY_RAISED, When the hospital responds, Then status `PENDING` with `PA-QUERY-ANSWERED`.
- **AC-04.4** Given a decided (APPROVED) pre-auth, When any further decision is attempted, Then 409 `INVALID_PREAUTH_STATE`.
- **AC-04.5** Every decision's reason codes belong to the catalogue of the pre-auth's `rule_version`.

### AC-05 — Auto-approval up to policy cap
- **AC-05.1** Given estimate 40000.00 ≤ threshold 50000.00 and an auto-approved diagnosis, Then `APPROVED`, amount 40000.00, `PA-AUTO-APPROVED`.
- **AC-05.2** Given estimate **equal** to the threshold, Then auto `APPROVED` (boundary is inclusive).
- **AC-05.3** Given estimate 50000.01 (above the threshold), Then it stays `PENDING` (`PA-MANUAL-REVIEW`).
- **AC-05.4** Given an auto-approved diagnosis within threshold but a policy cap below the estimate, Then `PARTIALLY_APPROVED` with amount = policy cap and `PA-AUTO-CAPPED`.
- **AC-05.5** Given a diagnosis within threshold but not in the auto list, Then it stays `PENDING`.

## Tests

`tests/unit/test_preauth_rules.py`, `tests/unit/test_preauth_state_machine.py`,
`tests/api/test_ac03_ac05_preauth.py`.
