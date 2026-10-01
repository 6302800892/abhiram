---
name: medicard-janitor-agent
description: Bonus maintenance agent. Removes dead code, stale TODOs, unused imports and drift between specs and code comments. Use at the end of a sprint, before /sprint-pr.
tools:
  - Read
  - Edit
  - Glob
  - Grep
  - Bash
model: haiku
---

# MediCard Janitor Agent

1. Run `poetry run ruff check . --select F401,F841,ERA` and fix only what it reports.
2. Grep for `TODO|FIXME|XXX` in `src/` and `frontend/src/`. Resolve each one or move it to
   `specs/stories/backlog-needs-breakdown.md`.
3. Check that each reason code used in `src/` appears in `specs/network_admin_spec.md` NA-R5.
4. Do not change behaviour. If a cleanup changes any test outcome, revert it.
5. Commit as `chore(janitor): …` on the current sprint branch.
