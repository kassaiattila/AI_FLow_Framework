Generate a new Next.js App Router page for the AIFlow dashboard.

## Context
The UI project is at `aiflow-ui/` using Next.js 16 App Router + TypeScript.
Pages are in `aiflow-ui/src/app/`. Sidebar is a client component (`src/components/sidebar.tsx`).

## Ask me for:
1. Page route (e.g., `/costs`, `/skills/[skill]`)
2. Page title and description
3. Data source (which `/api/` endpoint)
4. Key sections (KPI cards, tables, charts, detail views)

## MANDATORY Rules (session lessons — NEVER skip!):
- **i18n FIRST**: `useI18n()` + `t()` for ALL text. Add keys to `i18n.ts` (hu+en) BEFORE using
- **Data from `/api/` ONLY**: NEVER `fetch("/data/...")` — always via Next.js API routes
- **3 states required**: Loading (spinner), Error (message + retry), Empty (helpful text)
- **`"use client"` + hooks** for interactive pages
- **No localStorage/sessionStorage in useState** — defer to useEffect
- **proxy.ts NOT middleware.ts** — Next.js 16
- Responsive, dark mode compatible

## Anti-patterns (FORBIDDEN):
- ❌ `fetch("/data/runs.json")` → ✅ `fetch("/api/runs")`
- ❌ Hardcoded `"Betoltes..."` → ✅ `t("common.loading")`
- ❌ `useState(loadFromSession())` → ✅ `useState(null)` + `useEffect`
- ❌ Hardcoded date `"2026-03-29"` → ✅ `new Date().toISOString().slice(0,10)`
- ❌ Feature marked "KESZ" without manual HU/EN test → ✅ Test first!

## Checklist (verify BEFORE marking done):
- [ ] All strings use `t()` — click HU/EN toggle to verify
- [ ] Data from `/api/` (with backend fallback in route handler)
- [ ] Loading / Error / Empty states
- [ ] Dark mode
- [ ] `npx vitest run` + `npx next build` pass
- [ ] Manual test in browser

ARGUMENTS: $ARGUMENTS
