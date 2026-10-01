# Feature Spec — Final-Bill Validation & Settlement

Owns: **AC-06** (cap rule), **AC-07** · Sprint: 3 ·
Domain modules: `src/domain/bill_rules.py`, `src/domain/settlement_calculator.py`, `src/domain/money.py`

## Overview

The settlement module validates the final bill against the authorised amount plus buffer. It then
computes the payout to the hospital, records it immutably, and fires a stubbed payment.

## Business Rules

| ID | Rule |
|---|---|
| ST-R1 | **Bill cap:** `cap = pre_auth_amount + pre_auth_amount × buffer_pct / 100`, quantized to 0.01. `final_bill ≤ cap` is required (equality allowed). `buffer_pct` comes from the **coverage-rule version recorded on the pre-auth** (PA-R3), never from the product's current version |
| ST-R2 | **Settlement:** with `D` = the deductible and `c` = the `copay_pct` of that same recorded rule version (so a bill is settled against the cap it was accepted under): |
| | `admissible = min(final_bill, cap)` |
| | `deductible_applied = min(D, admissible)` |
| | `copay = (admissible − deductible_applied) × c / 100`, quantized to 0.01 HALF_UP |
| | `settlement_amount = admissible − deductible_applied − copay` |
| ST-R3 | **Invariant:** `0 ≤ settlement_amount ≤ admissible`. The calculator asserts it and raises `SettlementInvariantError` if it is ever violated. A settlement is never persisted without passing this check |
| ST-R4 | All arithmetic is `Decimal`. A `float` input to the calculator raises `TypeError` (NFR-01) |
| ST-R5 | `settle` (INSURER) is allowed on DISCHARGED or DISPUTED cases that have a final bill. It persists one append-only settlement row `{case_id, pre_auth_amount, buffer_pct, cap, final_bill, admissible, deductible, copay, settlement_amount, payment_reference, settled_by, settled_at}`, triggers the stub payment (`payment_reference = "PAYSTUB-<case_id>-<n>"`), and moves the case to SETTLED |
| ST-R6 | Settling twice ⇒ 409 `CASE_SETTLED_IMMUTABLE`. Settlement rows cannot be updated or deleted (DB trigger) |
| ST-R7 | The settled amount reduces the policy's remaining sum insured |
| ST-R8 | `GET /api/cases/{id}/settlement` returns the breakdown (customer post-discharge summary): pre-auth amount, final bill, deductible, co-pay, paid amount |

## API

| Method | Path | Role |
|---|---|---|
| POST | `/api/cases/{id}/settle` | INSURER |
| GET | `/api/cases/{id}/settlement` | CUSTOMER (own), HOSPITAL (own), INSURER, ADMIN |

## Acceptance Criteria

### AC-06 — Bill cap
- **AC-06.5** `bill_within_cap(100000.00, 10, 110000.00)` is True; `110000.01` is False (unit).
- **AC-06.6** Buffer 0 % ⇒ cap equals pre_auth_amount exactly.

### AC-07 — Settlement formula and invariant
- **AC-07.1** Bill 90000.00 under cap 110000.00, deductible 5000.00, co-pay 10 % ⇒ admissible 90000.00, co-pay 8500.00, settlement 76500.00.
- **AC-07.2** Bill 120000.00 recorded above cap 110000.00 (defence in depth) ⇒ admissible is capped at 110000.00.
- **AC-07.3** Deductible 5000.00 larger than bill 3000.00 ⇒ settlement 0.00, never negative.
- **AC-07.4** Co-pay rounding: (1000.05 − 0) × 10 % = 100.005 → 100.01 (HALF_UP); settlement 900.04.
- **AC-07.5** A float argument raises `TypeError`.
- **AC-07.6** API: settling a discharged case returns the breakdown, the case becomes SETTLED, a payment reference starting with `PAYSTUB-` is returned, and remaining sum insured falls by the settled amount.
- **AC-07.7** Settling an already SETTLED case ⇒ 409 `CASE_SETTLED_IMMUTABLE`.

- **AC-07.8** Given a pre-auth approved under SILVER v1 (buffer 10 %, deductible 5000.00, co-pay 10 %), When the admin publishes v2 (buffer 5 %, deductible 0.00, co-pay 0 %) mid-cycle and a bill of 108000.00 is then submitted and settled, Then the bill is accepted against cap 110000.00 and the settlement is 92700.00 under v1 terms.

## Change log
- 2026-10-01 — ST-R1/ST-R2 now say explicitly that buffer, deductible and co-pay come from the pre-auth's recorded rule version. The Sprint 3 evaluator (failure C-01) showed that a mid-cycle rule publish changed the cap and the payout of already-approved cases. Fix loop FL-001 (`docs/fix-loops/FL-001-rule-version-mid-cycle.md`).

## Tests

`tests/unit/test_settlement_calculator.py`, `tests/unit/test_bill_rules.py`,
`tests/api/test_ac07_settlement.py`, `tests/architecture/test_settled_cases_immutable.py`.
