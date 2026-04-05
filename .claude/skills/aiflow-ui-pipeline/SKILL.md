---
name: aiflow-ui-pipeline
description: >
  AIFlow admin UI fejlesztesi pipeline 7 HARD GATE-tel. Hasznald amikor UI
  oldalt, komponenst, viewert fejlesztesz, Figma design-t csinalsz, vagy
  aiflow-admin/ kodot irsz. Untitled UI + Tailwind v4 + React Aria.
allowed-tools: Read, Write, Grep, Glob, Bash
---

# AIFlow Admin UI Development Pipeline

## 7 HARD GATE — KIHAGYNI TILOS, SORREND KOTELEZO!

```
GATE 1: /ui-journey → OUTPUT: 01_PLAN/ journey fajl (ONALLO FAJL!)
   GATE CHECK: ls 01_PLAN/*JOURNEY* — FAJL FIZIKAILAG LETEZIK-e?

GATE 2: API audit → OUTPUT: minden endpoint curl-lel tesztelve, source: "backend"
   GATE CHECK: curl tesztek PASS, nincs FAIL endpoint?

GATE 3: /ui-api-endpoint → OUTPUT: hianyzo endpointok implementalva
   GATE CHECK: MINDEN journey endpoint 200 OK + valos adat?

GATE 4: /ui-design (Figma MCP) → OUTPUT: PAGE_SPECS.md frissitve + Figma frame
   GATE CHECK: grep "{PageName}" PAGE_SPECS.md + Figma frame ID letezik

GATE 5: /ui-page vagy /ui-component → OUTPUT: .tsx fajl + tsc --noEmit PASS
   GATE CHECK: TypeScript HIBA NELKUL?

GATE 6: Playwright E2E → OUTPUT: screenshot + 0 console error + i18n HU/EN
   GATE CHECK: MINDEN E2E check PASS?

GATE 7: Figma sync → OUTPUT: PAGE_SPECS.md vegso frissites
   GATE CHECK: PAGE_SPECS.md es a .tsx fajl KONZISZTENS?
```

**Ha BARMELYIK check FAIL → NEM IRUNK UI KODOT. Eloszor az elofeltetelt teljesitjuk.**

## GATE CHECK PROTOCOL (MINDEN UI munka ELOTT futtatando!)

```bash
# 1. Journey fajl FIZIKAILAG letezik? (ls, NEM grep!)
ls 01_PLAN/*JOURNEY*.md 2>/dev/null || echo "GATE 1 FAIL — /ui-journey KELL ELOSZOR!"

# 2. PAGE_SPECS.md-ben van-e az oldal szekcioja?
grep -c "## Page.*{PageName}" aiflow-admin/figma-sync/PAGE_SPECS.md || echo "GATE 4 FAIL"

# 3. API valos adatot ad?
curl -sf http://localhost:8102/api/v1/{endpoint} | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('source')=='backend'" || echo "GATE 2-3 FAIL"
```

## Untitled UI + Tailwind Rules

- **Styling:** Tailwind utility classes — NEM inline style, NEM sx prop, NEM emotion
- **Components:** Untitled UI primitives (Button, Input, Table, Badge) — NEM MUI
- **Icons:** @untitledui/icons — NEM @mui/icons-material
- **Accessibility:** React Aria hooks (useButton, useDialog, useTable)
- **Theming:** tailwind.config.ts design tokenek — NEM MUI createTheme
- **Data fetching:** `fetchApi<T>()` from `src/lib/api-client.ts`
- **Auth:** `src/lib/auth.ts`
- **Tables:** `<DataTable>` from `src/components-new/DataTable.tsx` — KOTELEZO minden lista oldalon
  (TanStack Table v8, headless, Tailwind styled, beepitett: sort, search, pagination)

## i18n Rules (NEVER skip!)

- EVERY user-visible string MUST use `useTranslate()` from `src/lib/i18n.ts`
- Wire i18n AS YOU BUILD — not after
- Check: page titles, button labels, table headers, KPI labels, error messages, empty states
- Test: click HU/EN toggle → EVERY string on screen must change

## Vite + Routing Rules

- **vite.config.ts** tartalmazza az API proxy-t (`/api` → `localhost:8102`)
- **No hardcoded localhost URLs** — use relative paths via `/api/` proxy routes
- **Routing:** React Router v7 route-ok `src/router.tsx`-ben
- **No localStorage in useState() initializer** — causes hydration mismatch

## UI Component Checklist (verify BEFORE marking done)

1. [ ] `useTranslate()` hook imported and all strings use `translate()`
2. [ ] Loading state (spinner/skeleton while data loads)
3. [ ] Error state (error message + retry button)
4. [ ] Empty state (meaningful message when no data)
5. [ ] Data fetched via `fetchApi()` / `useApi()` hook
6. [ ] No hardcoded Hungarian/English strings
7. [ ] Works in both light and dark mode
8. [ ] Playwright E2E teszt: navigate → snapshot → click → screenshot → console check

## Viewer Completeness Rules

- A viewer is NOT complete unless: INPUT → REAL PROCESSING → REAL OUTPUT
- Every API route returns `source: "backend"|"demo"` field
- Every page shows "Demo mod" banner when `source === "demo"`
- NEVER pretend mock data is real
- Status badges must be honest: "Production" only if actually works

## No Silent Mock Data

- Every API route: `source` field mandatory
- Demo banner when source !== "backend"
- NEVER silent fallback to mock data
- Connection status visible in sidebar

## UI Testing Protocol

```bash
cd aiflow-admin && npx tsc --noEmit     # 0 error
# Playwright MCP:
# browser_navigate → browser_snapshot → browser_click → browser_take_screenshot
# browser_console_messages → 0 JS hiba
```

## Design System

Untitled UI (React 19 + Tailwind v4), Figma channel: `hq5dlkhu`
