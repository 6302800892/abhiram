# Evaluator Report — Group A (Sprint 1)

Date: 2026-10-01T15:40:00Z
VERDICT: PASS

Contract: `sprint-contracts/group-A.json` (stories E1-S1..E1-S5) · Mode: lean · Verification mode: local

**Environment note:** port 8000 was already in use by an unrelated process
(`...\guard\backend\.venv\Scripts\python.exe -m app.run`, PID 25108). Against port 8000, `/health` returned
404 `{"error":{"code":"HTTP_404"...}}` from that other app. The evaluator did not stop it. MediCard ran on
**port 8010** instead, with a fresh throwaway DB (`$TEMP/medicard-eval-A.db`),
`MEDICARD_PBKDF2_ITERATIONS=1000` and `MEDICARD_FRONTEND_DIST=""`. Every path below ran against
`http://localhost:8010`.

## API Checks

Contract checks:

- [PASS] api-001 GET /health → 200 `{"status":"ok","service":"medicard"}`, 0.205 s
- [PASS] api-002 POST /api/auth/login (cityhosp.desk / Demo@1234) → 200, token + `"role":"HOSPITAL"`
- [PASS] api-003 POST /api/auth/login (wrong-pass) → 401 `INVALID_CREDENTIALS`
- [PASS] api-004 POST /api/customers/register (ravi.k) → 201 `{"customer_id":4,"username":"ravi.k"}`; ravi.k can then log in
- [PASS] api-005 POST /api/customers/me/policies (POL-SLV-0001 / MBR-1002 / 2015-09-03) → 201 coverage item (Rohan Verma, SILVER)
- [PASS] api-006 GET /api/customers/me/coverage → 200 with `sum_insured "500000.00"`, `remaining_sum_insured "500000.00"`, `exclusions[{code,label}]`, `network_hospitals` = CITYHOSP, LAKEVIEW, SUNSHINE (NONNET excluded)
- [PASS] api-007 POST /api/eligibility (MBR-1001 / POL-SLV-0001, cityhosp) → 200 `ELIGIBLE` `["ELG-OK"]`
- [PASS] api-008 POST /api/eligibility (MBR-3001 / POL-SLV-0003) → 200 `NOT_ELIGIBLE` `["ELG-POLICY-INACTIVE","ELG-OUTSIDE-COVER-PERIOD"]`
- [PASS] api-009 POST /api/eligibility with CUSTOMER token (asha.verma and ravi.k) → 403 `FORBIDDEN`
- [PASS] api-010 POST /api/admin/products/SILVER/coverage-rules (full NA-R5 catalogue) → 201 `version: 2`, `published_by: admin.sam`; GET afterwards lists v1 (seed values unchanged) and v2
- [PASS] api-011 PATCH /api/admin/hospitals/CITYHOSP `{"in_network":false}` → 200 `in_network:false`; eligibility from cityhosp.desk then → `NOT_ELIGIBLE ["ELG-HOSPITAL-NOT-NETWORK"]` (NA-AC2)
- [PASS] api-012 GET /api/admin/hospitals with HOSPITAL token → 403 `FORBIDDEN`

Adversarial probes (from the spec):

