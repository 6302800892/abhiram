-- 0003 — Sprint 3 (group C): case timeline, stub notifications, procedures, versioned final bills,
-- settlements. All five tables are append-only (NFR-02). Append-only file (NFR-05).

CREATE TABLE case_events (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES claim_cases (id),
    event_type  TEXT    NOT NULL CHECK (event_type IN ('PREAUTH_STATUS', 'CASE_STATUS', 'PROCEDURE', 'FINAL_BILL', 'SETTLEMENT')),
    from_status TEXT,
    to_status   TEXT,
    actor       TEXT    NOT NULL,
    occurred_at TEXT    NOT NULL,
    event_date  TEXT,              -- business date (admitted_on / discharged_on) when relevant
    note        TEXT               -- ids, codes and amounts only: never diagnosis/procedure text (NFR-03)
);

CREATE TABLE notifications (
    id            INTEGER PRIMARY KEY,
    case_id       INTEGER NOT NULL REFERENCES claim_cases (id),
    member_row_id INTEGER NOT NULL REFERENCES members (id),
    channel       TEXT    NOT NULL CHECK (channel = 'STUB'),
    event         TEXT    NOT NULL,
    to_status     TEXT    NOT NULL,
    message       TEXT    NOT NULL,
    created_at    TEXT    NOT NULL
);

CREATE TABLE procedures (
    id             INTEGER PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES claim_cases (id),
    procedure_code TEXT    NOT NULL,
    description    TEXT    NOT NULL,
    recorded_by    TEXT    NOT NULL,
    recorded_at    TEXT    NOT NULL
);

CREATE TABLE final_bills (
    id           INTEGER PRIMARY KEY,
    case_id      INTEGER NOT NULL REFERENCES claim_cases (id),
    version      INTEGER NOT NULL,
    amount       TEXT    NOT NULL,
    cap          TEXT    NOT NULL,   -- pre_auth_amount + buffer at submission time
    submitted_by TEXT    NOT NULL,
    submitted_at TEXT    NOT NULL,
    UNIQUE (case_id, version)
);

CREATE TABLE settlements (
    id                INTEGER PRIMARY KEY,
    case_id           INTEGER NOT NULL UNIQUE REFERENCES claim_cases (id),
    pre_auth_amount   TEXT    NOT NULL,
    buffer_pct        TEXT    NOT NULL,
    cap               TEXT    NOT NULL,
    final_bill        TEXT    NOT NULL,
    admissible        TEXT    NOT NULL,
    deductible        TEXT    NOT NULL,
    copay             TEXT    NOT NULL,
    settlement_amount TEXT    NOT NULL,
    payment_reference TEXT    NOT NULL,
    settled_by        TEXT    NOT NULL,
    settled_at        TEXT    NOT NULL
);

CREATE TRIGGER trg_case_events_no_update BEFORE UPDATE ON case_events
BEGIN SELECT RAISE(ABORT, 'append-only: case_events'); END;
CREATE TRIGGER trg_case_events_no_delete BEFORE DELETE ON case_events
BEGIN SELECT RAISE(ABORT, 'append-only: case_events'); END;
CREATE TRIGGER trg_notifications_no_update BEFORE UPDATE ON notifications
BEGIN SELECT RAISE(ABORT, 'append-only: notifications'); END;
CREATE TRIGGER trg_notifications_no_delete BEFORE DELETE ON notifications
BEGIN SELECT RAISE(ABORT, 'append-only: notifications'); END;
CREATE TRIGGER trg_procedures_no_update BEFORE UPDATE ON procedures
BEGIN SELECT RAISE(ABORT, 'append-only: procedures'); END;
CREATE TRIGGER trg_procedures_no_delete BEFORE DELETE ON procedures
BEGIN SELECT RAISE(ABORT, 'append-only: procedures'); END;
CREATE TRIGGER trg_final_bills_no_update BEFORE UPDATE ON final_bills
BEGIN SELECT RAISE(ABORT, 'append-only: final_bills'); END;
CREATE TRIGGER trg_final_bills_no_delete BEFORE DELETE ON final_bills
BEGIN SELECT RAISE(ABORT, 'append-only: final_bills'); END;
CREATE TRIGGER trg_settlements_no_update BEFORE UPDATE ON settlements
BEGIN SELECT RAISE(ABORT, 'append-only: settlements'); END;
CREATE TRIGGER trg_settlements_no_delete BEFORE DELETE ON settlements
BEGIN SELECT RAISE(ABORT, 'append-only: settlements'); END;

-- NFR-08 at the storage layer: a SETTLED case may only move to CLOSED.
CREATE TRIGGER trg_claim_cases_settled_locked BEFORE UPDATE OF status ON claim_cases
WHEN OLD.status = 'SETTLED' AND NEW.status <> 'CLOSED'
BEGIN SELECT RAISE(ABORT, 'settled case is immutable'); END;

CREATE INDEX idx_events_case ON case_events (case_id, id);
CREATE INDEX idx_notifications_member ON notifications (member_row_id, id);
CREATE INDEX idx_bills_case ON final_bills (case_id, version);
