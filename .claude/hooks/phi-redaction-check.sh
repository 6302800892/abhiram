#!/usr/bin/env bash
# PostToolUse(Write|Edit): NFR-03 — block log statements that reference PHI fields.
# PHI = diagnosis, procedure, clinical notes, health history, date of birth, query responses.
HOOK_NAME="phi-redaction-check"
source "$(dirname "$0")/lib/hook-input.sh"

FILE="$(hook_file_path)"
case "$FILE" in
  */src/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0
# The redaction filter itself must name the PHI keys.
case "$FILE" in */src/config/logging_config.py) exit 0 ;; esac

# Whole identifiers only (same set as PHI_KEYS in src/config/logging_config.py), so event names such
# as "case.procedure_added" are fine while p.diagnosis_code / extra={"clinical_notes": ...} are blocked.
PHI='diagnosis|diagnosis_code|diagnosis_label|procedure|procedure_code|description|clinical_notes|health_history|date_of_birth|response_note'
HITS="$(grep -nE "(logger|logging|log)\.(debug|info|warning|error|exception|critical)\(.*\b($PHI)\b" "$FILE")"
if [ -n "$HITS" ]; then
  hook_block "PHI field referenced in a log call (NFR-03) in $FILE:
$HITS
Fix: log only ids/status (case_id, preauth_id, status). See .claude/skills/phi-safe-logging/SKILL.md"
fi
exit 0
