-- 0002 — Sprint 2 (group B): claim cases, pre-authorization requests and their append-only
-- decision stream (NFR-02). Append-only file (NFR-05).

CREATE TABLE claim_cases (
    id            INTEGER PRIMARY KEY,
    policy_id     INTEGER NOT NULL REFERENCES policies (id),
    member_row_id INTEGER NOT NULL REFERENCES members (id),
    hospital_id   INTEGER NOT NULL REFERENCES hospitals (id),
    status        TEXT    NOT NULL CHECK (status IN ('PRE_AUTH', 'ADMITTED', 'DISCHARGED', 'SETTLED', 'DISPUTED', 'CLOSED')),
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE preauths (
    id                      INTEGER PRIMARY KEY,
    case_id                 INTEGER NOT NULL UNIQUE REFERENCES claim_cases (id),
    diagnosis_code          TEXT    NOT NULL,
    estimated_cost          TEXT    NOT NULL,
    expected_admission_date TEXT    NOT NULL,
    clinical_notes          TEXT,
    rule_product_id         INTEGER NOT NULL REFERENCES policy_products (id),
    rule_version            INTEGER NOT NULL,
    submitted_by            TEXT    NOT NULL,
    submitted_at            TEXT    NOT NULL
);

CREATE TRIGGER trg_preauths_no_update BEFORE UPDATE ON preauths
BEGIN SELECT RAISE(ABORT, 'append-only: preauths'); END;
CREATE TRIGGER trg_preauths_no_delete BEFORE DELETE ON preauths
BEGIN SELECT RAISE(ABORT, 'append-only: preauths'); END;

CREATE TABLE preauth_decisions (
    id              INTEGER PRIMARY KEY,
    preauth_id      INTEGER NOT NULL REFERENCES preauths (id),
    seq             INTEGER NOT NULL,
    status          TEXT    NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'PARTIALLY_APPROVED', 'REJECTED', 'QUERY_RAISED')),
    approved_amount TEXT,
    reason_codes    TEXT    NOT NULL,  -- JSON array, validated against the pre-auth's rule version
    note            TEXT,
    decided_by      TEXT    NOT NULL,
    decided_at      TEXT    NOT NULL,
    UNIQUE (preauth_id, seq)
);

CREATE TRIGGER trg_preauth_decisions_no_update BEFORE UPDATE ON preauth_decisions
BEGIN SELECT RAISE(ABORT, 'append-only: preauth_decisions'); END;
CREATE TRIGGER trg_preauth_decisions_no_delete BEFORE DELETE ON preauth_decisions
BEGIN SELECT RAISE(ABORT, 'append-only: preauth_decisions'); END;

CREATE INDEX idx_cases_hospital ON claim_cases (hospital_id);
CREATE INDEX idx_cases_member ON claim_cases (member_row_id);
CREATE INDEX idx_decisions_preauth ON preauth_decisions (preauth_id, seq);
