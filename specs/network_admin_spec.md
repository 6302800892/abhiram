# Feature Spec — Network & Coverage Admin

Owns: AC-01 (network list source), NFR-05 · Sprint: 1 · Domain module: `src/domain/coverage_rules.py`

## Overview

The insurer admin maintains network hospitals, policy products and **versioned** coverage rules.
Rules are never edited in place. A change publishes a new version, and existing pre-auths keep
the version they were decided under.

## Business Rules

| ID | Rule |
|---|---|
| NA-R1 | Hospital: `{code (unique, uppercase 3–12), name, city, in_network}`. `PATCH` may change only `in_network`. Hospitals are never deleted |
| NA-R2 | Product: `{code (unique), name, sum_insured > 0, annual_premium > 0}` |
| NA-R3 | Coverage-rule version fields: `auto_approve_threshold ≥ 0`, `auto_approved_diagnoses[]`, `excluded_diagnoses[]`, `per_claim_cap > 0`, `buffer_pct` in `[0, 50]`, `deductible ≥ 0`, `copay_pct` in `[0, 100]`, `reason_codes[]`. Every diagnosis code must exist in the ICD stub. The two diagnosis lists must not overlap |
| NA-R4 | Publishing creates version `n+1` for the product with `published_by` and `published_at`. Old versions are kept and never change (DB trigger; NFR-05 "policy migrations are append-only"). The **current** version is the highest version number |
| NA-R5 | The reason-code catalogue must contain every code used by the pre-auth engine and the workbench: `PA-SUBMITTED, PA-MANUAL-REVIEW, PA-AUTO-APPROVED, PA-AUTO-CAPPED, PA-REJECTED-EXCLUSION, PA-QUERY-UNKNOWN-DIAGNOSIS, PA-QUERY-ANSWERED, PA-QUERY-DOCUMENTS, PA-APPROVED-MANUAL, PA-PARTIAL-MANUAL, PA-REJECTED-MANUAL, PA-OVERRIDE`. Publishing without them ⇒ 422 `REASON_CATALOGUE_INCOMPLETE` |
| NA-R6 | Schema migrations live in `migrations/NNNN_name.sql`. They are applied in order and recorded with a SHA-256 checksum in `schema_migrations`. Startup fails with `MigrationTamperedError` if an applied file's checksum changes |
| NA-R7 | All admin endpoints require `ADMIN` |

## API

| Method | Path | Role |
|---|---|---|
| GET | `/api/network-hospitals` | any authenticated role (in-network only) |
| GET / POST | `/api/admin/hospitals` | ADMIN |
| PATCH | `/api/admin/hospitals/{code}` | ADMIN |
| GET / POST | `/api/admin/products` | ADMIN |
| GET / POST | `/api/admin/products/{code}/coverage-rules` | ADMIN (GET returns all versions) |

## Acceptance Criteria (Given-When-Then)

- **NA-AC1** Given an ADMIN, When creating hospital `SUNRISE` in network, Then it appears in `/api/network-hospitals` and in the customer coverage view (AC-01.5).
- **NA-AC2** Given an in-network hospital, When the ADMIN patches `in_network=false`, Then eligibility from that hospital returns `ELG-HOSPITAL-NOT-NETWORK`.
- **NA-AC3** Given product `SILVER` at version 1, When the ADMIN publishes new rules, Then version 2 is current and version 1 is unchanged.
- **NA-AC4** Given overlapping auto-approved and excluded lists, Then 422 `INVALID_COVERAGE_RULE`.
- **NA-AC5** Given a direct SQL `UPDATE` on `coverage_rule_versions`, Then SQLite aborts with `append-only`.
- **NA-AC6** Given an applied migration file whose content changes, When the app starts, Then `MigrationTamperedError`.
- **NA-AC7** Given a HOSPITAL token, When calling any `/api/admin/*`, Then 403.

## Tests

`tests/unit/test_coverage_rules.py`, `tests/unit/test_migrations.py`, `tests/api/test_network_admin.py`.
