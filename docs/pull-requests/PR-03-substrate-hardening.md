# PR #3 — Substrate hardening

| | |
|---|---|
| Branch | `chore/substrate-hardening` → `main` (`git merge --no-ff`) |
| Author | Claude Code agents (harness generator + MediCard domain agents), supervised by the AI-native engineer |
| ACs / NFRs | NFR-03, NFR-04, NFR-05, NFR-08 (guardrails) |

## Summary
Git-free migration hook; role hook discovers guard aliases from deps.py; PHI hook matches whole identifiers; settlement hook scoped to services; hook smoke tests extended; ac_trace.py; Poetry lock; CI e2e on Playwright v1.63.

## Quality gates
test-hooks.sh 13/13

## Agent review
n/a

Security review for the merged codebase: `specs/reviews/security-review.md` (VERDICT: PASS — 0 critical/high; SEC-06/07/08/09/11/12/17 fixed test-first).

## Checklist
- [x] Spec-Is-Truth: specs changed first where behaviour changed (see spec change logs)
- [x] Tests tagged with AC/NFR ids; red runs saved in `specs/test_artefacts/`
- [x] No hand-written production code; synthetic data only
- [x] Merged with `--no-ff` (no direct commits to `main`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
