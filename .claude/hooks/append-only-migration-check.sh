#!/usr/bin/env bash
# PreToolUse(Write|Edit): NFR-05 — migrations are append-only. Editing or overwriting a migration
# that is already committed is blocked; add a new migrations/NNNN_<name>.sql instead.
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
  REPO="$(git -C "$(dirname "$FILE")" rev-parse --show-toplevel 2>/dev/null)"
  if [ -n "$REPO" ] && git -C "$REPO" ls-files --error-unmatch "$FILE" >/dev/null 2>&1; then
    hook_block "$BASENAME is a committed migration and is append-only (NFR-05).
Fix: create the next numbered migration file instead of editing this one."
  fi
fi
exit 0
