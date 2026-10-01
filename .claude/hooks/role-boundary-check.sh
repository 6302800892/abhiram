#!/usr/bin/env bash
# PostToolUse(Write|Edit): NFR-04 — every route handler in src/api/routes must declare a role
# dependency (require_roles / current_principal, or one of the typed guard aliases declared in
# src/api/deps.py as `Name = Annotated[Principal, Depends(...)]`) unless marked `# public-endpoint`.
HOOK_NAME="role-boundary-check"
source "$(dirname "$0")/lib/hook-input.sh"

FILE="$(hook_file_path)"
case "$FILE" in
  */src/api/routes/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

# Guard aliases are discovered from deps.py so new guards need no hook change.
DEPS="$(dirname "$(dirname "$FILE")")/deps.py"
ALIASES="$(sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\) = Annotated\[Principal, Depends(.*/\1/p' "$DEPS" 2>/dev/null | paste -sd'|' -)"
[ -n "$ALIASES" ] || ALIASES="__no_aliases__"

# Split the file into blocks starting at each @router.<verb>( decorator; each block must mention a
# guard before the next decorator.
VIOLATIONS="$(awk -v aliases="$ALIASES" '
  BEGIN { guard = "(require_roles\\(|current_principal|# public-endpoint|(" aliases ")([^A-Za-z0-9_]|$))" }
  /^@router\.(get|post|put|patch|delete)\(/ {
    if (inblock && !guarded) print start
    inblock=1; guarded=0; start=FNR": "$0; next
  }
  inblock && $0 ~ guard { guarded=1 }
  END { if (inblock && !guarded) print start }
' "$FILE")"

if [ -n "$VIOLATIONS" ]; then
  hook_block "unguarded route(s) in $FILE (NFR-04 role boundary at controller layer):
$VIOLATIONS
Fix: take a guard alias from src/api/deps.py (e.g. principal: HospitalUser) or mark '# public-endpoint' (login/register/health only)."
fi
exit 0
