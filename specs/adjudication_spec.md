# Feature Spec — Adjudicator Workbench & Admin Override

Owns: **AC-04** (manual decisions), **AC-10** · Sprints: 2 (workbench) and 4 (override audit) ·
Domain modules: `src/domain/preauth_state_machine.py`, `src/domain/override_policy.py`

## Overview

Adjudicators work a queue of PENDING pre-auths: large estimates, non-auto diagnoses, and answered
queries. The insurer admin can override an auto-rejection or an escalated query, and every
override is audited.

## Business Rules

| ID | Rule |
|---|---|
| AD-R1 | The queue (`GET /api/adjudication/queue`) lists every pre-auth whose current status is `PENDING`, oldest first, with hospital, estimate, diagnosis **code** and age in hours |
| AD-R2 | An `INSURER` decides with `{status, approved_amount?, reason_codes[], note?}` on a PENDING pre-auth only |
| AD-R3 | `APPROVED` ⇒ approved_amount = estimated_cost, which must be ≤ policy cap. `PARTIALLY_APPROVED` ⇒ 0 < approved_amount < estimated_cost and ≤ policy cap. `REJECTED` / `QUERY_RAISED` ⇒ approved_amount is null. Breach ⇒ 422 `INVALID_APPROVED_AMOUNT` |
| AD-R4 | At least one reason code is required. Codes must come from the pre-auth's rule-version catalogue (PA-R6) |
| AD-R5 | Decisions are appended with `decided_by = <username>` (append-only, NFR-02) |
| AD-R6 | **Override (AC-10):** only `ADMIN`. Allowed when the current decision is `REJECTED` with `decided_by = SYSTEM` (auto-rejected) or the status is `QUERY_RAISED` (escalated query). Target status `APPROVED` or `PARTIALLY_APPROVED` with an amount obeying AD-R3. `reason` is mandatory (non-blank, ≤ 500 chars). Otherwise 422 `OVERRIDE_NOT_ALLOWED` / `OVERRIDE_REASON_REQUIRED`. The claim case must still be `PRE_AUTH`; otherwise 409 `INVALID_CLAIM_STATE` and nothing is written (SEC-09) |
| AD-R7 | An override appends a decision with reason code `PA-OVERRIDE` **and** an audit record `{actor, action: "PREAUTH_OVERRIDE", entity_type: "preauth", entity_id, reason, from_status, to_status, occurred_at}` in the same transaction. No audit record ⇒ no override |
| AD-R8 | `GET /api/admin/audit` (ADMIN) lists audit records, newest first |

## API

| Method | Path | Role |
|---|---|---|
| GET | `/api/adjudication/queue` | INSURER, ADMIN |
| POST | `/api/preauths/{id}/decisions` | INSURER |
| POST | `/api/admin/preauths/{id}/override` | ADMIN |
| GET | `/api/admin/audit` | ADMIN |

## Acceptance Criteria

### AC-04 (manual) — Adjudicator decisions
- **AC-04.6** Given a PENDING pre-auth in the queue, When an INSURER approves with `PA-APPROVED-MANUAL`, Then status `APPROVED`, amount = estimate, and it leaves the queue.
- **AC-04.7** Given a PENDING pre-auth, When an INSURER partially approves 30000.00 of 80000.00 with `PA-PARTIAL-MANUAL`, Then `PARTIALLY_APPROVED` with 30000.00.
- **AC-04.8** Given a PENDING pre-auth, When an INSURER raises a query with `PA-QUERY-DOCUMENTS`, Then `QUERY_RAISED`.
- **AC-04.9** Given a reason code missing from the version catalogue, Then 422 `UNKNOWN_REASON_CODE`.
- **AC-04.10** Given a HOSPITAL token, When posting a decision, Then 403.

### AC-10 — Audited override
- **AC-10.1** Given an auto-rejected pre-auth, When an ADMIN overrides to `APPROVED` with a reason, Then status `APPROVED` with `PA-OVERRIDE`, and an audit record holds the actor username, timestamp, reason, and from/to status.
- **AC-10.2** Given a QUERY_RAISED (escalated) pre-auth, When an ADMIN overrides to `PARTIALLY_APPROVED`, Then it succeeds and is audited.
- **AC-10.3** Given an INSURER token, When overriding, Then 403 and no audit record is written.
- **AC-10.4** Given a blank reason, Then 422 `OVERRIDE_REASON_REQUIRED` and nothing is written.
- **AC-10.5** Given a pre-auth rejected **manually** by an adjudicator, or already APPROVED, Then 422 `OVERRIDE_NOT_ALLOWED`.

## Change log
- 2026-10-01 — AD-R6: an override requires the case to still be PRE_AUTH (security review SEC-09: a closed case could gain an approved pre-auth).

## Tests

`tests/unit/test_override_policy.py`, `tests/api/test_ac04_adjudication.py`,
`tests/api/test_ac10_override_audit.py`, `tests/architecture/test_override_audited.py`.
