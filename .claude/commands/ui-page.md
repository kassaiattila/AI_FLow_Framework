Generate a new page for the AIFlow admin dashboard.

> **GATE 5 a 7 HARD GATE pipeline-bol. CSAK Gate 1-4 UTAN futtatható!**

## HARD GATE ELLENORZES (AUTOMATIKUS — ha FAIL → STOP, NEM GENERÁLUNK!):
> **GATE VIOLATION TORTENELEM:** F1+F2 fazisban ezek a check-ek KIHAGYASRA kerultek.
> Emiatt FIZIKAI FAJL ELLENORZES (`ls`) szukseges, grep ONMAGABAN NEM ELEG.

```bash
# GATE CHECK 1: Journey fajl FIZIKAILAG LETEZIK? (ONALLO FAJL, NEM grep!)
ls 01_PLAN/F*_*JOURNEY*.md 2>/dev/null || echo "GATE 1 FAIL: Journey fajl HIANYZIK!"
# Ha NINCS FAJL → **STOP** — futtasd `/ui-journey` ELOSZOR!

# GATE CHECK 2: PAGE_SPECS.md LETEZIK az oldalhoz + FIGMA REFERENCIA van benne?
grep -c "## Page.*{PageName}" aiflow-admin/figma-sync/PAGE_SPECS.md || echo "GATE 4 FAIL: PAGE_SPECS entry HIANYZIK!"
# Ha 0 → **STOP** — futtasd `/ui-design` (valos Figma MCP design!) ELOSZOR!

# GATE CHECK 3: API endpoint valos adatot ad?
curl -sf http://localhost:8102/api/v1/{endpoint} | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend', 'NO BACKEND'" || echo "GATE 2-3 FAIL: API nem ad valos adatot!"
```
**Mind a 3 GATE PASS kell mielott BARMILYEN UI kodot generalnal!**
**Ha barmelyik FAIL → STOP → megoldas → ujra ellenorzes → AZTAN generálas.**
**NEM kerhetsz engedelyt a gate kihagyasara — NINCS kiveteles.**

## Context
The UI project is at `aiflow-admin/` using Vite + Untitled UI + React 19 + Tailwind v4 + TypeScript.
Pages are in `aiflow-admin/src/pages/`.
Layout components in `aiflow-admin/src/layout/` (AppShell, Sidebar, TopBar, PageLayout).
Reusable components in `aiflow-admin/src/components/` (DataTable, EmptyState, LoadingState, ErrorState, StatusBadge, TabLayout, etc.).
Data flows through `src/lib/api-client.ts` (`fetchApi<T>()`) → FastAPI `/api/v1/*` endpoints.
Auth via `src/lib/auth.ts`, i18n via `src/lib/i18n.ts`.
Proxy config in `vite.config.ts` (NOT proxy.ts or middleware.ts).
Design specs in `aiflow-admin/figma-sync/PAGE_SPECS.md`.

## Ask me for:
1. Page route (e.g., `/costs`, `/documents`)
2. Page title and description
3. Data source (which `/api/v1/` endpoint via fetchApi)
4. Key sections (KPI cards, tables, charts, detail views)

## MANDATORY Rules:
- **i18n**: `useTranslate()` from `src/lib/i18n` for ALL text
- **Data via fetchApi**: `const { data, loading, error } = useApi<T>("/api/v1/runs")` — NEM dataProvider, NEM useGetList
- **Styling**: Tailwind utility classes (`className="p-4 text-sm"`) — NEM MUI sx prop, NEM emotion
- **Components**: Untitled UI primitives — NEM `@mui/material`
- **Icons**: `@untitledui/icons` — NEM `@mui/icons-material`
- **Layout**: Wrap content in `<PageLayout>` component
- **Tables**: `<DataTable>` from `src/components-new/DataTable.tsx` (TanStack Table) — KOTELEZO lista oldalaknal. Sort, search, pagination beepitett. NEM szabad kezi `<table>` markup-ot irni.
- **3 states required**: Loading (`<LoadingState />`), Error (`<ErrorState />`), Empty (`<EmptyState />`)
- **No hardcoded `localhost` URLs** — use relative `/api/` paths via Vite proxy
- **No localStorage/sessionStorage in useState** — defer to useEffect
- Responsive via Tailwind breakpoints (`sm:`, `md:`, `lg:`)
- Dark mode via Tailwind `dark:` variant

## Anti-patterns (FORBIDDEN):
- `import { Button } from "@mui/material"` → import from Untitled UI or use Tailwind styled HTML
- `sx={{ p: 2, color: "text.secondary" }}` → `className="p-4 text-gray-500 dark:text-gray-400"`
- `useGetList("runs")` → `useApi<RunsResponse>("/api/v1/runs")`
- `import { Typography } from "@mui/material"` → semantic HTML (`<h2>`, `<p>`) with Tailwind
- Hardcoded `"Betoltes..."` → `translate("common.loading")`
- `<CircularProgress />` → `<LoadingState />` component
- Feature marked "KESZ" without Playwright E2E test → Test first!

## Checklist (verify BEFORE marking done):
- [ ] All strings use `translate()` — click HU/EN toggle to verify
- [ ] Data from `fetchApi()` / `useApi()` hook / `/api/v1/` endpoints
- [ ] Loading / Error / Empty states (using reusable components)
- [ ] StatusBadge (Live/Demo) visible
- [ ] Dark mode (Tailwind `dark:` variant)
- [ ] `cd aiflow-admin && npx tsc --noEmit` pass
- [ ] Playwright E2E: navigate → snapshot → click → screenshot → console check

## VALOS teszteles (SOHA ne mock/fake!):
- **TypeScript check:** `cd aiflow-admin && npx tsc --noEmit` — HIBA NELKUL
- **Playwright E2E (KOTELEZO!):**
  1. `browser_navigate` → oldal betolt valos backend-del?
  2. `browser_snapshot` → vart tartalom megjelenik (NEM "Loading..." oreokke)?
  3. `browser_click` → gombok, linkek, szurok, rendezesek mukodnek?
  4. `browser_take_screenshot` → vizualis ellenorzes
  5. `browser_console_messages` → nincs JS hiba?
- **Adat ellenorzes:** Az oldalon valos backend adat jelenik meg (`source: "backend"`), NEM demo/mock
- **Az oldal CSAK AKKOR "KESZ" ha Playwright E2E teszten atment valos backend-del**

ARGUMENTS: $ARGUMENTS
