# Learned Rules
<!-- Monotonic — rules are NEVER deleted. Only add new rules. -->
<!-- Format: Each rule includes Impact, Pattern, Mistake description, Anti-Pattern code, Better Approach code, Rule, and Applied-in fields. See .claude/skills/auto/SKILL.md SECTION 12 for full format. -->

## Rule 1 — Money terms of an existing case come from the pre-auth's recorded rule version
- **Impact:** HIGH. Underpaid settlements, which are append-only and cannot be corrected (FL-001)
- **Pattern:** reading "current" configuration on a path that must use a snapshot taken earlier
- **Mistake:** `bill_terms()` and `_settlement_input()` called `coverage_service.current_rule(policy)`
- **Anti-Pattern:** `rule = coverage_service.current_rule(conn, policy).rule  # in a bill/settlement path`
- **Better Approach:** `rule = case_service.case_rule(conn, case)  # pre-auth's recorded version`
- **Rule:** On any path that prices an existing case, resolve the rule version stored on the pre-auth. `current_rule()` is only for creating new pre-auths
- **Applied-in:** `src/service/case_service.py`, `src/service/settlement_service.py`; guarded by `tests/architecture/test_bill_cap_enforced.py::test_money_paths_never_read_the_current_rule_version`

## Rule 2 — Never invent error codes; take them from the spec
- **Impact:** MEDIUM. Clients get an undocumented contract (C-02)
- **Pattern:** a guard written during implementation with a fresh code name
- **Mistake:** `BusinessRuleError("PREAUTH_NOT_REJECTED", …)` for a disallowed state transition
- **Anti-Pattern:** `raise BusinessRuleError("SOMETHING_NEW", …)` with no matching spec line
- **Better Approach:** `raise InvalidClaimStateException(current, target)` (AM-R1), or amend the spec first
- **Rule:** Every error code raised in `src/` must appear in `specs/`. If a new one is needed, update the spec first (Spec-Is-Truth)
- **Applied-in:** `src/service/case_service.py::close`; `specs/admission_spec.md` AM-R6

## Rule 3 — Structural tests need a tripwire against vacuous passes
- **Impact:** HIGH. A guard test that checks zero items passes silently
- **Pattern:** iterate over discovered items and assert on each
- **Mistake:** route discovery returned 0 routes under FastAPI 0.142 (nested `_IncludedRouter`)
- **Anti-Pattern:** `for r in routes: assert guarded(r)` with nothing asserting that `routes` is non-empty
- **Better Approach:** flatten nested routers, and assert the known public routes are found (`test_public_allowlist_is_minimal`)
- **Rule:** Every discovery-based structural test asserts that discovery found what must exist
- **Applied-in:** `tests/architecture/test_controllers_guarded.py`

## Rule 4 — Do not satisfy a guard with a comment or a dead branch
- **Impact:** MEDIUM. The guard then checks text, not behaviour
- **Pattern:** a hook or architecture test greps for a token, and the code adds the token without the behaviour
- **Mistake:** `# require_roles(` comments on routes; `calculate_settlement(...) if False else ...` in `settle`
- **Rule:** When a guard is wrong, fix the guard (it parses the guard aliases from `deps.py`). When the code is wrong, fix the code. Never add tokens to please a check
- **Applied-in:** `.claude/hooks/role-boundary-check.sh`, `src/service/settlement_service.py`
