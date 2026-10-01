# Security Review — MediCard (BC-AINE-017) — 2026-10-01

Reviewer: harness `security-reviewer` agent (read-only review; the only file written is this report).
Scope: `src/` (api, service, repository, domain, config), `migrations/*.sql`, `frontend/src/`,
`seed/seed_data.json`, `.gitlab-ci.yml`, `scripts/`, `.claude/hooks/*.sh`, `.mcp.json`, `plugin.json`.
Baseline: `specs/app_spec.md` NFR-01..NFR-08 and the §7.1 error catalogue.

## Summary

The core security controls hold up under code reading and live probing. HMAC-SHA256 tokens use a
timing-safe compare and check expiry, and the role on the token is re-checked against the database
on every request. Every route has a role guard (NFR-04). Hospital and customer isolation returns
404 on all 9 case and pre-auth endpoints probed. Only ADMIN can override. All SQL is
parameterised. The SPA fallback blocks path traversal. No PHI appears in logs, error envelopes or
notifications (NFR-03). Money is Decimal-only, with append-only triggers and a DB-level lock on
settled cases (NFR-01/02/08).

No CRITICAL or HIGH issues were found. The four MEDIUM findings:

1. Policy linking can be brute-forced, which exposes a member's PHI.
2. Login has no throttling.
3. Seeding is on by default, so privileged demo accounts with the published `Demo@1234` password are created automatically.
4. The CI `claude-review` job gives `ANTHROPIC_API_KEY` to code the MR author controls.

The rest are LOW robustness and hardening issues (unhandled 500s, TOCTOU on state transitions,
unpinned tooling) and INFO notes.

| Severity | Count | Harness level |
|---|---|---|
| CRITICAL | 0 | BLOCK |
| HIGH | 0 | BLOCK |
| MEDIUM | 4 | WARN |
| LOW | 9 | INFO |
| INFO | 7 | INFO |

Overall harness verdict: **WARN** (no BLOCK findings).

VERDICT: PASS

## Findings

