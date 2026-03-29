Generate a new Next.js App Router page for the AIFlow dashboard.

## Context
The UI project is at `aiflow-ui/` using Next.js 16 App Router + TypeScript.
Pages are in `aiflow-ui/src/app/` following App Router conventions.
The layout (`layout.tsx`) provides a sidebar navigation.

## Ask me for:
1. Page route (e.g., `/costs`, `/runs`, `/skills/[skill]`)
2. Page title and description
3. Data source (API endpoint or local JSON)
4. Key sections (KPI cards, tables, charts, detail views)

## Rules:
- Use App Router file conventions (page.tsx, layout.tsx, loading.tsx)
- Client components: add `"use client"` directive at top
- Server components: use async/await for data fetching
- Import components from `@/components/`
- Import types from `@/lib/types`
- Use shadcn/ui components (Card, Table, Badge, Tabs, etc.)
- Hungarian labels for user-facing text
- Responsive grid layout (mobile-first with md: breakpoints)

## Generate:
1. The `page.tsx` file in the correct App Router directory
2. Any supporting components needed
3. API hooks if data fetching required

ARGUMENTS: $ARGUMENTS
