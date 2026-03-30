Generate a skill-specific result viewer component for the AIFlow dashboard.

## Context
Viewers display the output of a specific AIFlow skill in a user-friendly way.
They live in `aiflow-ui/src/components/{skill-name}/` and are used by skill pages.
The invoice viewer is the reference implementation.

## Pattern:
- KPI summary cards at top (real data from `/api/` route)
- Tabbed interface (data view, detail, pipeline trace)
- Loading / Error / Empty states for every data-dependent section
- Confidence badges (green >= 90%, yellow >= 70%, red < 70%)
- Validation errors/warnings display

## Ask me for:
1. Skill name (e.g., "email_intent_processor")
2. What data fields to display
3. Layout preference (side-by-side, tabbed, etc.)
4. Special visualizations needed

## MANDATORY Rules (session lessons — NEVER skip!):

### i18n
- Import `useI18n` from `@/hooks/use-i18n` in EVERY component
- ALL user-visible strings use `t()` — buttons, labels, headers, errors, empty states
- Add i18n keys to `src/lib/i18n.ts` (BOTH hu and en) BEFORE using them
- Test: HU/EN toggle must change EVERY string on the viewer

### Data
- Fetch from `/api/` routes ONLY — never `/data/` static files
- API route should try FastAPI backend first, fall back to mock JSON (use `backend.ts`)
- Every fetch needs error handling: `.catch(e => setError(e.message))`

### States
- Loading: show `<LoadingState />` from `@/components/page-state`
- Error: show `<ErrorState error={error} onRetry={loadData} />`
- Empty: show `<EmptyState message={t("...")} />`

### Next.js 16
- `"use client"` on all interactive components
- No localStorage in useState — use useEffect
- No hardcoded localhost URLs
- proxy.ts not middleware.ts

### Depth over Breadth
- **Build ONE viewer completely before starting the next**
- Don't mark KESZ until: i18n works, data loads, all tabs work, dark mode OK
- Write Vitest test for utility logic

## Generate:
1. Skill page (`app/skills/{name}/page.tsx`) with i18n
2. Component files (`components/{name}/*.tsx`) with i18n
3. API route (`app/api/{name}/route.ts`) with backend fallback
4. TypeScript types in `lib/types.ts`
5. i18n keys (both hu and en) in `lib/i18n.ts`
6. Mock data seed file in `public/data/{name}.json`

## Checklist (verify before marking done):
- [ ] HU/EN toggle changes all text
- [ ] Loading/error/empty states work
- [ ] All tabs/sections functional
- [ ] Dark mode looks correct
- [ ] `npx vitest run` passes
- [ ] `npx next build` passes
- [ ] Manual browser test passes

ARGUMENTS: $ARGUMENTS
