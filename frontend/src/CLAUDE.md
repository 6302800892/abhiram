# frontend/src/ — portal source

| Path | Role |
|---|---|
| `api.ts` | Fetch wrapper; maps `{"error":{code,message}}` to `ApiError` |
| `auth.tsx` | Session context (sessionStorage, wrapped in try/catch) and `HOME_BY_ROLE` |
| `hooks.ts` | `useLoad` (fetch on mount, then `reload`) and `useAction` (busy + error for mutations) |
| `types.ts` | Response shapes; every money field is a `string` |
| `components/ui.tsx` | `Panel`, `Field`, `SelectField`, `StatusBadge`, `ErrorAlert`, `Notice`, `Money` |
| `components/CaseActions.tsx` | Hospital and insurer case actions, shown according to case status |
| `pages/*Page.tsx` | One workspace per role, plus the shared `CaseDetailPage` |

To add a screen: create a page, add a route in `App.tsx` behind `RequireRole`, and add a
Playwright journey in `e2e/` first (red). Then build it.
