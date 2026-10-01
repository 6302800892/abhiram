#!/usr/bin/env bash
# PostToolUse(Write|Edit): NFR-04 — every route handler in src/api/routes must declare a role
# dependency (require_roles / current_principal) unless explicitly marked `# public-endpoint`.
HOOK_NAME="role-boundary-check"
source "$(dirname "$0")/lib/hook-input.sh"

FILE="$(hook_file_path)"
case "$FILE" in
  */src/api/routes/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

# Split the file into blocks starting at each @router.<verb>( decorator; each block must mention
# require_roles( or current_principal or the public marker before the next decorator.
VIOLATIONS="$(awk '
  /^@router\.(get|post|put|patch|delete)\(/ {
    if (inblock && !guarded) print start
    inblock=1; guarded=0; start=FNR": "$0; next
  }
  inblock && /(require_roles\(|current_principal|# public-endpoint)/ { guarded=1 }
  END { if (inblock && !guarded) print start }
' "$FILE")"

if [ -n "$VIOLATIONS" ]; then
  hook_block "unguarded route(s) in $FILE (NFR-04 role boundary at controller layer):
$VIOLATIONS
Fix: add principal: Principal = Depends(require_roles(Role.X, ...)) or mark '# public-endpoint' (login/register/health only)."
fi
exit 0
