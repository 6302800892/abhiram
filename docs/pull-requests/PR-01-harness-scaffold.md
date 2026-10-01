# PR #1 — Scaffold Claude Harness Engine + MediCard substrate

| | |
|---|---|
| Branch | `chore/harness-scaffold` → `main` (`git merge --no-ff`) |
| Author | Claude Code agents (harness generator + MediCard domain agents), supervised by the AI-native engineer |
| ACs / NFRs | — |

## Summary
Harness v1.1.4 copied via /scaffold (7 agents, 23 skills, 15 hooks, templates, state); MediCard agents (8), skills (6), hooks (5), commands (3), plugin.json, .mcp.json (Playwright MCP), Agent SDK scripts, GitLab CI with Claude review.

## Quality gates
bash scripts/test-hooks.sh (all hooks block bad / pass clean input)

## Agent review
n/a (substrate)

Security review for the merged codebase: `specs/reviews/security-review.md` (VERDICT: PASS — 0 critical/high; SEC-06/07/08/09/11/12/17 fixed test-first).

## Checklist
- [x] Spec-Is-Truth: specs changed first where behaviour changed (see spec change logs)
- [x] Tests tagged with AC/NFR ids; red runs saved in `specs/test_artefacts/`
- [x] No hand-written production code; synthetic data only
- [x] Merged with `--no-ff` (no direct commits to `main`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
