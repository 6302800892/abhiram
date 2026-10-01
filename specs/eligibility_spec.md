# Feature Spec — Eligibility & Coverage

Owns: **AC-01**, **AC-02** · Sprint: 1 · Domain module: `src/domain/eligibility_rules.py`

## Overview

A customer registers, links a policy, and sees the coverage. A network hospital checks whether a
member can be treated cashless.

## Business Rules

| ID | Rule |
|---|---|
| EL-R1 | Registration needs a unique `username` (3–40 chars), a `password` of at least 8 chars, and `full_name`. The password is stored as PBKDF2-SHA256 (never plaintext) |
| EL-R2 | Linking needs `policy_number`, `member_id` and `date_of_birth`. All three must match a seeded member on that policy, or the request fails with 422 `POLICY_LINK_MISMATCH`. A member can be linked to only one customer (409 `MEMBER_ALREADY_LINKED`) |
| EL-R3 | Coverage view shows per linked policy: product name, `sum_insured`, `remaining_sum_insured`, cover period, status, exclusions (ICD code + label), and the list of in-network hospitals |
| EL-R4 | Eligibility checks run in this order. **All** failing reasons are returned: |
| | `ELG-POLICY-NOT-FOUND` — no policy with that number (stops further checks) |
| | `ELG-MEMBER-NOT-COVERED` — member_id is not on that policy (stops further checks) |
| | `ELG-POLICY-INACTIVE` — policy status is not `ACTIVE` |
| | `ELG-OUTSIDE-COVER-PERIOD` — today is outside `[cover_start, cover_end]` |
| | `ELG-SUM-INSURED-EXHAUSTED` — remaining sum insured ≤ 0 |
| | `ELG-HOSPITAL-NOT-NETWORK` — the requesting hospital is not in network |
| EL-R5 | No failing reason ⇒ `ELIGIBLE` with reason code `ELG-OK`. Otherwise `NOT_ELIGIBLE` |
| EL-R6 | Only `HOSPITAL` users may call eligibility. The hospital is taken from the token, never from the body |
| EL-R7 | `remaining_sum_insured` is returned only when the member is on the policy. For `ELG-POLICY-NOT-FOUND` and `ELG-MEMBER-NOT-COVERED` it is `null`, so the hospital learns nothing about a policy it has no member on |

## API

| Method | Path | Role | Body → Response |
|---|---|---|---|
| POST | `/api/customers/register` | public | `{username,password,full_name}` → 201 `{customer_id}` |
| POST | `/api/customers/me/policies` | CUSTOMER | `{policy_number,member_id,date_of_birth}` → 201 coverage item |
| GET | `/api/customers/me/coverage` | CUSTOMER | → 200 `{policies:[…], network_hospitals:[…]}` |
| POST | `/api/eligibility` | HOSPITAL | `{member_id,policy_number}` → 200 `{status,reason_codes,policy_number,member_id,remaining_sum_insured}` |

## Acceptance Criteria

### AC-01 — Register, link and view coverage
- **AC-01.1** Given no user `ravi.k`, When `POST /api/customers/register` with a valid body, Then 201 and the customer can log in.
- **AC-01.2** Given an existing username, When registering again, Then 409 `USERNAME_TAKEN`.
- **AC-01.3** Given a registered customer, When linking with matching `policy_number`, `member_id` and `date_of_birth`, Then 201 and the policy appears in `GET /api/customers/me/coverage`.
- **AC-01.4** Given a wrong `date_of_birth`, When linking, Then 422 `POLICY_LINK_MISMATCH`.
- **AC-01.5** Given a linked policy, When viewing coverage, Then the response has `sum_insured`, `remaining_sum_insured`, `exclusions[]` (code + label), and `network_hospitals[]` containing only in-network hospitals.

### AC-02 — Eligibility lookup
- **AC-02.1** Given an active, in-period policy with remaining cover and an in-network hospital, When the hospital checks eligibility, Then `ELIGIBLE` with `["ELG-OK"]`.
- **AC-02.2** Given an unknown policy number, Then `NOT_ELIGIBLE` with `["ELG-POLICY-NOT-FOUND"]`.
- **AC-02.3** Given a member not on the policy, Then `NOT_ELIGIBLE` with `["ELG-MEMBER-NOT-COVERED"]`.
- **AC-02.4** Given a lapsed policy whose cover period has ended, Then `NOT_ELIGIBLE` with both `ELG-POLICY-INACTIVE` and `ELG-OUTSIDE-COVER-PERIOD`.
- **AC-02.5** Given an exhausted sum insured, Then `NOT_ELIGIBLE` including `ELG-SUM-INSURED-EXHAUSTED`.
- **AC-02.6** Given a hospital that is not in network, Then `NOT_ELIGIBLE` including `ELG-HOSPITAL-NOT-NETWORK`.
- **AC-02.7** Given a CUSTOMER token, When calling eligibility, Then 403.

- **AC-02.8** Given a member who is not on the policy, Then `remaining_sum_insured` is `null` (EL-R7).

## Change log
- 2026-10-01 — Added EL-R7 / AC-02.8 after the Sprint 1 evaluator found that a hospital could read
  the remaining cover of any policy number. This was a spec gap, not a code defect, so the spec
  was changed first and the code regenerated.

## Tests

`tests/unit/test_eligibility_rules.py` (rules), `tests/api/test_ac01_customer_coverage.py`,
`tests/api/test_ac02_eligibility.py`.
