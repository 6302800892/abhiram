# frontend/ — MediCard role-based portal (React 19 + Vite + TypeScript)

The UI layer (rank 6 in `project-manifest.json`). It talks to the backend **only** through
`src/api.ts`. FastAPI serves the built `dist/` at `/` (`src/api/static.py`).

## Commands
- `npm ci` · `npm run build` (runs `tsc --noEmit` first) · `npm run dev` (proxies `/api` to :8000)
- `npx playwright test`: full UI validation, including `@visual` pixel baselines (local only)
- `npm run test:e2e:ci`: CI subset (journeys + ARIA snapshots, no pixel diffs)

## Rules for generators
- **No business math in the UI.** Money is displayed exactly as the server's decimal strings.
  Never `parseFloat` an amount (NFR-01). Caps, settlement and eligibility are computed server-side only.
- Role gating in `App.tsx` is a convenience. The real boundary is the API (NFR-04).
- Accessibility drives the tests. Each panel is a `<section>` named by its heading (Playwright
  `getByRole('region', { name })`). Each input has a `<label>` (`Field` / `SelectField`). Errors
  use `role="alert"`, confirmations `role="status"`.
- Responsive: one column under 768px, two above. Tables scroll inside `.table-wrap`, never the page.
- Keep components under 300 lines. Shared primitives live in `src/components/ui.tsx`.
- Never render diagnosis labels or clinical notes in notifications. Codes only (NFR-03).

See `src/CLAUDE.md` and `e2e/CLAUDE.md`.
