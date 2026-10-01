# Evaluator Report — Group E (Sprint 5)

Date: 2026-10-01T16:40:00Z
VERDICT: PASS

Scope: `sprint-contracts/group-E.json` (E5-S1..E5-S4; F033–F038). The React + Vite portal in
`frontend/` is built to `frontend/dist` and served by FastAPI.
Environment: local mode. The committed suite starts its own backend on :8123. The independent probes
used a separate server, `uvicorn src.main:create_app --factory --port 8014`, with a fresh DB
`$TEMP/medicard-eval-E.db`, `MEDICARD_PBKDF2_ITERATIONS=1000` and
`MEDICARD_FRONTEND_DIST=frontend/dist`. `GET /health` returned 200 on the first attempt. The server was
stopped after the run and port 8014 is free. No source, test, spec, config, snapshot or
`features.json` file was modified. No git commands were run.

No contract check failed. The observations at the end are minor and none of them blocks the sprint.

## API Checks

- [PASS] api-401 `GET /` -> 200 `text/html; charset=utf-8` (SPA index)
- [PASS] api-402 `GET /api/does-not-exist` -> 404 `application/json` `{"error":{"code":"NOT_FOUND","message":"unknown API path"}}`, not the SPA
- [PASS] (probe) `GET /cases/1` (SPA deep link) -> 200 text/html
- [PASS] (probe) `GET /assets/missing.js` -> 404 JSON, so the SPA does not swallow missing assets
- [NOTE] (probe) `POST /api/does-not-exist` -> 405 `METHOD_NOT_ALLOWED` JSON, not 404. See Observation O-1.
- [PASS] (probe) `POST /api/preauths` with `estimated_cost "12.345"` -> 422 `VALIDATION_ERROR` ("at most 2 decimal places")
- [PASS] (probe) `POST /api/eligibility` for unknown MBR-9999 / POL-NOPE-0000 -> 200 `NOT_ELIGIBLE` `[ELG-POLICY-NOT-FOUND]`. This is a domain answer, not an error.

## Playwright Checks

### Committed suite (`frontend/e2e/*.spec.ts`)

- `npm run build`: PASS (tsc + vite build, 55 modules, JS 285.5 kB, gzip 89 kB).
- `npx playwright test --reporter=line`: **22 passed / 0 failed** (31.8 s), including the 2 `@visual` pixel tests.
- `npm run test:e2e:ci` (`--grep-invert @visual`): **20 passed / 0 failed** (30.4 s).

### Independent replays

I wrote these myself in `$TEMP/medicard-eval-E/probe*.cjs` and ran them headless in Chromium against
:8014. All data was created through the UI. The one exception is the final settlement call, which used
the API because the insurer workspace has no Settle control (see O-6).

