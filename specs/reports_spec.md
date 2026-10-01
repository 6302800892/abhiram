# Feature Spec — Reports

Sprint: 4 · Domain module: `src/domain/report_metrics.py`

## Overview

Operational reports for the insurer. They are read-only aggregations over append-only tables.

## Business Rules

| ID | Rule |
|---|---|
| RP-R1 | `preauth_turnaround_hours`: mean over decided pre-auths of (first non-PENDING decision time − submission time), in hours, rounded to 0.01. Null when nothing has been decided |
| RP-R2 | `settlement_volume`: `{count, total_amount}` of settlements |
| RP-R3 | `query_rate_by_hospital`: per hospital code, `{preauths, queried, rate}`, where `queried` = pre-auths that ever entered QUERY_RAISED, `rate = queried / preauths` rounded to 0.0001 |
| RP-R4 | `top_diagnoses`: up to 5 `{diagnosis_code, label, count}` by pre-auth count desc, ties broken by code asc. Codes and labels come from the ICD stub only; no free-text clinical notes |
| RP-R5 | `loss_ratio_by_product` = settled amount on the product's policies ÷ the sum of annual premiums of those policies, rounded to 0.0001 (HALF_UP). Products with no policies (premium total 0) are omitted, never divided by zero. `average_loss_ratio` = mean of the listed products' ratios (0.0001), or null when none. Decimal throughout |
| RP-R6 | `GET /api/reports/summary` requires INSURER or ADMIN |

## Acceptance Criteria (Given-When-Then)

- **RP-AC1** Given pre-auths decided after 2 h and 4 h, Then turnaround is 3.00.
- **RP-AC2** Given hospital A with 4 pre-auths of which 1 was queried, Then A's rate is 0.2500.
- **RP-AC3** Given settlements 76500.00 and 23500.00 on a product with premiums totalling 200000.00, Then its loss ratio is 0.5000.
- **RP-AC4** Given 6 distinct diagnoses, Then only the top 5 are returned, in order.
- **RP-AC5** Given a HOSPITAL token, Then `GET /api/reports/summary` returns 403.

## Change log
- 2026-10-01 — RP-R5: products without policies are omitted (division-by-zero gap found while writing the Sprint 4 tests).

## Tests

`tests/unit/test_report_metrics.py`, `tests/api/test_reports.py`.
