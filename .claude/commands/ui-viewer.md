Generate a skill-specific result viewer for the AIFlow admin dashboard.

> **ELOFELTETEL:** User journey (`/ui-journey`) + API endpoint (`/ui-api-endpoint`) + Figma design (`/ui-design`)
> Ez a pipeline 5. lepese. Ha nincs Figma spec, ld. `aiflow-admin/figma-sync/PAGE_SPECS.md`

## Context
Viewers display the output of a specific AIFlow skill/service in a user-friendly way.
They live in `aiflow-admin/src/pages/`.
Data flows through `src/lib/api-client.ts` (`fetchApi<T>()`) → FastAPI `/api/v1/*` endpoints.
Design specs in `aiflow-admin/figma-sync/PAGE_SPECS.md`.

## Pattern:
- KPI summary cards at top (`<KpiCard>` component + recharts sparkline)
- Tabbed/split interface (`<TabLayout>` component + React Aria)
- Loading (`<LoadingState>`) / Error (`<ErrorState>`) / Empty (`<EmptyState>`) states
- Confidence badges (`<ConfidenceBadge>` — Governor Pattern: 70% opacity unverified, 100% verified)
- Status badge (`<StatusBadge>` — Live/Demo based on `source` field)
- Validation errors/warnings display

## Ask me for:
1. Skill/service name (e.g., "email_intent_processor", "document_extractor")
2. What data fields to display
3. Layout preference (side-by-side, tabbed, etc.)
4. Special visualizations needed

## MANDATORY Rules:

### i18n
- `useTranslate()` from `src/lib/i18n` for ALL user-visible strings
- Test: HU/EN toggle must change EVERY string on the viewer

### Data
- Fetch via `fetchApi<T>()` or `useApi()` hook — NEVER dataProvider, NEVER direct static files
- Every API response MUST include `source: "backend"|"demo"` field
- Page MUST show StatusBadge (Demo/Live) based on source

### States (using reusable components)
- Loading: `<LoadingState />` (skeleton loading)
- Error: `<ErrorState error={error} onRetry={refetch} />`
- Empty: `<EmptyState messageKey="..." onAction={...} />`

### Styling
- Tailwind utility classes — NEM MUI sx prop, NEM emotion
- Components from Untitled UI — NEM @mui/material
- Icons from @untitledui/icons — NEM @mui/icons-material
- Dark mode via Tailwind `dark:` variant
- Responsive via Tailwind breakpoints

### Depth over Breadth
- **Build ONE viewer completely before starting the next**
- Don't mark KESZ until: Playwright E2E test passes with real backend data
- NEVER mark as "Production" if only shows mock data

## Generate:
1. Page component (`pages/{Name}.tsx`) with i18n and Tailwind styling
2. Supporting components in `components/` if needed
3. i18n keys for `src/locales/hu.json` + `en.json`

## Backend Integration Checklist (MANDATORY — no silent mock!):
- [ ] API endpoint returns `source: "backend"|"demo"` field
- [ ] Page shows StatusBadge (Demo/Live) based on source
- [ ] Input mechanism exists (upload, text form, etc.)
- [ ] Real processing callable (FastAPI endpoint or SSE stream)
- [ ] Mock data clearly labeled — NEVER silent fallback
- [ ] Status badge honest: NOT "Production" if only mock

## Full Checklist:
- [ ] HU/EN toggle changes all text
- [ ] Loading/error/empty states work (reusable components)
- [ ] All tabs/sections functional
- [ ] Dark mode looks correct (Tailwind `dark:` variants)
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
