#!/usr/bin/env bash
# Usage: bash scripts/test-hooks.sh [repo-root]   (exits non-zero if any hook misbehaves)
# Smoke test for MediCard hooks: run each hook on a violating and a clean file.
cd "${1:-$(dirname "$0")/..}" || exit 1
T="$(mktemp -d)"
mkdir -p "$T/src/service" "$T/src/api/routes" "$T/migrations"
cat > "$T/src/service/bad.py" <<'EOF'
import logging
logger = logging.getLogger(__name__)
logger.info("x %s", p.diagnosis_code)
x = float(a)
EOF
cat > "$T/src/service/good.py" <<'EOF'
import logging
logger = logging.getLogger(__name__)
logger.info("preauth.submitted", extra={"case_id": 1})
logger.info("case.procedure_added", extra={"case_id": 1})
EOF
cat > "$T/src/service/leak2.py" <<'EOF'
import logging
logger = logging.getLogger(__name__)
logger.info("debug", extra={"clinical_notes": notes})
EOF
cat > "$T/src/api/routes/r.py" <<'EOF'
@router.get("/a")
def a(principal = Depends(require_roles(Role.ADMIN))):
    pass

@router.post("/b")
def b():
    pass
EOF
cat > "$T/src/service/bill_bad.py" <<'EOF'
def submit_final_bill(conn, amount):
    bill_repo.append_bill(conn, amount=amount)
EOF
cat > "$T/src/api/routes/bill_route.py" <<'EOF'
@router.post("/x")
def submit_final_bill(principal: HospitalUser):
    return case_service.submit_final_bill()
EOF
cat > "$T/src/service/s.py" <<'EOF'
def calculate_settlement(x):
    return admissible - ded
EOF
run() {
  local expected="$1" hook="$2" target="$3" path code
  path="$target"
  if command -v cygpath >/dev/null 2>&1; then path="$(cygpath -w "$target")"; path="${path//\/\\}"; fi
  printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$path" | bash ".claude/hooks/$hook.sh" >/dev/null 2>&1
  code=$?
  if [ "$code" = "$expected" ]; then echo "ok   $hook $(basename "$target") -> $code"
  else echo "FAIL $hook $(basename "$target") -> $code (expected $expected)"; FAILED=1; fi
}
FAILED=0
run 2 phi-redaction-check "$T/src/service/bad.py"
run 0 phi-redaction-check "$T/src/service/good.py"
run 2 phi-redaction-check "$T/src/service/leak2.py"
run 2 money-float-check "$T/src/service/bad.py"
run 0 money-float-check "$T/src/service/good.py"
run 2 role-boundary-check "$T/src/api/routes/r.py"
run 2 settlement-cap-check "$T/src/service/s.py"
run 0 settlement-cap-check "$T/src/service/good.py"
run 2 settlement-cap-check "$T/src/service/bill_bad.py"
run 0 settlement-cap-check "$T/src/api/routes/bill_route.py"
run 2 append-only-migration-check "$T/migrations/bad-name.sql"
run 0 append-only-migration-check "$T/migrations/0001_init.sql"
echo "-- applied" > "$T/migrations/0002_existing.sql"
run 2 append-only-migration-check "$T/migrations/0002_existing.sql"
exit $FAILED
