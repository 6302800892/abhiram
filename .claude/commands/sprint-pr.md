---
name: sprint-pr
description: Close a MediCard harness sprint — run all quality gates, require an evaluator PASS for the sprint contract, write the PR record, and merge the sprint branch into main with git merge --no-ff (PR-Only Merge Rule).
argument-hint: "<group-id> e.g. A"
---

# /sprint-pr <group>

Run on the sprint branch, never on `main`.

1. **Preconditions**
   - `git branch --show-current` is not `main`.
   - `sprint-contracts/group-$ARGUMENTS.json` exists.
   - `specs/reviews/sprint-$ARGUMENTS-evaluator-report.md` contains a line `VERDICT: PASS`.
     If it does not, stop and run `/evaluate group-$ARGUMENTS`.
2. **Gates.** Every gate must pass:
   - `poetry run ruff check .`
   - `poetry run lint-imports`
   - `poetry run pytest --cov=src --cov-report=xml --cov-fail-under=80`
   - `bash scripts/test-hooks.sh`
   - `poetry run python scripts/ac_trace.py`
   - When `frontend/` exists: `cd frontend && npm run build && npx playwright test`
3. **Review.** Run the `security-reviewer` agent on `git diff main...HEAD`. Append its findings to
   the PR record. A CRITICAL or HIGH finding blocks the merge.
4. **PR record.** Write `docs/pull-requests/PR-<n>-<branch>.md` with the summary, stories, ACs,
   gate results, evaluator verdict, security review and reviewer.
5. **Merge.**
   ```bash
   git checkout main
   git merge --no-ff <branch> -m "Merge PR #<n>: <title>"
   ```
6. Update `claude-progress.txt` (groups_completed and next_action) and `features.json` passes.
   Append the sprint to `.claude/state/iteration-log.md`.