| ID | Severity | File:line | Rule / CWE | Finding | Recommendation |
|---|---|---|---|---|---|
| SEC-01 | MEDIUM | `src/service/customer_service.py:44-58`, `src/api/routes/customer_routes.py:24` | CWE-307 / CWE-799 (no limit on guessing attempts) | `POST /api/customers/me/policies` has no attempt limit. Member IDs (`MBR-1001`, `MBR-1002`, ...) and policy numbers (`POL-SLV-0001`, ...) follow guessable patterns, and DOB is the only secret (about 36.5k values per century). **Probe:** a newly registered customer swept DOBs for the unlinked dependant `MBR-1002` and got 201 on the 3rd try. That member's coverage now shows under the attacker's account, and through `members.customer_id` so would all of the member's cases (diagnosis code and label, procedures, bills, settlement) and notifications. | Throttle and lock out per customer and per member (for example 5 failures, then a cool-down). Write an audit record for each link attempt. Notify the policyholder when a member is linked. For a real deployment, require an out-of-band factor (OTP to the policyholder's registered contact). |
| SEC-02 | MEDIUM | `src/api/routes/auth_routes.py:14-22`, `src/service/auth_service.py:78-82` | CWE-307 | Login has no rate limiting or lockout. **Probe:** 30 consecutive bad passwords for `admin.sam` all returned 401, and the next correct login returned 200. Combined with SEC-03, this makes online guessing against ADMIN and INSURER accounts unbounded. | Add per-username and per-IP throttling with backoff, and log failed-login events (username hash plus correlation_id, no password). |
| SEC-03 | MEDIUM | `src/config/settings.py:25`, `src/service/seed_service.py:46-59`, `seed/seed_data.json:3`, `frontend/src/pages/LoginPage.tsx:40` | CWE-1392 (default credentials) / CWE-1188 (insecure default) | `seed_on_startup` defaults to `True`, so any fresh DB gets 8 accounts, including `admin.sam` (ADMIN) and `adjudicator.priya` (INSURER). They all share the password `Demo@1234`, and the login page prints it. The data is synthetic, as Rule 4 of CLAUDE.md requires, so this is acceptable for the demo. It becomes privileged default credentials in any deployment that does not set `MEDICARD_SEED=false`. | Default `MEDICARD_SEED` to false outside dev, or refuse to seed when `MEDICARD_SECRET` is set or the host is not loopback. Show the demo-credential hint only in a dev build (`import.meta.env.DEV`). Document a credential-rotation step in `init.sh`/README. |
| SEC-04 | MEDIUM | `.gitlab-ci.yml:69-85`, `scripts/sdk_mr_review.py:45-52` | CWE-829 / CWE-522 (secret exposed to untrusted code), prompt injection | `claude-review` runs on every MR pipeline whenever `ANTHROPIC_API_KEY` is visible. Several things in that job come from the MR branch: `scripts/sdk_mr_review.py` itself, project hooks and settings (`setting_sources=["project"]`), and `conftest.py`/tests (the `CLAUDE_PROMPT` path allows `poetry run pytest`). Anyone who can push an MR branch can read the key if the variable is not *protected*. The reviewer agent also reads attacker-controlled diff content while it holds `Write` and `permission_mode="acceptEdits"`, so a prompt injection can rewrite any workspace file (see SEC-05). | Mark `ANTHROPIC_API_KEY` as protected and masked, and run the job only for protected or trusted refs (or from a trusted, pinned copy of the reviewer script outside the MR tree). Drop `acceptEdits` and restrict `Write` to `specs/reviews/mr-review.md`, for example with a `PreToolUse` path guard that does not come from the MR branch. For `CLAUDE_PROMPT`, use the default permission mode with a read-only allowlist. |
| SEC-05 | LOW | `scripts/sdk_mr_review.py:69-71` | CWE-693 (protection mechanism failure, fail-open) | The gate reads `specs/reviews/mr-review.md` from the workspace and fails only if the text contains `VERDICT: FAIL`. An MR that commits its own report saying `VERDICT: PASS`, or an agent run that writes nothing useful while that file exists, passes the gate. | Delete the report before the run. Require an exact `VERDICT: PASS` line written during this run (check the mtime, or have the SDK return the verdict in the `ResultMessage`). Treat a missing verdict as a failure. |
| SEC-06 | LOW | `src/service/auth_service.py:66` | CWE-755 / CWE-20 | `hmac.compare_digest` on `str` raises `TypeError` for non-ASCII input. **Probe:** a bearer token whose signature contains latin-1 bytes returns **500 INTERNAL_ERROR** instead of 401. No bypass is possible, but it creates log noise and violates the §7.1 401 contract. | Compare bytes (`_sign(...).encode()` against `signature.encode("utf-8", "surrogateescape")`), or catch `TypeError` and raise `AuthenticationError("invalid token")`. |
| SEC-07 | LOW | `src/domain/money.py:258-266`, `src/api/schemas.py:106-112` | CWE-20 / CWE-755 | `to_money` accepts any finite Decimal, and `quantize()` then raises `decimal.InvalidOperation` once the value needs more than 28 significant digits. That error is not mapped. **Probe:** `{"amount": "1e30"}` and `"1e999999"` on `/final-bill` return **500**. This affects every `Money` field. Money integrity is not broken (nothing is persisted), but the response should be 422 `INVALID_MONEY`. | Catch `InvalidOperation` inside `to_money`, or enforce an upper bound (for example `< 10^13`) and raise `ValidationError("INVALID_MONEY", ...)`. |
| SEC-08 | LOW | `src/service/settlement_service.py:43-58`, `src/repository/case_repo.py:32`, `src/repository/preauth_repo.py:43-50`, `src/service/adjudication_service.py:65-79` | CWE-367 (TOCTOU) | State checks run on reads made before the write transaction opens (Python `sqlite3` uses deferred `BEGIN`), and `UPDATE claim_cases SET status=? WHERE id=?` has no condition on the current status. **Probe:** 4 concurrent `/settle` calls produced 1×200 and 3×**500** (`IntegrityError: UNIQUE settlements.case_id`). The UNIQUE constraint keeps money integrity (one settlement, one stub payment), but the clients get 500s. Concurrent adjudicator decisions are not protected by any constraint: two can both pass a `PENDING` check and append APPROVED and then REJECTED, which bypasses the pre-auth state machine (needs `seq` to serialise rather than collide). | Use `BEGIN IMMEDIATE` (`isolation_level=None` plus explicit begin) around read-check-write. Use conditional updates (`... WHERE id=? AND status=?`, checking `rowcount`). Re-check the latest decision `seq` inside the transaction. Map `IntegrityError` to 409. |
| SEC-09 | LOW | `src/service/override_service.py:34-38`, `src/domain/override_policy.py:89-111` | CWE-841 (workflow not enforced) | The override checks only the pre-auth decision, not the case status. **Probe:** an auto-rejected pre-auth (excluded `Z41.1`) was closed by INSURER (`PRE_AUTH→CLOSED`), and ADMIN could still override it to `APPROVED`. The case stays `CLOSED`, so no money moves, but the record now shows an approved pre-auth on a closed case. The override was correctly audited. | Allow overrides only while the case is `PRE_AUTH`; otherwise return 409 `INVALID_CLAIM_STATE`. Add an AD-R6 clause to the spec first (Spec-Is-Truth). |
| SEC-10 | LOW | `src/service/customer_service.py:50-58` | CWE-204 (response discrepancy) | A wrong DOB returns 422 `POLICY_LINK_MISMATCH` and the right DOB returns 409 `MEMBER_ALREADY_LINKED` (probed against `MBR-1001`). An attacker can therefore confirm the DOB (PHI) of members who are already linked, even though linking itself is refused. This ordering follows EL-R2, but it is an oracle. | Have EL-R2 return the same response for "already linked" and "mismatch", or check linkage before validating DOB. Throttle per SEC-01. |
| SEC-11 | LOW | `src/service/auth_service.py:80-81` | CWE-208 (timing discrepancy, user enumeration) | For an unknown username, login skips PBKDF2, so it is measurably faster. The probe at 1,000 iterations showed 6.9 ms vs 8.0 ms. At the production 200,000 iterations the gap grows roughly in proportion (to tens of ms or more), which makes it easy to tell which usernames exist. | When the row is missing, run `verify_password` against a fixed dummy hash. |
| SEC-12 | LOW | `src/config/settings.py:38` | CWE-1391 / CWE-326 (weak key accepted) | `MEDICARD_SECRET` is taken as given, so an empty or short value (for example `MEDICARD_SECRET=`) becomes the HMAC key. Unset is safe (random 32-byte key per process). | At startup, reject a secret shorter than 32 bytes and fail fast. |
| SEC-13 | LOW | `.mcp.json:6`, `.gitlab-ci.yml:21,56,76-77`, `pyproject.toml:8-10` | CWE-1357 / CWE-829 (unpinned supply chain) | `npx -y @playwright/mcp@latest` fetches and runs whatever is latest every session. In CI, `@anthropic-ai/claude-code`, `claude-agent-sdk` and `poetry>=2.0` are unpinned, and images are pinned by tag only. App dependencies are locked (`poetry.lock`, `frontend/package-lock.json`). | Pin `@playwright/mcp@<version>`, `@anthropic-ai/claude-code@<version>`, `claude-agent-sdk==<version>` and `poetry==<version>`. Pin images by digest. Enable Renovate or Dependabot for controlled bumps. |
| SEC-14 | LOW | `src/service/customer_service.py:27-28` | CWE-521 | The only password rule is length ≥ 8 (probe: `aaaaaaaa` was accepted). There is no deny-list or breached-password check. | Add a common-password deny-list and a longer minimum (for example 12). Specify it in EL-R1 first. |
| SEC-15 | INFO | `src/main.py:62`, `src/api/static.py:19-26` | Missing security headers / CWE-1021 | Responses have no `Content-Security-Policy`, `X-Frame-Options`/`frame-ancestors` or `X-Content-Type-Options`. `/docs` and `/openapi.json` are public (200). No CORS middleware is installed (cross-origin preflight → 405), which is the safe default. | Add a small header middleware (CSP `default-src 'self'`, `frame-ancestors 'none'`, `nosniff`). Disable `docs_url`/`openapi_url` in production. |
| SEC-16 | INFO | `frontend/src/auth.tsx:24-51`, `frontend/src/api.ts:3-23` | Token storage / CWE-922 | The bearer token sits in `sessionStorage` and in module memory, so any XSS could read it. This is mitigated: React escapes all output, there is no `dangerouslySetInnerHTML`/`innerHTML`/`eval` in `frontend/src`, and no third-party scripts are loaded. CSRF does not apply: there are no cookies, and auth relies only on the `Authorization` header. There is no server-side revocation (12 h TTL), but a role change does invalidate the token (`load_principal` re-checks the role). | Keep it as is for the demo. Add a CSP (SEC-15). Consider a shorter TTL and a server-side logout or deny-list for production. |
| SEC-17 | INFO | `src/service/case_service.py:29-33` | CWE-639 (defence in depth) | In `load_visible`, a CUSTOMER principal with `customer_id is None` would pass the check for cases whose member is unlinked (`None != None` is false). This cannot happen today: every CUSTOMER user gets a `customers` row in the same transaction (`customer_service.py:34-39`, `seed_service.py:55-58`), and `list_cases` already returns `[]` for that case. | Treat `principal.customer_id is None` as hidden, mirroring `list_cases`. |
| SEC-18 | INFO | `.claude/hooks/phi-redaction-check.sh:19`, `src/config/logging_config.py:38-45` | Guardrail coverage | The hook only matches a log call and a PHI identifier on the same line, so multi-line `logger.info(...)` calls slip past it. The runtime filter redacts by `extra` key name, not by value or message text. Current code is clean (see "Verified sound"). Hook input handling is safe: the payload is only `printf '%s'`-ed into `sed`/`grep`/`case`, all quoted, with no `eval`. `${CLAUDE_PLUGIN_ROOT}` is unquoted in `medicard-hooks.json`, which breaks on paths with spaces. | Make the hook scan whole logger call expressions (an AST check in `tests/architecture/` is more reliable). Quote `"${CLAUDE_PLUGIN_ROOT}"`. |
| SEC-19 | INFO | `src/service/case_service.py:100-101`, `migrations/0003_admission_settlement.sql` (`case_events.note` comment) | NFR-03 (scope note) | The timeline note stores the procedure code (`procedure 0DTJ4ZZ recorded`), which customers and the treating hospital can see. It is never logged. The `case_events.note` column comment says "never diagnosis/procedure text", and a code is not text, but the code is still clinical data in a widely read stream. | Confirm the intent in the admission spec, or replace it with "procedure #n recorded". |
| SEC-20 | INFO | `seed/seed_data.json:3`, `frontend/e2e/support.ts:4`, `tests/conftest.py` | Secrets scan | A detect-secrets-style grep found only the synthetic demo password `Demo@1234` (seed, tests, e2e, README, built bundle). No API keys, tokens or private keys are in source. `.env*` is git-ignored, and `.env.example` holds only a placeholder. The demo password is classified as test-fixture data, not a leaked secret (production risk covered by SEC-03). | None beyond SEC-03. |
| SEC-21 | INFO | `scripts/sdk_sprint_runner.py:43-44` | Least privilege | The local sprint runner grants unrestricted `Bash` with `acceptEdits`. This is acceptable for a developer-run harness, but it must never run in CI or on untrusted branches. | Document it as local-only, or restrict Bash to a prefix allowlist. |

