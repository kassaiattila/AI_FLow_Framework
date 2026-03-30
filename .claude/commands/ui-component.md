Generate a new shadcn/ui + TypeScript component for the AIFlow dashboard.

## Context
The UI project is at `aiflow-ui/` using Next.js 16 + TypeScript + shadcn/ui + Tailwind CSS.
Existing components are in `aiflow-ui/src/components/`.
shadcn/ui base components (button, card, badge, table, tabs, progress) are already installed.

## Ask me for:
1. Component name (e.g., "workflow-timeline", "cost-bar", "step-detail")
2. Where it goes (e.g., `components/workflow/`, `components/email/`)
3. Props interface (what data it receives)
4. Visual description (what it should look like)

## MANDATORY Rules (session lessons — NEVER skip!):
- **i18n FIRST**: Import `useI18n` from `@/hooks/use-i18n`, use `t()` for ALL user-visible strings
- **Add i18n keys**: Add new keys to BOTH hu and en in `src/lib/i18n.ts` BEFORE using them
- Use TypeScript strict (no `any`)
- Import shadcn/ui from `@/components/ui/`, types from `@/lib/types`
- Use Tailwind CSS (no inline styles)
- Named export (not default), add `"use client"` if using hooks
- **No localStorage/sessionStorage in useState** — use useEffect to read after mount
- **No hardcoded URLs** — use `/api/` routes, never `localhost`
- **No hardcoded strings** — every label, error, empty state uses `t()`

## Anti-patterns (NEVER do):
- ❌ `<p>Betoltes...</p>` → ✅ `<p>{t("common.loading")}</p>`
- ❌ `useState(localStorage.getItem(...))` → ✅ `useState(null)` + `useEffect`
- ❌ `fetch("/data/runs.json")` → ✅ `fetch("/api/runs")`
- ❌ `<script dangerouslySetInnerHTML>` → ✅ useEffect

## Generate:
1. The component `.tsx` file with i18n
2. New i18n keys (both hu and en) to add to `i18n.ts`
3. Vitest test file for pure logic

ARGUMENTS: $ARGUMENTS
