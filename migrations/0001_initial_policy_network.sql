-- 0001 — Sprint 1 (group A): users, customers, hospitals, products, versioned coverage rules,
-- policies and members. Append-only file (NFR-05): never edit; add 0002+ instead.
-- Money is stored as canonical decimal TEXT ("12345.67"), never REAL (NFR-01).

CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL CHECK (role IN ('CUSTOMER', 'HOSPITAL', 'INSURER', 'ADMIN')),
    display_name  TEXT    NOT NULL,
    hospital_id   INTEGER REFERENCES hospitals (id),
    created_at    TEXT    NOT NULL
);

CREATE TABLE customers (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL UNIQUE REFERENCES users (id),
    full_name  TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

CREATE TABLE hospitals (
    id         INTEGER PRIMARY KEY,
    code       TEXT    NOT NULL UNIQUE,
    name       TEXT    NOT NULL,
    city       TEXT    NOT NULL,
    in_network INTEGER NOT NULL CHECK (in_network IN (0, 1)),
    created_at TEXT    NOT NULL
);

CREATE TABLE policy_products (
    id             INTEGER PRIMARY KEY,
    code           TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    sum_insured    TEXT NOT NULL,
    annual_premium TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE coverage_rule_versions (
    id                      INTEGER PRIMARY KEY,
    product_id              INTEGER NOT NULL REFERENCES policy_products (id),
    version                 INTEGER NOT NULL,
    auto_approve_threshold  TEXT    NOT NULL,
    auto_approved_diagnoses TEXT    NOT NULL,  -- JSON array of ICD codes
    excluded_diagnoses      TEXT    NOT NULL,  -- JSON array of ICD codes
    per_claim_cap           TEXT    NOT NULL,
    buffer_pct              TEXT    NOT NULL,
    deductible              TEXT    NOT NULL,
    copay_pct               TEXT    NOT NULL,
    reason_codes            TEXT    NOT NULL,  -- JSON array (versioned reason catalogue)
    published_by            TEXT    NOT NULL,
    published_at            TEXT    NOT NULL,
    UNIQUE (product_id, version)
);

CREATE TRIGGER trg_coverage_rule_versions_no_update BEFORE UPDATE ON coverage_rule_versions
BEGIN SELECT RAISE(ABORT, 'append-only: coverage_rule_versions'); END;
CREATE TRIGGER trg_coverage_rule_versions_no_delete BEFORE DELETE ON coverage_rule_versions
BEGIN SELECT RAISE(ABORT, 'append-only: coverage_rule_versions'); END;

CREATE TABLE policies (
    id                INTEGER PRIMARY KEY,
    policy_number     TEXT    NOT NULL UNIQUE,
    product_id        INTEGER NOT NULL REFERENCES policy_products (id),
    status            TEXT    NOT NULL CHECK (status IN ('ACTIVE', 'LAPSED', 'CANCELLED')),
    cover_start       TEXT    NOT NULL,
    cover_end         TEXT    NOT NULL,
    sum_insured       TEXT    NOT NULL,
    annual_premium    TEXT    NOT NULL,
    prior_claims_paid TEXT    NOT NULL DEFAULT '0.00',  -- claims paid before onboarding (synthetic)
    created_at        TEXT    NOT NULL
);

CREATE TABLE members (
    id            INTEGER PRIMARY KEY,
    member_id     TEXT    NOT NULL UNIQUE,
    policy_id     INTEGER NOT NULL REFERENCES policies (id),
    full_name     TEXT    NOT NULL,
    date_of_birth TEXT    NOT NULL,
    relationship  TEXT    NOT NULL,
    customer_id   INTEGER REFERENCES customers (id)
);

CREATE INDEX idx_members_policy ON members (policy_id);
CREATE INDEX idx_rules_product ON coverage_rule_versions (product_id, version);
