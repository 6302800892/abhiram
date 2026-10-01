# MediCard — Application Spec (root)

Business case: BC-AINE-017 · Status: approved · Spec-Is-Truth: when code and spec disagree, this
spec (and the feature specs it indexes) wins. Change the spec deliberately, then regenerate code.

## 1. Purpose

MediCard is a cashless hospitalization and settlement platform connecting customers, network
hospitals and the insurer. See `docs/business-case.md` for context and `specs/brd/brd.md` for the BRD.

## 2. Actors and Roles

| Role | Code | Sees |
|---|---|---|
| Customer | `CUSTOMER` | Own policies, own cases, own notifications |
| Hospital | `HOSPITAL` | Only cases raised by its own hospital (NFR-04) |
| Insurer adjudicator | `INSURER` | Adjudication queue, all cases, reports |
| Insurer admin | `ADMIN` | Everything the insurer sees, plus network / product / rule admin, overrides and the audit log |

## 3. Feature Specs

| Feature | Spec | ACs owned |
|---|---|---|
| Eligibility and coverage | `specs/eligibility_spec.md` | AC-01, AC-02 |
| Pre-authorization | `specs/preauth_spec.md` | AC-03, AC-04, AC-05 |
| Adjudication and override | `specs/adjudication_spec.md` | AC-04 (manual), AC-10 |
| Admission and case lifecycle | `specs/admission_spec.md` | AC-06 (bill entry), AC-08, AC-09 |
| Settlement | `specs/settlement_spec.md` | AC-06 (cap), AC-07 |
| Network and coverage admin | `specs/network_admin_spec.md` | AC-01 (network list), NFR-05 |
| Reports | `specs/reports_spec.md` | Reports (6.2) |

## 4. Acceptance Criteria

Every AC has at least one automated test whose name or `@pytest.mark.ac(...)` marker carries its
`AC-NN` identifier. Run `/ac-trace` to see the mapping.

| ID | Criterion | Spec |
|---|---|---|
| AC-01 | Customer can register and link to their health policy; coverage details (sum insured, exclusions, network hospitals) are visible | eligibility |
| AC-02 | Network hospital can look up customer eligibility by member_id and policy_id; system returns ELIGIBLE / NOT_ELIGIBLE with reason codes | eligibility |
| AC-03 | Hospital can submit a pre-authorization request with admission diagnosis, estimated_cost, and expected admission date; pre-auth enters PENDING state | preauth |
| AC-04 | Pre-auth lifecycle: PENDING → APPROVED / PARTIALLY_APPROVED / REJECTED / QUERY_RAISED, each carrying reason codes from the versioned policy | preauth, adjudication |
| AC-05 | Auto-approval: if estimated_cost ≤ configured threshold AND diagnosis is in the auto-approved list, the pre-auth is auto-approved up to the policy cap | preauth |
| AC-06 | Hospital can update the case post-admission with procedure details and the final bill; the final bill cannot exceed pre_auth_amount + buffer percentage | admission, settlement |
| AC-07 | Settlement amount = min(final_bill, pre_auth_amount + buffer) − deductibles − co-pay; invariant settlement_amount ≥ 0 | settlement |
| AC-08 | Cashless claim lifecycle PRE_AUTH → ADMITTED → DISCHARGED → SETTLED / DISPUTED → CLOSED; invalid transitions raise InvalidClaimStateException | admission |
| AC-09 | Customer receives a stubbed notification at every state transition; hospital and customer can both view the case status timeline | admission |
| AC-10 | Insurer admin can override an auto-rejected pre-auth (or escalated query) with reason; override is audited with actor and timestamp | adjudication |

## 5. Non-Functional Requirements

| ID | Requirement | Enforced by |
|---|---|---|
| NFR-01 | Money (estimated cost, final bill, deductible, co-pay, settlement) uses `decimal.Decimal`, quantized to 0.01 with ROUND_HALF_UP; never `float`. Responses carry money as strings. Requests accept decimal strings (max 2 places, absolute value below 10^13, otherwise 422 `INVALID_MONEY`) or whole-number JSON integers, which are exact; JSON numbers with a fraction are rejected (422) | `src/domain/money.py`, `tests/architecture/test_money_fixed_point.py`, `money-float-check.sh` hook |
| NFR-02 | Pre-auth decisions, bill submissions, settlements, case events and override audit records are append-only | SQLite `BEFORE UPDATE/DELETE` triggers, `tests/architecture/test_append_only.py` |
| NFR-03 | Diagnosis, procedure and health history never appear in logs in plaintext | `src/config/logging_config.py` redaction filter, `phi-redaction-check.sh` hook, NFR-03 test |
| NFR-04 | Role checks at the controller layer through `require_roles(...)`. Hospitals see only their own cases (others → 404) | `src/api/deps.py`, `tests/architecture/test_controllers_guarded.py`, `role-boundary-check.sh` hook |
| NFR-05 | DB migrations (`migrations/NNNN_*.sql`) and coverage-rule versions are append-only. An edited applied migration fails startup | migration checksum ledger, `append-only-migration-check.sh` hook |
| NFR-06 | Structured JSON logs (UTC timestamps) with `correlation_id` (from or echoed to the `X-Correlation-ID` header) and `case_id` when known | `src/api/middleware.py`, `src/config/logging_config.py` |
| NFR-07 | `GET /health` returns 200 within 1 second of successful startup | `tests/api/test_health.py` |
| NFR-08 | Architecture rules as tests: settled cases cannot be mutated; final bill cannot exceed pre_auth_amount + buffer; insurer override requires a role check and an audit record | `tests/architecture/` |

## 6. State Machines

