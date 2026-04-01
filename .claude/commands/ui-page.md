Generate a new page for the AIFlow admin dashboard.

> **GATE 5 a 7 HARD GATE pipeline-bol. CSAK Gate 1-4 UTAN futtatható!**

## HARD GATE ELLENORZES (AUTOMATIKUS — ha FAIL → STOP, NEM GENERÁLUNK!):
> **GATE VIOLATION TORTENELEM:** F1+F2 fazisban ezek a check-ek KIHAGYASRA kerultek.
> Emiatt FIZIKAI FAJL ELLENORZES (`ls`) szukseges, grep ONMAGABAN NEM ELEG.

```bash
# GATE CHECK 1: Journey fajl FIZIKAILAG LETEZIK? (ONALLO FAJL, NEM grep!)
ls 01_PLAN/F*_*JOURNEY*.md 2>/dev/null || echo "GATE 1 FAIL: Journey fajl HIANYZIK!"
# Ha NINCS FAJL → **STOP** — futtasd `/ui-journey` ELOSZOR!
# NEM eleg grep-pelni a generalizacios tervet — ONALLO journey fajl KELL!

# GATE CHECK 2: PAGE_SPECS.md LETEZIK az oldalhoz + FIGMA REFERENCIA van benne?
grep -c "## Page.*{PageName}" aiflow-admin/figma-sync/PAGE_SPECS.md || echo "GATE 4 FAIL: PAGE_SPECS entry HIANYZIK!"
# Ha 0 → **STOP** — futtasd `/ui-design` (valos Figma MCP design!) ELOSZOR!
# Manuálisan írt PAGE_SPECS entry Figma design NÉLKÜL NEM ELFOGADHATÓ!

# GATE CHECK 3: API endpoint valos adatot ad?
curl -sf http://localhost:8100/api/v1/{endpoint} | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend', 'NO BACKEND'" || echo "GATE 2-3 FAIL: API nem ad valos adatot!"
# Ha NEM "backend" → **STOP** — implementald az API-t ELOSZOR!
```
**Mind a 3 GATE PASS kell mielott BARMILYEN UI kodot generalnal!**
**Ha barmelyik FAIL → STOP → megoldas → ujra ellenorzes → AZTAN generálas.**
**NEM kerhetsz engedelyt a gate kihagyasara — NINCS kiveteles.**

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
