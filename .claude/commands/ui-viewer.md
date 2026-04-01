Generate a skill-specific result viewer for the AIFlow admin dashboard.

> **ELOFELTETEL:** User journey (`/ui-journey`) + API endpoint (`/ui-api-endpoint`) + Figma design (`/ui-design`)
> Ez a pipeline 5. lepese. Ha nincs Figma spec, ld. `aiflow-admin/figma-sync/PAGE_SPECS.md` 🔧 Skill Viewers szekcioja.

## Context
Viewers display the output of a specific AIFlow skill/service in a user-friendly way.
They live in `aiflow-admin/src/pages/` or `aiflow-admin/src/resources/`.
The invoice verification viewer (DocumentCanvas + VerificationPanel) is the reference implementation.
Data flows through `src/dataProvider.ts` → FastAPI `/api/v1/*` endpoints.
Design specs in `aiflow-admin/figma-sync/PAGE_SPECS.md` (🔧 Skill Viewers szekció).

## Pattern:
- KPI summary cards at top (real data from dataProvider)
- Tabbed/split interface (data view, detail, verification)
- Loading / Error / Empty states for every data-dependent section
- Confidence badges (green >= 90%, yellow >= 70%, red < 70%)
- Validation errors/warnings display

## Ask me for:
1. Skill/service name (e.g., "email_intent_processor", "document_extractor")
2. What data fields to display
3. Layout preference (side-by-side, tabbed, etc.)
4. Special visualizations needed

## MANDATORY Rules:

### i18n
- `useTranslate()` from react-admin for ALL user-visible strings
- Test: HU/EN toggle must change EVERY string on the viewer

### Data
- Fetch via dataProvider or `/api/v1/` endpoints — NEVER static files
- Every API response MUST include `source: "backend"|"demo"` field
- Page MUST show Demo/Live badge based on source

### States
- Loading: MUI CircularProgress or Skeleton
- Error: Alert + retry button
- Empty: meaningful message with suggested action

### Vite + React Admin
- No localStorage in useState — use useEffect
- No hardcoded localhost URLs — use Vite proxy
- vite.config.ts for proxy (NOT proxy.ts or middleware.ts)

### Depth over Breadth
- **Build ONE viewer completely before starting the next**
- Don't mark KESZ until: Playwright E2E test passes with real backend data
- NEVER mark as "Production" if only shows mock data

## Generate:
1. Page component (`pages/{Name}.tsx`) with i18n
2. Resource files (`resources/{Name}List.tsx`, `{Name}Show.tsx`) if needed
3. Supporting components in `components/` or `verification/`
4. dataProvider extension if needed

## Backend Integration Checklist (MANDATORY — no silent mock!):
- [ ] dataProvider endpoint configured in RESOURCE_MAP
- [ ] Response includes `source: "backend"|"demo"` field
- [ ] Page shows Demo/Live badge based on source
- [ ] Input mechanism exists (upload, text form, etc.)
- [ ] Real processing callable (FastAPI endpoint or SSE stream)
- [ ] Mock data clearly labeled — NEVER silent fallback
- [ ] Status badge honest: NOT "Production" if only mock

## Full Checklist:
- [ ] HU/EN toggle changes all text
- [ ] Loading/error/empty states work
- [ ] All tabs/sections functional
- [ ] Dark mode looks correct
- [ ] Backend Integration Checklist above — ALL checked
- [ ] `cd aiflow-admin && npx tsc --noEmit` passes
- [ ] **Playwright E2E test: navigate → snapshot → click → screenshot → console check**
- [ ] Manual browser test: backend ON (Live) + OFF (Demo) both work

## VALOS teszteles (SOHA ne mock/fake!):
- **Playwright E2E (KOTELEZO!):** Valos backend-del csatlakozva, valos adat a viewerben
  1. `browser_navigate` → viewer betolt?
  2. `browser_snapshot` → valos adat megjelenik (NEM placeholder)?
  3. `browser_click` → interakciok (tab valtas, detail nezet, szurok) mukodnek?
  4. `browser_take_screenshot` → vizualis ellenorzes
  5. `browser_console_messages` → nincs JS hiba?
- **Backend ON teszt:** `source: "backend"` — valos adat, Live badge megjelenik
- **Backend OFF teszt:** `source: "demo"` — Demo badge megjelenik, mock JELOLVE van
- **Teljes flow:** Input (upload/form) → Process (valos feldolgozas) → Output (valos eredmeny)
- **A viewer CSAK AKKOR "KESZ" ha MINDKET szcenario (Live + Demo) Playwright teszten atment**

ARGUMENTS: $ARGUMENTS