### 6.1 Pre-auth (AC-04)

```
PENDING ──► APPROVED | PARTIALLY_APPROVED | REJECTED | QUERY_RAISED
QUERY_RAISED ──(hospital responds)──► PENDING
REJECTED (by SYSTEM) | QUERY_RAISED ──(ADMIN override, AC-10)──► APPROVED | PARTIALLY_APPROVED
```

APPROVED, PARTIALLY_APPROVED, and REJECTED by an adjudicator are terminal.

### 6.2 Claim case (AC-08)

```
PRE_AUTH ──► ADMITTED ──► DISCHARGED ──► SETTLED ──► CLOSED
   │                          │              ▲
   │                          └──► DISPUTED ─┴──► CLOSED
   └──► CLOSED   (only when the pre-auth is REJECTED)
```

Allowed transitions: PRE_AUTH→ADMITTED, PRE_AUTH→CLOSED, ADMITTED→DISCHARGED,
DISCHARGED→SETTLED, DISCHARGED→DISPUTED, DISPUTED→SETTLED, DISPUTED→CLOSED, SETTLED→CLOSED.
Any other transition raises `InvalidClaimStateException` (HTTP 409, code `INVALID_CLAIM_STATE`).

## 7. Conventions

- Base path `/api`. Auth: `Authorization: Bearer <token>` from `POST /api/auth/login`.
- Errors: `{"error": {"code": "<UPPER_SNAKE>", "message": "..."}}`. 401 unauthenticated, 403 wrong
  role, 404 not found or not yours, 409 state conflict, 422 validation or business-rule breach.
- Dates use ISO-8601. "Today" comes from an injectable clock (tests pin it).
- The ICD stub (`src/domain/icd_stub.py`) is the only diagnosis catalogue (brief 6.3).
- Seed data (`seed/seed_data.json`) is synthetic only.

### 7.1 Error catalogue

Every `error.code` the API can return. `tests/architecture/test_error_codes_specified.py` fails
the build if code raises one that is not listed in a spec.

| HTTP | Codes |
|---|---|
| 401 | `UNAUTHENTICATED` (missing, invalid or expired token), `INVALID_CREDENTIALS` (login) |
| 403 | `FORBIDDEN` (role not allowed at the controller) |
| 404 | `NOT_FOUND` (unknown path), `CASE_NOT_FOUND`, `PREAUTH_NOT_FOUND`, `POLICY_NOT_FOUND`, `HOSPITAL_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `NO_COVERAGE_RULE`. "Not yours" also returns 404 (NFR-04) |
| 405 | `METHOD_NOT_ALLOWED` |
| 409 | `USERNAME_TAKEN`, `MEMBER_ALREADY_LINKED`, `HOSPITAL_EXISTS`, `PRODUCT_EXISTS`, `INVALID_CLAIM_STATE`, `INVALID_PREAUTH_STATE`, `CASE_SETTLED_IMMUTABLE` |
| 422 (input) | `VALIDATION_ERROR` (schema), `INVALID_MONEY`, `INVALID_PERCENT`, `INVALID_USERNAME`, `WEAK_PASSWORD`, `FULL_NAME_REQUIRED`, `INVALID_HOSPITAL_CODE`, `INVALID_PRODUCT`, `INVALID_ESTIMATED_COST`, `ADMISSION_DATE_IN_PAST`, `INVALID_BILL_AMOUNT`, `DISPUTE_REASON_REQUIRED` |
| 422 (business rule) | `POLICY_LINK_MISMATCH`, `NOT_ELIGIBLE` (details: `reason_codes`), `INVALID_COVERAGE_RULE`, `REASON_CATALOGUE_INCOMPLETE`, `REASON_CODE_REQUIRED`, `UNKNOWN_REASON_CODE`, `INVALID_APPROVED_AMOUNT`, `PREAUTH_NOT_APPROVED`, `BILL_EXCEEDS_CAP` (details: `cap`, `final_bill`), `FINAL_BILL_REQUIRED`, `NOT_SETTLED`, `OVERRIDE_NOT_ALLOWED`, `OVERRIDE_REASON_REQUIRED` |
| 500 | `INTERNAL_ERROR`, `SETTLEMENT_INVARIANT_VIOLATED` (a defect; never persisted), `HTTP_ERROR` (other framework errors) |

## 8. Glossary

| Term | Meaning |
|---|---|
| Sum insured | Annual coverage limit of a policy |
| Remaining sum insured | Sum insured minus the sum of settled amounts on that policy |
| Policy cap | `min(per_claim_cap, remaining_sum_insured)` (BRD D-1) |
| pre_auth_amount | The approved amount of the pre-auth (latest APPROVED / PARTIALLY_APPROVED decision) |
| Buffer | `pre_auth_amount × buffer_pct / 100` |
| Deductible | Fixed amount per claim borne by the customer |
| Co-pay | `copay_pct %` of (admissible − deductible) borne by the customer (BRD D-2) |

## 9. Change log

| Date | Change | Trigger |
|---|---|---|
| 2026-10-01 | NFR-01 clarified: whole-number JSON integers are accepted as exact money input; fractional JSON numbers stay rejected | Sprint 2 evaluator observation 1 |
| 2026-10-01 | NFR-06 clarified: log timestamps are UTC ISO-8601, matching API timestamps | Sprint 2 evaluator observation 5 |
| 2026-10-01 | §7.1 error catalogue added; every raised code is now specified and enforced by an architecture test | Learned rule 2 (FL-001 / C-02) |
| 2026-10-01 | NFR-01 money upper bound (< 10^13); AD-R6 override requires PRE_AUTH case; token/secret hardening | Security review SEC-06/07/09/12 |
