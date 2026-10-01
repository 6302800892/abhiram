#!/usr/bin/env bash
# PostToolUse(Write|Edit): AC-06 / AC-07 / NFR-08 guardrail.
#  1. Any code that computes a settlement must assert the invariant 0 <= settlement <= admissible.
#  2. Any code path that accepts a final bill must check it against pre_auth_amount + buffer.
HOOK_NAME="settlement-cap-check"
source "$(dirname "$0")/lib/hook-input.sh"

FILE="$(hook_file_path)"
case "$FILE" in
  */src/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

if grep -qE 'def calculate_settlement|admissible[[:space:]]*-[[:space:]]' "$FILE"; then
  if ! grep -q 'assert_settlement_invariant' "$FILE"; then
    hook_block "$FILE computes a settlement without assert_settlement_invariant (AC-07 invariant settlement_amount >= 0).
Fix: call assert_settlement_invariant(settlement, admissible) before returning. See .claude/skills/settlement-calculator/SKILL.md"
  fi
fi

# Only the service layer persists bills; controllers with the same function name just delegate.
case "$FILE" in */src/service/*.py) SERVICE_FILE=1 ;; *) SERVICE_FILE=0 ;; esac
if [ "$SERVICE_FILE" = 1 ] && grep -qE 'def submit_final_bill' "$FILE"; then
  if ! grep -qE 'ensure_bill_within_cap|bill_within_cap' "$FILE"; then
    hook_block "$FILE accepts a final bill without the cap check (AC-06: final_bill <= pre_auth_amount + buffer).
Fix: call ensure_bill_within_cap(...) from src/domain/bill_rules.py before persisting."
  fi
fi
exit 0
