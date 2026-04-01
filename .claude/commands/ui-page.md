Generate a new page for the AIFlow admin dashboard.

> **GATE 5 a 7 HARD GATE pipeline-bol. CSAK Gate 1-4 UTAN futtatható!**

## HARD GATE ELLENORZES (AUTOMATIKUS — ha FAIL → STOP, NEM GENERÁLUNK!):
```bash
# GATE CHECK 1: Journey LETEZIK?
grep -ri "Journey:" 01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md | grep -i "{page}"
# Ha NINCS → **STOP** — futtasd `/ui-journey` ELOSZOR!

# GATE CHECK 2: Figma design LETEZIK a PAGE_SPECS.md-ben?
grep -ic "{PageName}" aiflow-admin/figma-sync/PAGE_SPECS.md
# Ha 0 → **STOP** — futtasd `/ui-design` ELOSZOR!

# GATE CHECK 3: API endpoint valos adatot ad?
curl -s http://localhost:8100/api/v1/{endpoint} | python -c "import sys,json; print(json.load(sys.stdin).get('source','?'))"
# Ha NEM "backend" → **STOP** — implementald az API-t ELOSZOR!
```
**Mind a 3 GATE PASS kell mielott BARMILYEN UI kodot generalnal!**
Ha barmelyik FAIL → jelezd a felhasznalonak melyik elofeltetel hianyzik.

## Context
The UI project is at `aiflow-admin/` using Vite + React Admin + React 19 + MUI + TypeScript.
Pages are in `aiflow-admin/src/pages/`. Resources in `src/resources/`.
Data flows through `src/dataProvider.ts` → FastAPI `/api/v1/*` endpoints.
Proxy config in `vite.config.ts` (NOT proxy.ts or middleware.ts).
Design specs in `aiflow-admin/figma-sync/PAGE_SPECS.md`.

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