- [PASS] adv AC-01.2 POST /api/customers/register duplicate ravi.k → 409 `USERNAME_TAKEN`
- [PASS] adv EL-R1 POST /api/customers/register username "ab", password "short" → 422 `VALIDATION_ERROR` (both fields)
- [PASS] adv AC-01.4 POST /api/customers/me/policies wrong DOB 2015-09-04 → 422 `POLICY_LINK_MISMATCH`
- [PASS] adv EL-R2 POST /api/customers/me/policies MBR-1002 by a second customer (neha.s) → 409 `MEMBER_ALREADY_LINKED`
- [PASS] adv EL-R2 POST /api/customers/me/policies seed-linked MBR-1001 by neha.s → 409 `MEMBER_ALREADY_LINKED`
- [PASS] adv AC-02.2 POST /api/eligibility unknown POL-XXX-9999 → 200 `NOT_ELIGIBLE ["ELG-POLICY-NOT-FOUND"]`
- [PASS] adv AC-02.3 POST /api/eligibility MBR-2001 on POL-SLV-0001 → 200 `NOT_ELIGIBLE ["ELG-MEMBER-NOT-COVERED"]`
- [PASS] adv AC-02.5 POST /api/eligibility MBR-4001 / POL-SLV-0004 → 200 `NOT_ELIGIBLE ["ELG-SUM-INSURED-EXHAUSTED"]`, remaining `"0.00"`
- [PASS] adv AC-02.6 POST /api/eligibility from greenfield.desk (NONNET) → 200 `NOT_ELIGIBLE ["ELG-HOSPITAL-NOT-NETWORK"]`
- [PASS] adv EL-R6 POST /api/eligibility from greenfield.desk with body `hospital_code: CITYHOSP` → 422 (extra field rejected; the hospital cannot be spoofed)
- [PASS] adv POST /api/eligibility without a token → 401 `UNAUTHENTICATED`
- [PASS] adv GET /api/customers/me/coverage with a garbage bearer token → 401 `UNAUTHENTICATED invalid token`
- [PASS] adv GET /api/customers/me/coverage with HOSPITAL token → 403
- [PASS] adv POST /api/auth/login with unknown user → 401 `INVALID_CREDENTIALS` (same message as a wrong password)
- [PASS] adv NA-R5 POST coverage-rules with only `PA-SUBMITTED` → 422 `REASON_CATALOGUE_INCOMPLETE` (lists the 11 missing codes)
- [PASS] adv NA-AC4 POST coverage-rules where K35.8 is both auto-approved and excluded → 422 `INVALID_COVERAGE_RULE`
- [PASS] adv NFR-01 POST coverage-rules `auto_approve_threshold: 60000.5` (JSON float) → 422 `VALIDATION_ERROR` "money must be a decimal string"
- [PASS] adv NA-R3 POST coverage-rules unknown ICD QQ9.9 → 422 `INVALID_COVERAGE_RULE`
- [PASS] adv NA-R3 POST coverage-rules `buffer_pct "51"` → 422 `INVALID_COVERAGE_RULE`
- [PASS] adv NA-AC7 POST /api/admin/products/SILVER/coverage-rules with HOSPITAL token → 403
- [PASS] adv NA-AC7 GET /api/admin/products with HOSPITAL token → 403
- [PASS] adv NA-R7 GET /api/admin/hospitals with CUSTOMER token → 403; without a token → 401
- [PASS] adv NA-R1 PATCH /api/admin/hospitals/CITYHOSP `{"name":"Renamed"}` → 422 (only `in_network` allowed)
- [PASS] adv PATCH /api/admin/hospitals/NOPE → 404 `HOSPITAL_NOT_FOUND`
- [PASS] adv NA-AC1 POST /api/admin/hospitals SUNRISE → 201; it then appears in GET /api/network-hospitals and in the customer coverage `network_hospitals`
- [PASS] adv NA-AC5 direct SQL `UPDATE` / `DELETE` on `coverage_rule_versions` (throwaway DB) → `IntegrityError: append-only: coverage_rule_versions`
- [PASS] adv NFR-06 `X-Correlation-ID: eval-A-corr-12345` on /health → echoed in the response header; a generated id is returned when the header is absent
- [PASS] adv NFR-06 server stderr: the app's JSON log lines carry `correlation_id`; the `eval-A-corr-*` ids appear in the `http.request` and `eligibility.checked` lines
- [PASS] adv NFR-03 stderr scan for passwords, DOBs, member names, ICD codes and exclusion labels → no matches

## Performance Checks

- [PASS] GET /health → max 1000 ms. Observed 0.205–0.235 s via `localhost` (5 samples) and 0.006 s via `127.0.0.1` (3 samples). The first health-retry attempt got 200 right after `Application startup complete`.

## Architecture Checks

- [PASS] pytest (tests/unit, the 4 sprint-A API files, tests/architecture) → `189 passed, 1 skipped` (skip: `tests\architecture\test_layering.py:37: not a layered module`)
- [PASS] layering: `lint-imports` → `Contracts: 3 kept, 0 broken.`
- [PASS] typing: `mypy` (pyproject `strict = true`, packages = src) → `Success: no issues found in 45 source files`
- [PASS] lint: `ruff check .` → `All checks passed!`
- [PASS] hooks: `bash scripts/test-hooks.sh` → 10/10 ok, exit 0
- [PASS] migrations: live DB `schema_migrations` holds `0001_initial_policy_network.sql` with a SHA-256 checksum; `tests/unit/test_migrations.py::test_tampered_applied_migration_raises` passes (this evaluator did not edit a migration file, by mandate)
- [PASS] append_only: the live SQL UPDATE/DELETE aborted (above); `tests/architecture/test_append_only.py` passes
- [PASS] env_vars: `src/config/settings.py` reads `MEDICARD_SECRET`, else `secrets.token_urlsafe(32)` per process; grep finds no hardcoded `secret = "..."` literal in src