- [PASS] **pw-001** Each role landed on the correct h1 and route: asha.verma -> "My coverage" `/customer`; cityhosp.desk -> "Hospital workspace" `/hospital`; adjudicator.priya -> "Adjudication queue" `/insurer`; admin.sam -> "Admin workspace" `/admin`.
- [PASS] **pw-002** MBR-1001/POL-SLV-0001 -> `ELIGIBLE`. MBR-3001/POL-SLV-0003 -> `NOT_ELIGIBLE` with `ELG-POLICY-INACTIVE` and `ELG-OUTSIDE-COVER-PERIOD`. Pre-auth K35.8 / 40000.00 -> `APPROVED` with `PA-AUTO-APPROVED`. Also: I21.9 / 100000.00 -> `PENDING` (CASE-000002) and Z41.1 / 10000.00 -> `REJECTED` (CASE-000003).
- [PASS] **pw-005a** The adjudicator approved CASE-000002 from the "Pending pre-authorizations" queue with PA-APPROVED-MANUAL. The status banner showed "CASE-000002 is now APPROVED" and the row left the queue. A REJECTED decision with PA-REJECTED-MANUAL also worked on a second case.
- [PASS] **pw-003** Ran the CASE-000002 journey: Admit -> ADMITTED, then added procedure 02703ZZ. A final bill of 110000.01 showed `role=alert` "BILL_EXCEEDS_CAP: final bill exceeds pre_auth_amount + 10% buffer". A bill exactly at the cap (110000.00) was accepted. Discharge -> DISCHARGED. Reloading `/cases/2` re-rendered the same case.
- [PASS] **pw-004** The customer saw the "My coverage" heading and POL-SLV-0001 with sum insured 500000.00 and remaining 405500.00. The timeline shows PENDING, APPROVED, ADMITTED, DISCHARGED and SETTLED. The settlement breakdown reads: admissible 110000.00, deductible 5000.00, co-pay 10500.00, paid 94500.00, PAYSTUB-2-1. That arithmetic is correct: (110000 - 5000) x 0.9 = 94500.
- [PASS] **pw-005b** The admin overrode REJECTED CASE-000003 to APPROVED with a reason. The status banner showed "CASE-000003 overridden to APPROVED". The "Audit log" heading appeared with a new row: admin.sam, PREAUTH_OVERRIDE, REJECTED -> APPROVED, the reason text. An empty reason and a whitespace-only reason were each refused with 422 `OVERRIDE_REASON_REQUIRED`, shown in `role=alert`.
- [PASS] **pw-006** At 375x800, `scrollWidth == innerWidth == 375` on all of these: hospital, the hospital case page, customer, customer case, insurer and admin. Hospital panels stack at 767px and sit side by side at 768px, which matches the E5-S1 "<768px single column" rule.
- [PASS] Keyboard only: Tab moves Username > Password > Sign in. Pressing Enter in Password submits and lands on "Hospital workspace". Focus shows a 2px solid teal outline.
- [PASS] A wrong password shows `role=alert` "INVALID_CREDENTIALS: invalid username or password" and stays on the login page.
- [PASS] RBAC routing: a hospital user who opens `/admin` or `/insurer` is redirected to `/hospital`. A customer who opens `/hospital` or `/admin` is redirected to `/customer`.
- [PASS] Sign out returns to the login page. `/customer` afterwards shows the login page, and session/local storage is empty.
- [PASS] An API error appears in `role=alert`: the 422 for a pre-auth amount of 12.345 shows "VALIDATION_ERROR: request validation failed".
- [PASS] Deep link `/cases/2` works on a fresh page after login. An unauthenticated deep link shows the login page.
- [PASS] While the eligibility request is in flight (I delayed it 1.2 s), the submit button is `disabled`.

## Design Checks

Design-critic rubric, internal-tool weighting. I scored from my own screenshots at 1280x800 and
375x800, which I viewed with the Read tool, plus measured DOM data.

| Criterion | Score | Min | Justification |
|---|---|---|---|
| visual_hierarchy | 7 | 6 | Each page has one h1, card sections with h2 titles, a teal header bar, status pills and the amount paid in bold green. It is dense, but raw ISO timestamps and code-prefixed messages make it look technical. |
| accessibility | 7 | 5 | `lang=en`, `main` and `nav` landmarks, every control labelled (0 unlabelled across 4 roles), contrast 5.07–15.6:1, visible focus ring, errors in `role=alert`, success in `role=status`. Tables that scroll horizontally cannot take keyboard focus, there is no `aria-busy`, and the document title stays the same on every page. |
| responsiveness | 7 | 6 | No page-level horizontal scroll at 375px on any workspace, and layout stacks below 768px. On the admin page at 375px, the Audit log and Override tables scroll inside their cards with columns clipped, and "Remove from network" wraps to 3 lines. |
| interaction_feedback | 6 | 5 | Buttons disable during requests, success banners name the case and new status, errors appear inline in red alerts, and the queue updates straight away. Button labels do not change to a busy state, and 422 messages are generic ("request validation failed") with no field detail. |

All four scores meet the contract minimums.

## Performance Checks

- [PASS] `GET /` over 20 sequential requests: min 7.4 ms, p50 8.0 ms, max 30.3 ms. The limit is 500 ms.
- The bundle is 285.5 kB JS (89 kB gzip) and 4.5 kB CSS.

## Architecture Checks

