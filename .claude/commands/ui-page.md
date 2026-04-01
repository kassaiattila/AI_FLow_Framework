Generate a new page for the AIFlow admin dashboard.

## Context
The UI project is at `aiflow-admin/` using Vite + React Admin + React 19 + MUI + TypeScript.
Pages are in `aiflow-admin/src/pages/`. Resources in `src/resources/`.
Data flows through `src/dataProvider.ts` → FastAPI `/api/v1/*` endpoints.
Proxy config in `vite.config.ts` (NOT proxy.ts or middleware.ts).

## Ask me for:
1. Page route (e.g., `/costs`, `/invoices`)
2. Page title and description
3. Data source (which `/api/v1/` endpoint via dataProvider)
4. Key sections (KPI cards, tables, charts, detail views)

## MANDATORY Rules:
- **i18n**: `useTranslate()` from react-admin for ALL text
- **Data via dataProvider**: NEVER direct `fetch("/data/...")` — use react-admin hooks or dataProvider
- **3 states required**: Loading (spinner), Error (message + retry), Empty (helpful text)
- **No hardcoded `localhost` URLs** — use relative `/api/` paths via Vite proxy
- **No localStorage/sessionStorage in useState** — defer to useEffect
- Responsive, dark mode compatible (MUI theme)

## Anti-patterns (FORBIDDEN):
- `fetch("/data/runs.json")` → use `useGetList("runs")` or dataProvider
- Hardcoded `"Betoltes..."` → `translate("common.loading")`
- `useState(loadFromSession())` → `useState(null)` + `useEffect`
- Feature marked "KESZ" without Playwright E2E test → Test first!

## Checklist (verify BEFORE marking done):
- [ ] All strings use `translate()` — click HU/EN toggle to verify
- [ ] Data from dataProvider / `/api/v1/` endpoints
- [ ] Loading / Error / Empty states
- [ ] Dark mode
- [ ] `cd aiflow-admin && npx tsc --noEmit` pass
- [ ] Playwright E2E: navigate → snapshot → click → screenshot → console check

ARGUMENTS: $ARGUMENTS
