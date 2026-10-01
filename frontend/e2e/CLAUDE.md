# frontend/e2e/ — Playwright UI validation (evaluator Layer 2)

- `playwright.config.ts` starts the **real** backend (`uvicorn src.main:create_app --factory`) on
  :8123 with a throwaway SQLite DB, serving the built `dist/`. Run `npm run build` first.
- Journeys map to the sprint-contract `playwright_checks` (`pw-001` … `pw-006`) and to AC IDs in
  the test titles.
- Every spec seeds its own data through the API (`support.ts`). Never rely on another spec's state.
- Snapshot baselines live in `__snapshots__/`:
  - `*.aria.yml`: ARIA snapshots. These are text, OS-independent, and run in CI. Snapshot static
    structure only, never data tables.
  - `*.png`: pixel baselines. These are tagged `@visual`, OS and font dependent, and excluded in CI.
- Update baselines deliberately: `npx playwright test --update-snapshots`. Review the diff in the PR.
- The Playwright MCP server (`.mcp.json`) is the evaluator's interactive counterpart to these specs.
