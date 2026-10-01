#!/usr/bin/env bash
# PreToolUse(Write|Edit): NFR-05 — migrations are append-only. A migration file that already
# exists on disk may never be edited or overwritten; add the next migrations/NNNN_<name>.sql.
# (The runtime counterpart is the SHA-256 ledger in schema_migrations -> MigrationTamperedError.)
HOOK_NAME="append-only-migration-check"
source "$(dirname "$0")/lib/hook-input.sh"

FILE="$(hook_file_path)"
case "$FILE" in
  */migrations/*.sql) ;;
  *) exit 0 ;;
esac

BASENAME="$(basename "$FILE")"
if ! printf '%s' "$BASENAME" | grep -qE '^[0-9]{4}_[a-z0-9_]+\.sql$'; then
  hook_block "migration name '$BASENAME' must match NNNN_snake_case.sql"
fi

if [ -f "$FILE" ]; then
  hook_block "$BASENAME already exists and migrations are append-only (NFR-05).
Fix: create the next numbered migration file instead of editing this one."
fi
exit 0
