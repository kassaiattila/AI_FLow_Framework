Generate a new Untitled UI + TypeScript component for the AIFlow admin dashboard.

> **GATE 5 a 7 HARD GATE pipeline-bol. CSAK Gate 1-4 UTAN futtatható!**

## HARD GATE ELLENORZES (AUTOMATIKUS — ha FAIL → STOP, NEM GENERÁLUNK!):
```bash
# GATE CHECK: Figma design LETEZIK a PAGE_SPECS.md-ben?
grep -ic "{ComponentName}" aiflow-admin/figma-sync/PAGE_SPECS.md
# Ha 0 → **STOP** — futtasd `/ui-design` ELOSZOR!
# Ha /ui-design sem futott → futtasd `/ui-journey` ELOSZOR!
```
**TILOS komponenst generalni Figma design NELKUL!**

## Context
The UI project is at `aiflow-admin/` using Vite + Untitled UI + React 19 + Tailwind v4 + TypeScript.
Existing components are in `aiflow-admin/src/components/`.
Layout components in `aiflow-admin/src/layout/`.
Untitled UI components available: Button, Input, Badge, Table, Card, Modal, Dialog, Tabs, etc.
Icons from `@untitledui/icons` (1,100+ icons).
Styling via Tailwind CSS v4 utility classes.
Design specs in `aiflow-admin/figma-sync/PAGE_SPECS.md`.

## Ask me for:
1. Component name (e.g., "pipeline-progress", "cost-bar", "health-badge")
2. Where it goes (e.g., `components/`, `layout/`)
3. Props interface (what data it receives)
4. Visual description (what it should look like)

## MANDATORY Rules:
- **i18n**: `useTranslate()` from `src/lib/i18n` for ALL user-visible strings
- Use TypeScript strict (no `any`)
- Import from Untitled UI and `@untitledui/icons`
- **Styling**: Tailwind utility classes (`className="..."`) — NEM inline style, NEM sx prop
- Named export (not default)
- **Tables**: Ha tabla kell, hasznald a `<DataTable>` from `src/components-new/DataTable.tsx` — TanStack Table, sort+search+pagination beepitett
- **No MUI imports** — NEM `@mui/material`, NEM `@mui/icons-material`
- **No emotion/styled** — NEM `sx` prop, NEM `styled()`
- **No hardcoded URLs** — use `/api/` routes via Vite proxy, never `localhost`
- **No hardcoded strings** — every label, error, empty state uses `translate()`
- **Accessibility**: React Aria hooks where applicable (useButton, useDialog, etc.)

## Anti-patterns (NEVER do):
- `import { Typography, Chip } from "@mui/material"` → Tailwind styled HTML or Untitled UI
- `sx={{ p: 2, color: "text.secondary" }}` → `className="p-4 text-gray-500 dark:text-gray-400"`
- `useState(localStorage.getItem(...))` → `useState(null)` + `useEffect`
- `<CircularProgress />` → `<LoadingState />` or Tailwind spinner
- `import PlayArrowIcon from "@mui/icons-material/PlayArrow"` → `import { Play } from "@untitledui/icons"`

## Generate:
1. The component `.tsx` file with i18n and Tailwind styling
2. New i18n translation keys if needed (hu.json + en.json)
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
- **Dark mode:** Tailwind `dark:` variansok helyesen mukodnek?
- **A komponens CSAK AKKOR "KESZ" ha Playwright E2E teszten atment valos backend-del**

ARGUMENTS: $ARGUMENTS
