# PR #2 — Requirements, specs and stories

| | |
|---|---|
| Branch | `docs/requirements-specs` → `main` (`git merge --no-ff`) |
| Author | Claude Code agents (harness generator + MediCard domain agents), supervised by the AI-native engineer |
| ACs / NFRs | AC-01..AC-10 (definition) |

## Summary
Harness /brd → specs/brd/brd.md; docs/business-case.md; specs/app_spec.md (AC-01..AC-10, NFR-01..NFR-08, state machines, error catalogue); 7 feature specs with Given-When-Then + AC-NN.x; /spec → 19 stories, 38 features.

## Quality gates
Spec review by planner role; ac_trace later proves every AC is tested

## Agent review
n/a

Security review for the merged codebase: `specs/reviews/security-review.md` (VERDICT: PASS — 0 critical/high; SEC-06/07/08/09/11/12/17 fixed test-first).

## Checklist
- [x] Spec-Is-Truth: specs changed first where behaviour changed (see spec change logs)
- [x] Tests tagged with AC/NFR ids; red runs saved in `specs/test_artefacts/`
- [x] No hand-written production code; synthetic data only
- [x] Merged with `--no-ff` (no direct commits to `main`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
