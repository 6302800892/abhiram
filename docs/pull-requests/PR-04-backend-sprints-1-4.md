# PR #4 — Backend sprints 1–4 (groups A–D)

| | |
|---|---|
| Branch | `feat/backend-sprints-1-4` → `main` (`git merge --no-ff`) |
| Author | Claude Code agents (harness generator + MediCard domain agents), supervised by the AI-native engineer |
| ACs / NFRs | AC-01..AC-10, NFR-01..NFR-08 |

## Summary
Domain rules (eligibility, auto-decider, state machines, bill cap, settlement, override policy, report metrics), append-only migrations 0001–0004 with checksum ledger, repositories, services, FastAPI controllers with role guards, JSON logging with PHI redaction, seed data.

## Quality gates
pytest 424 passed (94.96 % coverage) · lint-imports 3/3 · mypy strict · ruff

## Agent review
Evaluator A PASS, B PASS, C PASS (round 2), D PASS — specs/reviews/sprint-*-evaluator-report*.md

Security review for the merged codebase: `specs/reviews/security-review.md` (VERDICT: PASS — 0 critical/high; SEC-06/07/08/09/11/12/17 fixed test-first).

## Checklist
- [x] Spec-Is-Truth: specs changed first where behaviour changed (see spec change logs)
- [x] Tests tagged with AC/NFR ids; red runs saved in `specs/test_artefacts/`
- [x] No hand-written production code; synthetic data only
- [x] Merged with `--no-ff` (no direct commits to `main`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
