"""Schema facts other layers and architecture tests rely on."""

from __future__ import annotations

# NFR-02 / NFR-05: tables whose rows are never updated or deleted (DB triggers enforce it).
APPEND_ONLY_TABLES: tuple[str, ...] = (
    "coverage_rule_versions",
    "preauths",
    "preauth_decisions",
    "case_events",
    "notifications",
    "procedures",
    "final_bills",
    "settlements",
    "audit_records",
)
