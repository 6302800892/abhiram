---
name: audit-tracer
description: Append-only audit and evidence model for MediCard (NFR-02, AC-10, AM-R7). Load before adding a table, an override path, or anything that writes decisions, bills, settlements, events or audit records.
---

# Audit Tracer

## Append-only tables (DB triggers abort UPDATE/DELETE)
`preauth_decisions`, `final_bills`, `settlements`, `case_events`, `audit_records`,
`coverage_rule_versions`, `notifications`.
They are listed in `src/repository/schema.py::APPEND_ONLY_TABLES`, and
`tests/architecture/test_append_only.py` checks each has both triggers.

## Trigger template (in a new migration file only)
```sql
CREATE TRIGGER trg_<table>_no_update BEFORE UPDATE ON <table>
BEGIN SELECT RAISE(ABORT, 'append-only: <table>'); END;
CREATE TRIGGER trg_<table>_no_delete BEFORE DELETE ON <table>
BEGIN SELECT RAISE(ABORT, 'append-only: <table>'); END;
```

## Current state = latest row
The current pre-auth status is the decision with the highest `seq` for that pre-auth. The current
final bill is the highest `version`.

## Override audit record (AC-10)
`{actor, action:"PREAUTH_OVERRIDE", entity_type:"preauth", entity_id, from_status, to_status, reason, occurred_at}`.
It is written in the **same** DB transaction as the `PA-OVERRIDE` decision. If either insert fails,
both roll back.

## Trace query
```sql
SELECT 'decision', seq, status, decided_by, decided_at FROM preauth_decisions WHERE preauth_id=?
UNION ALL SELECT 'event', id, to_status, actor, occurred_at FROM case_events WHERE case_id=?
ORDER BY 5;
```
