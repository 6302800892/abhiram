# Feature Spec — Admission, Case Lifecycle & Timeline

Owns: **AC-06** (case updates), **AC-08**, **AC-09** · Sprint: 3 ·
Domain modules: `src/domain/claim_state_machine.py`, `src/domain/bill_rules.py`

## Overview

After an approved pre-auth, the hospital admits the patient, records procedures and the final bill,
and discharges. Every case transition is timestamped on a timeline, and the customer is notified
through a stub channel.

## Business Rules

| ID | Rule |
|---|---|
| AM-R1 | Case transitions follow `specs/app_spec.md §6.2` exactly. Others raise `InvalidClaimStateException` → 409 `INVALID_CLAIM_STATE` |
| AM-R2 | `admit` (HOSPITAL, own case) requires the pre-auth status `APPROVED` or `PARTIALLY_APPROVED`. Otherwise 422 `PREAUTH_NOT_APPROVED` |
| AM-R3 | `procedures` (HOSPITAL) may be added only while `ADMITTED`. Body `{procedure_code, description}` |
| AM-R4 | `final-bill` (HOSPITAL) may be submitted while `ADMITTED` or `DISCHARGED`. Body `{amount}` (decimal string > 0). It must satisfy the bill-cap rule (settlement spec ST-R1). Otherwise 422 `BILL_EXCEEDS_CAP` and nothing is stored. Accepted bills are appended as versions 1, 2, …; the latest version is the final bill (NFR-02) |
| AM-R5 | `discharge` (HOSPITAL) moves ADMITTED → DISCHARGED |
| AM-R6 | `dispute` (INSURER) moves DISCHARGED → DISPUTED with a mandatory reason. `close` (INSURER/ADMIN) moves SETTLED / DISPUTED → CLOSED, or PRE_AUTH → CLOSED only when the pre-auth is REJECTED. Closing a PRE_AUTH case whose pre-auth is not REJECTED is a disallowed transition: 409 `INVALID_CLAIM_STATE` |
| AM-R7 | Every case transition **and** every pre-auth status change appends a timeline event `{case_id, event_type, from_status, to_status, actor, occurred_at, note}` and sends one stub notification to the customer: an append to `notifications` with channel `STUB` |
| AM-R8 | Timeline visibility: HOSPITAL (own cases), the CUSTOMER who owns the member, INSURER and ADMIN. Others get 404 |
| AM-R9 | Once SETTLED, no procedure, bill or settlement change is accepted: 409 `CASE_SETTLED_IMMUTABLE` (NFR-08) |

## API

| Method | Path | Role |
|---|---|---|
| GET | `/api/cases` | HOSPITAL (own), CUSTOMER (own), INSURER, ADMIN |
| GET | `/api/cases/{id}` | same as timeline |
| GET | `/api/cases/{id}/timeline` | HOSPITAL (own), CUSTOMER (own), INSURER, ADMIN |
| POST | `/api/cases/{id}/admit` | HOSPITAL |
| POST | `/api/cases/{id}/procedures` | HOSPITAL |
| POST | `/api/cases/{id}/final-bill` | HOSPITAL |
| POST | `/api/cases/{id}/discharge` | HOSPITAL |
| POST | `/api/cases/{id}/dispute` | INSURER |
| POST | `/api/cases/{id}/close` | INSURER, ADMIN |
| GET | `/api/customers/me/notifications` | CUSTOMER |

## Acceptance Criteria

### AC-06 — Post-admission updates
- **AC-06.1** Given an ADMITTED case, When the hospital adds a procedure, Then 201 and it is listed on the case.
- **AC-06.2** Given a case approved for 100000.00 with buffer 10 %, When the hospital submits a final bill of 110000.00, Then 201 (boundary inclusive).
- **AC-06.3** Given the same case, When the bill is 110000.01, Then 422 `BILL_EXCEEDS_CAP` and no bill is stored.
- **AC-06.4** Given a PRE_AUTH case, When adding a procedure, Then 409 `INVALID_CLAIM_STATE`.

### AC-08 — Claim lifecycle
- **AC-08.1** The happy path PRE_AUTH → ADMITTED → DISCHARGED → SETTLED → CLOSED succeeds.
- **AC-08.2** DISCHARGED → DISPUTED → CLOSED succeeds.
- **AC-08.3** PRE_AUTH → DISCHARGED raises `InvalidClaimStateException` (409).
- **AC-08.4** Every disallowed pair in the 6×6 status matrix (6 case statuses) raises `InvalidClaimStateException` (unit test).
- **AC-08.5** Admitting a case whose pre-auth is PENDING ⇒ 422 `PREAUTH_NOT_APPROVED`.

### AC-09 — Notifications and timeline
- **AC-09.1** Given a case driven to SETTLED, Then the customer has one notification per transition, in order.
- **AC-09.2** Given the case, When the hospital and the customer each read the timeline, Then both see the same ordered events.
- **AC-09.3** Given another hospital, When it reads the timeline, Then 404.

## Change log
- 2026-10-01 — AM-R6 now names the error for closing a PRE_AUTH case with a live pre-auth: 409 `INVALID_CLAIM_STATE`. Sprint 3 evaluator failure C-02; the code had returned an undocumented `PREAUTH_NOT_REJECTED`.
- 2026-10-01 — AC-08.4 corrected from a 7×7 matrix to 6×6 (six case statuses).

## Tests

`tests/unit/test_claim_state_machine.py`, `tests/unit/test_bill_rules.py`,
`tests/api/test_ac06_ac08_case_lifecycle.py`, `tests/api/test_ac09_timeline_notifications.py`.
