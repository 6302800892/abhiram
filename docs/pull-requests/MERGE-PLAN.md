# Merge plan: PR-driven history (for the human operator)

During the build session the operator asked the agent **not to run git**. The agent therefore
left the git work to the operator: branching, committing and `--no-ff` merging. This file lists
the exact sequence. The resulting history has:

- **6 PR merges into `main`, all `--no-ff`**, and zero direct commits on `main` after the root
  commit `chore: initialize MediCard repository`.
- Each PR's test files committed **before** the code that makes them pass (red → green visible
  in history).
- One PR record per merge in this folder, with the agent review (evaluator and security
  reviewer) linked.

> Current state: the branch `chore/harness-scaffold` already holds 2 commits on top of the root
> (harness scaffold, then MediCard substrate). Everything else is still uncommitted in the
> working tree.

Run the steps from the repository root in Git Bash. They are **idempotent per step**: check
`git status` between steps.

```bash
# ---------------------------------------------------------------- PR #1 harness scaffold + substrate
git checkout chore/harness-scaffold
git checkout main
git merge --no-ff chore/harness-scaffold -m "Merge PR #1: scaffold Claude Harness Engine + MediCard substrate"

# ---------------------------------------------------------------- PR #2 requirements & specs
git checkout -b docs/requirements-specs
git add specs/brd specs/stories specs/app_spec.md specs/*_spec.md specs/CLAUDE.md docs/business-case.md \
        features.json README.md .env.example
git commit -m "docs(specs): BRD, business case, root spec + 7 feature specs, stories, features.json"
git checkout main
git merge --no-ff docs/requirements-specs -m "Merge PR #2: requirements, specs and stories (harness /brd + /spec)"

# ---------------------------------------------------------------- PR #3 substrate hardening
git checkout -b chore/substrate-hardening
git add .claude .claude-plugin plugin.json .mcp.json .gitlab-ci.yml .gitattributes .gitignore scripts \
        pyproject.toml poetry.lock CLAUDE.md AGENTS.md init.sh project-manifest.json
git commit -m "chore(substrate): git-free hooks, guard-alias discovery, PHI/settlement hook fixes, SDK scripts, CI"
git checkout main
git merge --no-ff chore/substrate-hardening -m "Merge PR #3: substrate hardening (hooks, CI, Agent SDK scripts)"

# ---------------------------------------------------------------- PR #4 backend sprints 1-4 (red -> green)
git checkout -b feat/backend-sprints-1-4
git add sprint-contracts tests specs/test_artefacts
git commit -m "test: AC-tagged unit, API and architecture tests for groups A-D (red)"
git add migrations seed src/domain src/repository
git commit -m "feat(domain,repository): cashless rules, state machines, append-only migrations"
git add src
git commit -m "feat(service,api): eligibility, pre-auth, adjudication, case lifecycle, settlement, override, reports (green)"
git add coverage.xml specs/reviews/sprint-A-evaluator-report.md specs/reviews/sprint-B-evaluator-report.md \
        specs/reviews/sprint-D-evaluator-report.md specs/reviews/ac-trace.md
git commit -m "chore(evidence): coverage.xml (94.9 %), evaluator reports A/B/D, AC trace"
git checkout main
git merge --no-ff feat/backend-sprints-1-4 -m "Merge PR #4: backend sprints 1-4 (AC-01..AC-10)"

# ---------------------------------------------------------------- PR #5 fix loop FL-001
git checkout -b fix/fl-001-rule-version-snapshot
git add specs/reviews/sprint-C-evaluator-report.md specs/reviews/eval-failures-C.json \
        specs/reviews/sprint-C-evaluator-report-r2.md docs/fix-loops
git commit -m "fix(settlement): price existing cases with the pre-auth's recorded rule version (FL-001)"
git checkout main
git merge --no-ff fix/fl-001-rule-version-snapshot -m "Merge PR #5: fix loop FL-001 (settlement cap vs mid-cycle rule change)"

# ---------------------------------------------------------------- PR #6 portal UI (red -> green)
git checkout -b feat/portal-ui
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/playwright.config.ts \
        frontend/e2e/*.ts frontend/e2e/CLAUDE.md
git commit -m "test(e2e): Playwright journeys pw-001..pw-006 for the role portals (red)"
git add frontend
git commit -m "feat(ui): responsive React portal for customer, hospital, insurer and admin (green) + snapshots"
git checkout main
git merge --no-ff feat/portal-ui -m "Merge PR #6: role-based responsive portal + Playwright UI validation"

# ---------------------------------------------------------------- PR #7 docs & evidence
git checkout -b docs/architecture-tdd-evidence
git add docs specs/reviews claude-progress.txt .claude/state design.md calibration-profile.json
git commit -m "docs: architecture, TDD, post-mortem, knowledge deposits, PR records, security review"
git checkout main
git merge --no-ff docs/architecture-tdd-evidence -m "Merge PR #7: architecture/TDD docs and evidence trail"

# ---------------------------------------------------------------- verify + push
git log --first-parent --oneline main      # root + 7 merge commits only
git status                                  # clean
git remote add origin <your Virtusa GitLab repo URL>
git push -u origin main --all
```

Notes:
- The code-level FL-001 fix (`case_service.case_rule`) is part of the final `src/` state committed in
  PR #4, because the session did not use git while the loop ran. PR #5 carries the loop's evidence
  trail: detection report, reproduction, round-2 PASS. The order is documented in
  `docs/fix-loops/FL-001-rule-version-mid-cycle.md`.
- After pushing, protect `main` in GitLab (merge requests only) and add the masked CI variable
  `ANTHROPIC_API_KEY`, so the `claude-review` job runs on merge requests.
- Every commit above contains Claude-generated content. You may add the trailer
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` to each message.