## Playwright Checks

- [SKIP] None in this contract (`playwright_checks: []`). Group A is API-only; Playwright MCP journeys start in group E.

## Features Updated

- F001: PASS
- F002: PASS
- F003: PASS
- F004: PASS
- F005: PASS
- F006: PASS
- F007: PASS
- F008: PASS
- F009: PASS
- F010: PASS
- F011: PASS

(The evaluator's mandate allowed writing only this report, so `features.json` was not edited. The orchestrator should apply these results.)

## Observations (non-blocking)

1. Linking the same member again by the **same** customer returns 201 (idempotent), not 409. The spec only requires 409 when a different customer links the member, so this conforms.
2. For `ELG-MEMBER-NOT-COVERED`, the response still returns the policy's `remaining_sum_insured` ("500000.00") to the hospital, even though the member is not on that policy. This is minor information disclosure about a policy the member does not belong to.
3. The customer coverage `exclusions` follow the **current** rule version. After v2 was published, ravi.k's view dropped F10.2. This is expected under NA-R4, but worth knowing.
4. Uvicorn's own access log (`INFO: 127.0.0.1:... "GET /health" 200`) and its startup lines are plain text, not JSON. The application loggers are JSON. Strict NFR-06 might want the uvicorn loggers routed through the JSON formatter.
5. The ~210 ms latency on `localhost` is Windows IPv6-then-IPv4 fallback, not server time (6 ms on 127.0.0.1; server `duration_ms` 1.6–4.5).
6. The `__pycache__` files are `cpython-313`, while `project-manifest.json` declares Python 3.12. The venv runs 3.13.
7. The token is a custom `base64(payload).HMAC` with a readable payload (`sub`, `role`, `exp`). It is not a defect, because it holds no PHI.

## Evidence

```
# Port 8000 occupied
127.0.0.1 PID=25108 C:\Users\Pandu\OneDrive\ドキュメント\guard\backend\.venv\Scripts\python.exe -m app.run
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)

# Startup (port 8010)
{"logger": "medicard.seed", "message": "seed.loaded", "correlation_id": null, "hospitals": 4, "policies": 5}
{"logger": "medicard.startup", "message": "startup.ready", "migrations_applied": 1, "seeded": true}
final status 200
{"status":"ok","service":"medicard"} | 200 0.211691s   (x5, 0.21-0.24s); 127.0.0.1: 200 0.006s

# Key responses
api-007 {"status":"ELIGIBLE","reason_codes":["ELG-OK"],"policy_number":"POL-SLV-0001","member_id":"MBR-1001","remaining_sum_insured":"500000.00"} 200
api-008 {"status":"NOT_ELIGIBLE","reason_codes":["ELG-POLICY-INACTIVE","ELG-OUTSIDE-COVER-PERIOD"],...} 200
api-009 {"error":{"code":"FORBIDDEN","message":"requires one of ['HOSPITAL']"}} 403
api-010 {"product_code":"SILVER","version":2,"published_by":"admin.sam",...} 201
api-011 {"code":"CITYHOSP","name":"City Care Hospital","city":"Hyderabad","in_network":false} 200
api-012 {"error":{"code":"FORBIDDEN","message":"requires one of ['ADMIN']"}} 403
float   {"error":{"code":"VALIDATION_ERROR",...,"msg":"Value error, money must be a decimal string such as \"1250.50\", not a JSON number with a fraction"}} 422
SQL     IntegrityError append-only: coverage_rule_versions <- UPDATE ... / DELETE ...
corr    x-correlation-id: eval-A-corr-12345
log     {"logger": "medicard.eligibility", "message": "eligibility.checked", "correlation_id": "eval-A-corr-elig", "hospital": "CITYHOSP", "status": "NOT_ELIGIBLE", "reason_codes": ["ELG-HOSPITAL-NOT-NETWORK"]}

# Gates
189 passed, 1 skipped in 7.17s
Contracts: 3 kept, 0 broken.
Success: no issues found in 45 source files
All checks passed!
test-hooks.sh: 10 ok lines, exit 0

# Shutdown
stopped 14552 (port 8010 listener count afterwards: 0)
```