## Verified as sound (evidence)

**Authentication and tokens**
- Tokens are `base64url(payload).HMAC-SHA256(payload)` and verified with `hmac.compare_digest` (`auth_service.py:66`). Expiry is enforced (`:74`). The signature is checked before any JSON parsing.
- Probes returned 401 for: a tampered `role→ADMIN` with the original signature, a tampered `exp`, a stripped signature, and a garbage token. The only 500 was the non-ASCII input in SEC-06.
- `load_principal` re-reads the user and rejects the token if the DB role differs from the token's (`auth_service.py:88-89`). Hospital and customer binding always comes from the DB, never from the token.
- Passwords use PBKDF2-HMAC-SHA256 with a 16-byte random salt and 200,000 iterations by default (`settings.py:24`, `auth_service.py:28-31`). Verification is constant-time.
- With `MEDICARD_SECRET` unset, the key is a per-process `secrets.token_urlsafe(32)`. Nothing is hard-coded.

**Authorization (NFR-04)**
- Every handler in `src/api/routes/*.py` declares a guard alias from `deps.py`. The only exceptions are `login`, `register`, `/health` and the SPA shell, each marked `# public-endpoint`.
- Probes returned 403 for:
  - INSURER: override, audit log, publish rule
  - HOSPITAL: decide, reports
  - CUSTOMER: adjudication queue, pre-auth view
  - ADMIN: settle (INSURER only)