- [PASS] ui_layer: `fetch(` appears once in `frontend/src`, in `api.ts:23`. There is no axios, XMLHttpRequest, WebSocket or absolute http(s) URL. Every path the pages pass to `api.*` starts with `/api/`.
- [PASS] No business math in the UI: no `parseFloat`, `parseInt`, `Number(`, `toFixed`, `Math.` or numeric `+` in `frontend/src`. Money is displayed as the server strings, for example "94500.00".
- [PASS] No `dangerouslySetInnerHTML`. The session lives in `sessionStorage` and is cleared on sign out.
- [PASS] snapshots: `frontend/e2e/__snapshots__/` holds `login.spec.ts/login-page.aria.yml`, `responsive.spec.ts/hospital-workspace.aria.yml`, `visual.spec.ts/login.png` and `visual.spec.ts/hospital-mobile-panels.png`. I confirmed they exist on disk. I could not confirm they are committed, because git commands were not allowed.
- [PASS] `npm run typecheck` is clean.
- [PASS] Backend `pytest -q -p no:cacheprovider`: **423 passed, 1 skipped**.

## Tooling note

`.mcp.json` declares a Playwright MCP server, but no MCP browser tools were attached to this
evaluation session, so **no MCP tools were used**. Layer 2 replays used the Playwright library already
installed in `frontend/node_modules/playwright` (with `expect` from `@playwright/test`), driving headless
Chromium from Node scripts in `$TEMP/medicard-eval-E/`.

## Features Updated

I did not edit `features.json` because the caller told me not to. Based on this run, the recommended
state for all six is `passes: true`, `failure_reason: null`, `failure_layer: null`,
`last_evaluated: 2026-10-01T16:40:00Z`:

- F033 (E5-S1) Login routes each role to its workspace: PASS
- F034 (E5-S1) Layout is responsive at 375px: PASS
- F035 (E5-S2) Hospital checks eligibility and submits pre-auth in the UI: PASS
- F036 (E5-S3) Customer sees coverage and timeline: PASS
- F037 (E5-S4) Adjudicator approves from queue: PASS
- F038 (E5-S4) Admin overrides from UI and sees audit entry: PASS

## Evidence

- Probe scripts: `$TEMP/medicard-eval-E/probe.cjs` (23 checks; 22 passed. The "unknown member -> alert" check was built on a wrong assumption, because the API correctly returns 200 NOT_ELIGIBLE. I replaced it in probe2.), `probe2.cjs` (6/6), `probe3.cjs` (admin table overflow), `probe4.cjs` (contrast and focus), `probe5.cjs` (768px breakpoint). Results are in `results.json`.
- Screenshots in `$TEMP/medicard-eval-E/`: `login-1280`, `login-error-1280`, `hospital-1280`, `hospital-375`, `hospital-api-error-1280`, `case-1280`, `case-375`, `case-cap-error-1280`, `customer-1280`, `customer-375`, `customer-case-1280`, `customer-case-375`, `insurer-1280`, `insurer-375`, `admin-1280`, `admin-375`, `admin-375-scrolled` (.png).
- Server log: `$TEMP/medicard-eval-E/server.log`. Browser console errors were only the expected 422 and 401 resource errors from the negative probes.

## Observations

None of these blocks the sprint.

- **O-1** `POST /api/does-not-exist` returns 405 `METHOD_NOT_ALLOWED` instead of 404. This is probably the SPA's GET catch-all matching the path. The response is JSON, so api-402 (a GET) passes, but an unknown API path with a non-GET method should arguably return 404.
- **O-2** On the admin page at 375px, the Audit log, Overrides and Network tables are wider than their cards (534–577px in 309px). They scroll inside the card (`overflow-x:auto`), but the wrapper has no `tabindex`, role or label, so keyboard users can't scroll the Audit log, which has no focusable cells. "Remove from network" wraps to 3 lines (82x80px).
- **O-3** 422 validation errors show only "VALIDATION_ERROR: request validation failed" and drop the `details[].msg` the API returns (for example "amount may have at most 2 decimal places").
- **O-4** Messages are shown as `CODE: message` and timestamps as raw ISO `2026-10-01T16:27:11+00:00`. That works but is technical for the customer persona.
- **O-5** No `aria-busy` or busy label on submit buttons (they are only disabled), and `document.title` is "MediCard Portal" on every route.
- **O-6** The insurer workspace has no Settle action. Settlement is API-only, which is outside the E5 contract. The "All cases" table shows case status (PRE_AUTH) next to approved pre-auths, which could confuse adjudicators.
