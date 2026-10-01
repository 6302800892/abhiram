# MediCard — Architecture

## 1. System context (C4 level 1)

```mermaid
C4Context
    title MediCard cashless platform — system context
    Person(customer, "Customer / member", "Views coverage, case timeline, settlement")
    Person(hospital, "Network hospital desk", "Eligibility, pre-auth, admission, final bill")
    Person(adjudicator, "Insurer adjudicator", "Review queue, decisions, settlement")
    Person(admin, "Insurer admin", "Network & rules, overrides, audit, reports")
    System(medicard, "MediCard", "FastAPI + React portal, SQLite")
    System_Ext(payments, "Payment rail (stub)", "PAYSTUB-<case>-<n> reference")
    System_Ext(notify, "Notification channel (stub)", "Persisted STUB messages")
    Rel(customer, medicard, "HTTPS / browser")
    Rel(hospital, medicard, "HTTPS / browser")
    Rel(adjudicator, medicard, "HTTPS / browser")
    Rel(admin, medicard, "HTTPS / browser")
    Rel(medicard, payments, "trigger_stub_payment()")
    Rel(medicard, notify, "one message per state transition")
```

## 2. Layered structure (controllers / services / repositories / domain)

```mermaid
flowchart TB
    UI["UI — frontend/src (React)<br/>pages, components, api.ts"] -->|"/api JSON"| API
    subgraph Backend["src/ (Python package)"]
        API["api/ — controllers<br/>routes/*_routes.py · deps.py (require_roles) · schemas.py · errors.py · middleware.py"]
        SVC["service/ — use cases & transactions<br/>eligibility · preauth · adjudication · override · case · settlement · timeline · report · admin · seed"]
        REPO["repository/ — SQLite access<br/>db.py (migrations + checksum ledger) · *_repo.py · schema.py"]
        CFG["config/ — settings · JSON logging + PHI redaction"]
        DOM["domain/ — pure rules (no I/O)<br/>money · eligibility_rules · preauth_rules · preauth_state_machine · claim_state_machine · bill_rules · settlement_calculator · override_policy · coverage_rules · report_metrics · icd_stub"]
        API --> SVC --> REPO --> CFG --> DOM
        API --> DOM
        SVC --> DOM
        REPO --> DOM
    end
    REPO --> DB[("SQLite<br/>append-only triggers")]
```

| Layer | Package | Responsibility | Enforced by |
|---|---|---|---|
| Controllers | `src/api` | Auth boundary (`require_roles`), request validation (Money rejects float), error envelope, correlation ids | `role-boundary-check.sh`, `tests/architecture/test_controllers_guarded.py` |
| Services | `src/service` | Load facts, call domain rules, one transaction per use case, ownership checks (hospital sees own cases), timeline + notifications | import-linter "no fastapi in services" |
| Repositories | `src/repository` | Parameterised SQL, money as TEXT, append-only tables | `test_append_only.py`, DB triggers |
| Config | `src/config` | `MEDICARD_*` settings, JSON formatter, PHI filter | `phi-redaction-check.sh` |
| Domain | `src/domain` | Pure, deterministic business rules and state machines | import-linter "domain is pure", `test_layering.py` |

Import rule: a layer may import only layers below it (`lint-imports` contract
`src.main > src.api > src.service > src.repository > src.config > src.domain`).

## 3. Eligibility → settlement flow (sequence)

```mermaid
sequenceDiagram
    autonumber
    actor H as Hospital
    actor I as Adjudicator
    participant API as api (controllers)
    participant PA as preauth_service
    participant D as domain rules
    participant CS as case_service
    participant ST as settlement_service
    participant DB as SQLite (append-only)
    actor C as Customer

    H->>API: POST /api/eligibility {member_id, policy_number}
    API->>D: resolve_eligibility(...)  [AC-02]
    API-->>H: ELIGIBLE ["ELG-OK"]
    H->>API: POST /api/preauths {diagnosis, estimated_cost, admission date}
    API->>PA: submit()
    PA->>DB: case PRE_AUTH + pre-auth (rule_version) + decision PENDING/PA-SUBMITTED  [AC-03]
    PA->>D: decide_auto(estimate, diagnosis, rule v_n, remaining)  [AC-05]
    PA->>DB: decision APPROVED / PARTIAL / REJECTED / QUERY / PENDING + timeline + notification  [AC-04, AC-09]
    PA-->>C: STUB notification
    alt manual review
        I->>API: POST /api/preauths/{id}/decisions
        API->>DB: decision (reason codes ∈ rule v_n catalogue)
    end
    H->>API: POST /api/cases/{id}/admit → procedures → final-bill
    API->>CS: submit_final_bill()
    CS->>D: ensure_bill_within_cap(pre_auth_amount, buffer of rule v_n)  [AC-06]
    CS->>DB: final_bills v1..vn
    H->>API: POST /api/cases/{id}/discharge
    I->>API: POST /api/cases/{id}/settle
    API->>ST: settle()
    ST->>D: calculate_settlement() + assert_settlement_invariant  [AC-07]
    ST->>DB: settlement row + case SETTLED + event + notification
    ST-->>ST: trigger_stub_payment(PAYSTUB-…)
    C->>API: GET /api/cases/{id}/settlement  (post-discharge summary)
```

