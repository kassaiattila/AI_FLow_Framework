Generate a new MUI + TypeScript component for the AIFlow admin dashboard.

## Context
The UI project is at `aiflow-admin/` using Vite + React Admin + React 19 + MUI + TypeScript.
Existing components are in `aiflow-admin/src/components/`.
MUI components (Button, Card, Chip, Table, Stack, Typography, etc.) are available.
Verification components in `aiflow-admin/src/verification/`.

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

ARGUMENTS: $ARGUMENTS
