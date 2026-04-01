Generate a new MUI + TypeScript component for the AIFlow admin dashboard.

> **ELOFELTETEL:** Ha uj komponens, ellenorizd a Figma design-t: `aiflow-admin/figma-sync/PAGE_SPECS.md`
> Ha nincs design, futtasd eloszor `/ui-design`-t (Figma MCP). Ld. pipeline: `/ui-journey` → `/ui-design` → `/ui-component`

## Context
The UI project is at `aiflow-admin/` using Vite + React Admin + React 19 + MUI + TypeScript.
Existing components are in `aiflow-admin/src/components/`.
MUI components (Button, Card, Chip, Table, Stack, Typography, etc.) are available.
Verification components in `aiflow-admin/src/verification/`.
Design specs in `aiflow-admin/figma-sync/PAGE_SPECS.md`.

## Ask me for:
1. Component name (e.g., "pipeline-progress", "cost-bar", "health-badge")
2. Where it goes (e.g., `components/`, `verification/`, `resources/`)
3. Props interface (what data it receives)
4. Visual description (what it should look like)

## MANDATORY Rules:
- **i18n**: `useTranslate()` from react-admin for ALL user-visible strings
- Use TypeScript strict (no `any`)
- Import MUI from `@mui/material`, icons from `@mui/icons-material`
- Named export (not default)
- **No localStorage/sessionStorage in useState** — use useEffect to read after mount
- **No hardcoded URLs** — use `/api/` routes via Vite proxy, never `localhost`
- **No hardcoded strings** — every label, error, empty state uses `translate()`

## Anti-patterns (NEVER do):
- `<p>Betoltes...</p>` → `<Typography>{translate("common.loading")}</Typography>`
- `useState(localStorage.getItem(...))` → `useState(null)` + `useEffect`
- `fetch("/data/runs.json")` → use dataProvider or `/api/v1/` endpoint
- `<Typography variant="body2"><Chip .../></Typography>` → `<Typography component="div"><Chip .../></Typography>` (hydration fix)

## Generate:
1. The component `.tsx` file with i18n
2. New i18n translation keys if needed
3. Playwright E2E test verification steps

## VALOS teszteles (SOHA ne mock/fake!):
- **TypeScript check:** `cd aiflow-admin && npx tsc --noEmit` — HIBA NELKUL
- **Playwright E2E (KOTELEZO minden UI komponensnel!):**
  1. `browser_navigate` → oldal betolt?
  2. `browser_snapshot` → komponens megjelenik a vart helyen?
  3. `browser_click` → interakciok mukodnek?
  4. `browser_take_screenshot` → vizualis ellenorzes
  5. `browser_console_messages` → nincs JS hiba?
- **i18n teszt:** HU/EN toggle → MINDEN string valtozik?
- **Dark mode:** Tema valtasnal nem torik el a layout?
- **A komponens CSAK AKKOR "KESZ" ha Playwright E2E teszten atment valos backend-del**

ARGUMENTS: $ARGUMENTS