`rule v_n` is the coverage-rule version **recorded on the pre-auth**. A rule published later never
changes the cap or settlement of an existing case (ST-R1, fix loop FL-001).

## 4. State machines

```mermaid
stateDiagram-v2
    direction LR
    state "Pre-auth (AC-04)" as P {
        [*] --> PENDING
        PENDING --> APPROVED
        PENDING --> PARTIALLY_APPROVED
        PENDING --> REJECTED
        PENDING --> QUERY_RAISED
        QUERY_RAISED --> PENDING: hospital answers
        REJECTED --> APPROVED: ADMIN override (SYSTEM rejection only)
        QUERY_RAISED --> PARTIALLY_APPROVED: ADMIN override
    }
```

```mermaid
stateDiagram-v2
    direction LR
    [*] --> PRE_AUTH
    PRE_AUTH --> ADMITTED: approved pre-auth
    PRE_AUTH --> CLOSED: pre-auth rejected
    ADMITTED --> DISCHARGED
    DISCHARGED --> SETTLED
    DISCHARGED --> DISPUTED
    DISPUTED --> SETTLED
    DISPUTED --> CLOSED
    SETTLED --> CLOSED
    CLOSED --> [*]
```

Any other edge raises `InvalidClaimStateException` (409). A SETTLED case is mutation-locked at
three levels: `ensure_case_mutable` in the domain, the service guards, and a DB trigger
(`trg_claim_cases_settled_locked`).

## 5. Data model (append-only tables marked ⊕)

```mermaid
erDiagram
    POLICY_PRODUCTS ||--o{ COVERAGE_RULE_VERSIONS : "versions ⊕"
    POLICY_PRODUCTS ||--o{ POLICIES : issues
    POLICIES ||--o{ MEMBERS : covers
    CUSTOMERS ||--o{ MEMBERS : links
    USERS ||--o| CUSTOMERS : is
    HOSPITALS ||--o{ USERS : employs
    CLAIM_CASES ||--|| PREAUTHS : "has ⊕"
    PREAUTHS ||--o{ PREAUTH_DECISIONS : "stream ⊕"
    CLAIM_CASES ||--o{ CASE_EVENTS : "timeline ⊕"
    CLAIM_CASES ||--o{ NOTIFICATIONS : "stub ⊕"
    CLAIM_CASES ||--o{ PROCEDURES : "⊕"
    CLAIM_CASES ||--o{ FINAL_BILLS : "versions ⊕"
    CLAIM_CASES ||--o| SETTLEMENTS : "⊕"
    PREAUTHS ||--o{ AUDIT_RECORDS : "overrides ⊕"
```

## 6. Cross-cutting

| Concern | Mechanism |
|---|---|
| Money (NFR-01) | `Decimal` + `money.quantize` (HALF_UP, 0.01); TEXT columns; API `Money` type rejects JSON floats |
| PHI (NFR-03) | Event-style logs with ids only; `PhiRedactionFilter`; hook; log-capture tests |
| Logs (NFR-06) | `JsonFormatter` (UTC), `X-Correlation-ID` middleware, `case_id` context var, uvicorn routed through JSON too |
| Auth (NFR-04) | HMAC-signed bearer token (stdlib), PBKDF2 passwords, `require_roles` at the controller, ownership → 404 in services |
| Migrations (NFR-05) | `migrations/NNNN_*.sql` + SHA-256 ledger → `MigrationTamperedError`; hook blocks editing existing files |
| Health (NFR-07) | `GET /health`, tested to answer within 1 s of startup |