- ADMIN override is reachable only through `AdminUser`.
- Hospital isolation: SUNSHINE got 404 on CITYHOSP's case for `GET case`, `timeline`, `settlement`, `preauth`, and `POST admit`, `procedures`, `final-bill`, `discharge`, `query-response`. The case also did not appear in SUNSHINE's lists.
- Customer isolation: `kiran.rao` got 404 on `asha.verma`'s case, timeline and settlement, and saw none of her cases or notifications. Asha got 200 on her own case.
- The hospital comes from the token for eligibility and pre-auth (EL-R6). A body `hospital_code` is rejected with 422 because `extra="forbid"`.

**Injection**
- Every `conn.execute` in `src/repository/` uses `?` or named placeholders. The f-strings only join constant SQL fragments (`CASE_SELECT`, `PREAUTH_SELECT`, `CURRENT_STATUS`, fixed `WHERE` clauses) and never user values.
- `executescript` runs only on migration files.
- No shell or subprocess calls take request data.
- SPA fallback (`static.py:23-25`) uses `resolve()` and then checks `root in candidate.parents`. In-process probes all served the index shell or 404 and never the planted outside or sibling file: `../`, `%2e%2e/`, `..%2f`, `..%5c`, a sibling `dist-evil/`, absolute `C:/...` paths, and `/assets/..%2f..%2f`. `api/*` gets a JSON 404.

