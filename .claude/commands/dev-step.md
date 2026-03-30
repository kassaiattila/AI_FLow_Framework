Record a completed development step and run the full validation sequence.

Arguments: $ARGUMENTS
(Optional: step title)

## PRE-IMPLEMENTATION CHECKS (before writing any code!):

1. **Read the relevant plan document** in `01_PLAN/`:
   - `IMPLEMENTATION_PLAN.md` - current phase and task list
   - `35_UI_POLISH_PLAN.md` - for UI changes (i18n, UX, depth!)
   - `30_RAG_PRODUCTION_PLAN.md` - for RAG features
2. **Check reference materials** - `skills/*/reference/` if relevant
3. **Check existing code** - never reinvent what already works
4. **If DB change needed**: create Alembic migration FIRST
5. **If new skill**: use `/new-skill` command
6. **If UI change**: read CLAUDE.md "MANDATORY Next.js UI Development Rules"

## POST-IMPLEMENTATION VALIDATION:

### Python checks:
1. `git diff --name-only` — identify changes
2. `pytest tests/unit/ -q` — all pass
3. `alembic upgrade head` — if migration changed

### UI checks (if aiflow-ui/ files changed):
4. `cd aiflow-ui && npx vitest run` — all unit tests pass
5. `npx next build` — TypeScript + build clean
6. **i18n check**: grep for hardcoded strings in changed files
   - Every user-visible string MUST use `t()` from `useI18n()`
   - Run `npm run dev`, click HU/EN toggle — all text must change
7. **Data fetch check**: no `fetch("/data/...")` in page files — must use `/api/`
8. **State check**: no `localStorage`/`sessionStorage` in `useState()` initializer

### Mock vs Real audit (if viewer/skill page changed):
9. **Source tag check**: API routes return `source: "backend"|"demo"` field
10. **Demo label check**: pages show "Demo" badge when source is demo
11. **No silent mock**: NEVER fall back to mock data without visible indicator
12. **Input check**: does the viewer have an input mechanism? If not → "Results Viewer" label

### Quality gate:
13. `git status` — no untracked files that should be tracked
14. Generate conventional commit message

## CRITICAL RULES:

- NEVER commit with failing tests (Python OR UI)
- NEVER create DB tables without Alembic
- NEVER hardcode user-visible strings without `t()` in UI code
- NEVER fetch from `/data/` in page components — always `/api/`
- NEVER claim a feature is "KESZ" without manual browser test
- NEVER fall back to mock data silently — always show "Demo" label
- NEVER mark a viewer as "Production" if it only shows mock data
- ALWAYS include `source` field in API responses that use fetchBackend
- NEVER use `<script>` tags in React components
- NEVER use localStorage/sessionStorage in useState initializer
- ALWAYS use proxy.ts (NOT middleware.ts) for Next.js 16
- ALWAYS use conventional commits (feat/fix/docs/refactor)
- ALWAYS run `npx vitest run` + `npx next build` for UI changes

## Lesson from P0-P7 session:
> Build deep, not wide. Finish ONE feature end-to-end (i18n, data, states, tests)
> before starting the next. A half-working feature is worse than no feature.
