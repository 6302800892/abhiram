# PR #5 — Fix loop FL-001 — settlement cap vs mid-cycle rule change

| | |
|---|---|
| Branch | `fix/fl-001-rule-version-snapshot` → `main` (`git merge --no-ff`) |
| Author | Claude Code agents (harness generator + MediCard domain agents), supervised by the AI-native engineer |
| ACs / NFRs | AC-06, AC-07, AC-08 |

## Summary
Evaluator round 1 found bill cap/settlement using the current rule version (C-01) and an invented error code (C-02). Spec amended (ST-R1/ST-R2/AM-R6), red reproduction, structural guard, fix (case_service.case_rule), evaluator round 2 PASS.

## Quality gates
tests/api/test_fix_loop_rule_version.py 4/4; architecture guard; full suite green

## Agent review
Evaluator C round 1 FAIL → round 2 PASS

Security review for the merged codebase: `specs/reviews/security-review.md` (VERDICT: PASS — 0 critical/high; SEC-06/07/08/09/11/12/17 fixed test-first).

## Checklist
- [x] Spec-Is-Truth: specs changed first where behaviour changed (see spec change logs)
- [x] Tests tagged with AC/NFR ids; red runs saved in `specs/test_artefacts/`
- [x] No hand-written production code; synthetic data only
- [x] Merged with `--no-ff` (no direct commits to `main`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