**PHI (NFR-03)**
- Every `logger.*` call in `src/` logs only ids, status, reason codes or amounts. `PhiRedactionFilter` and `JsonFormatter` redact PHI-named extras, and exceptions log only the type name.
- Live log check: after submitting pre-auths with `clinical_notes` canaries, diagnoses `K35.8`/`Z41.1`, and DOB link attempts, `server.log` (878 lines) had zero matches for the canaries, diagnosis codes or labels, DOBs, member names or passwords.
- Validation errors echo only `loc` and `msg`, never the input (the canary was not echoed in the 422).
- Pre-auth views never return `clinical_notes` or decision notes.
- Notifications carry only the case number and status (`timeline_service.py:17-18`).

**Money and integrity (NFR-01/02/08)**
- Float JSON money is rejected (422). NaN, more than 2 decimal places and negative values are rejected, and `NaN` percent is rejected by pydantic.
- Money is stored as TEXT. The cap is inclusive: `44000.00` was accepted and `44000.01` rejected with `BILL_EXCEEDS_CAP`.
- Settlement asserts `0 ≤ settlement ≤ admissible` before persisting.
- `BEFORE UPDATE/DELETE` triggers make all 9 tables in `APPEND_ONLY_TABLES` append-only.
- `trg_claim_cases_settled_locked` lets a SETTLED case move only to CLOSED. After settlement, the probe got 409 `CASE_SETTLED_IMMUTABLE` for a new final bill and a re-settle, and 409 for a dispute. `settlements.case_id UNIQUE` kept a single settlement and a single stub payment under 4 concurrent settles.
- The override decision and its `audit_records` row are written in one `with conn:` transaction. The probe confirmed the audit row `PREAUTH_OVERRIDE REJECTED→APPROVED`.
- The migration checksum ledger rejects edited migrations (NFR-05).

**Frontend and dependencies**
- No `dangerouslySetInnerHTML`, `innerHTML`, `eval` or `document.write` in `frontend/src`. All HTTP goes through `api.ts` with fixed same-origin paths.
- `npm audit` (prod and dev, 128 packages) reported 0 vulnerabilities. Python dependencies are locked in `poetry.lock` (56 packages): FastAPI 0.142.2, Starlette 1.7.0, uvicorn 0.54.0, pydantic 2.13.5.

**Correlation id**
- Echoed and truncated to 64 characters (probe: 500 characters in, 64 out). Logs are written as JSON, so log lines cannot be injected.

## Probes run

1. Test suite: `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider` gave **424 passed, 1 skipped**.
2. Throwaway server: `MEDICARD_DB_PATH=$TEMP/medicard-sec.db MEDICARD_PBKDF2_ITERATIONS=1000 MEDICARD_FRONTEND_DIST="" uvicorn src.main:create_app --factory --port 8016`. It was stopped after probing.
3. `$TEMP/medicard-sec/probe.py`: token forgery and tamper checks, login throttling and timing, the role matrix, the cross-hospital and cross-customer IDOR matrix, money edge cases, the cap boundary, 4 concurrent settles, and post-settlement mutation attempts.
4. `$TEMP/medicard-sec/probe2.py`: override after `PRE_AUTH→CLOSED` (SEC-09), the DOB oracle on a linked member (SEC-10), and the DOB brute force on an unlinked dependant (SEC-01).
5. `$TEMP/medicard-sec/probe3.py`: SPA fallback path traversal with an in-process `TestClient`, a throwaway `dist/`, a planted outside file and a sibling directory.
6. `$TEMP/medicard-sec/probe4.py`: validation-error echo, security headers, `/docs` exposure, correlation-id length, CORS preflight, NaN percent, weak password.
7. Server-log review: grepped for PHI canaries (0 hits). Causes of the 500s: `TypeError` (SEC-06), `InvalidOperation` ×2 (SEC-07), `IntegrityError` ×3 (SEC-08).
8. Static scans: grep for SQL construction, hard-coded secrets, unsafe HTML in React, PHI in logger calls, and shell use in hooks. `npm audit --json` was run in `frontend/`.

No source, test, spec or config files were modified. No git commands were run.
