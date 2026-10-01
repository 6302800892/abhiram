#!/usr/bin/env bash
# PostToolUse(Write|Edit): NFR-01 — money is fixed-point Decimal, never float, in domain/service.
HOOK_NAME="money-float-check"
source "$(dirname "$0")/lib/hook-input.sh"

FILE="$(hook_file_path)"
case "$FILE" in
  */src/domain/*.py|*/src/service/*.py|*/src/repository/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

HITS="$(grep -nE '(\bfloat\(|:[[:space:]]*float\b|->[[:space:]]*float\b|Decimal\([0-9]+\.[0-9]+\))' "$FILE" | grep -v 'noqa: money-float')"
if [ -n "$HITS" ]; then
  hook_block "float used for money in $FILE (NFR-01):
$HITS
Fix: use decimal.Decimal parsed from str via src.domain.money.to_money(); Decimal(\"0.10\") not Decimal(0.10)."
fi
exit 0
