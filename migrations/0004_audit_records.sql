-- 0004 — Sprint 4 (group D): append-only audit trail for privileged actions (AC-10, NFR-02).
-- Append-only file (NFR-05).

CREATE TABLE audit_records (
    id          INTEGER PRIMARY KEY,
    actor       TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    entity_type TEXT    NOT NULL,
    entity_id   INTEGER NOT NULL,
    from_status TEXT,
    to_status   TEXT,
    reason      TEXT    NOT NULL,
    occurred_at TEXT    NOT NULL
);

CREATE TRIGGER trg_audit_records_no_update BEFORE UPDATE ON audit_records
BEGIN SELECT RAISE(ABORT, 'append-only: audit_records'); END;
CREATE TRIGGER trg_audit_records_no_delete BEFORE DELETE ON audit_records
BEGIN SELECT RAISE(ABORT, 'append-only: audit_records'); END;

CREATE INDEX idx_audit_entity ON audit_records (entity_type, entity_id);
