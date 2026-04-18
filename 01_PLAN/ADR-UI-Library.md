# ADR: UI Component Library Choice for `aiflow-admin`

> **Status:** Accepted
> **Date:** 2026-04-26
> **Session:** S89 (v1.4.4.2 — Sprint H Consolidation Day 2)
> **Supersedes:** Implicit F6 assumption "Untitled UI is the admin UI baseline"
> **Scope:** `aiflow-admin/` only (React 19 + Vite 7 + Tailwind v4). Does not apply to `DOHA/` or other frontends.

## Context

The F6 UI modernization track (see memory: *UI hard gates*, *Figma quality*) originally adopted [Untitled UI](https://www.untitledui.com/) as the admin design system. The codebase today reflects an incomplete migration in the opposite direction:

- `aiflow-admin/src/components/` — a Untitled UI (UUI) component tree (avatars, badges, inputs, selects, tags — 16 files importing `@untitledui/icons`).
- `aiflow-admin/src/components-new/` — an in-house Tailwind v4 component set (Breadcrumb, DataTable, StatusBadge, LoadingState, ErrorState, EmptyState, FileProgress, ChatPanel, …).
- `aiflow-admin/src/pages-new/` — the 19 pages wired into `router.tsx` (Dashboard, Documents, Emails, Rag, Runs, …). Every routed page comes from here.
- `aiflow-admin/src/pages/` — empty.
- `aiflow-admin/src/pages-archive/` — 5 superseded pages (Cubix, Media, ProcessDocs, Rpa, SpecWriter).

Audit, 2026-04-26 (`grep -rE "@untitledui" src/layout src/pages-new src/components-new`):

| Tree | Files importing `@untitledui` |
|---|---|
| `src/layout/` | **0** |
| `src/pages-new/` | **0** |
| `src/components-new/` | **0** |
| `src/components/` (UUI) | 16 (self-contained) |
| All other `src/**` | 0 |

Additionally, no file outside `src/components/` imports anything from `src/components/` (`grep -rE "from ['\"]\\.\\.?/components/"` returns only internal UUI cross-references). The UUI subtree is **dead code** in the active app. The `package.json` dependency `@untitledui/icons@0.0.22` is likewise unreferenced outside that subtree.

The S89 prompt described the current state as "Hybrid — keep Untitled UI icons, build layouts in Tailwind". Measurement does not support that: the active app has zero UUI imports, including icons. This ADR records the decision based on the measured state, not the prompt's premise.

## Decision

**Option 2 — Reject Untitled UI.** Commit to Tailwind v4 + `components-new/` as the sole admin UI stack. Schedule removal of the dead `src/components/` (UUI) tree and the `@untitledui/icons` dependency in a dedicated cleanup session (not part of S89).

This is not a new direction — it is a ratification of the codebase's observed state. The F6 assumption that UUI is the baseline is retired.

## Consequences

**Future UI sessions MUST:**

1. Add pages under `src/pages-new/` and register them in `src/router.tsx`.
2. Compose pages from `src/components-new/` + `src/layout/` (`PageLayout`, `AppShell`, `Sidebar`, `TopBar`, `NotificationBell`).
3. If a shared primitive is missing (button, input, select, badge), add it to `src/components-new/` as a pure Tailwind v4 component. Do **not** import anything from `src/components/` or `@untitledui/*`.
4. For iconography, use `@mui/icons-material` (already a dependency and used by the existing layout/pages) or inline SVGs. Do not add `@untitledui/icons` imports.
5. Follow the 7 HARD GATES (skill `aiflow-ui-pipeline`) with Untitled UI references in the Figma gate treated as reference only, not as a requirement to emit UUI code.
6. Continue to render the Demo/Live `source` badge on every data-surface page (memory: *No silent mock data*).

**Cleanup (tracked follow-up, not blocking):**

- Delete `aiflow-admin/src/components/` subtree.
- Remove `@untitledui/icons` from `aiflow-admin/package.json`.
- Delete `aiflow-admin/src/pages-archive/` or confirm it is retained only as a reading reference (label as such).
- Re-run `npx tsc --noEmit` + journey E2E after deletion to confirm the app still compiles and routes.
- Update memory entry *UI hard gates* / *Figma quality* to reflect "Tailwind v4 + `components-new/`" as the baseline instead of Untitled UI.

This cleanup is deferred to a future Sprint H session after S90 coverage uplift. Rationale: the dead code is already dead — it costs nothing to leave it one more sprint, but removing it now expands S89 scope beyond "verify + decide".

## Rejected alternatives

### Option 1 — Adopt Untitled UI (rebuild `pages-new/` on UUI components)

Rejected. Cost: 2–3 UI sessions to rewrite 19 pages and ~12 shared components on top of a library that was already present in the repo and not used. No compensating benefit: `components-new/` already implements the primitives the pages need, Tailwind v4 already handles theming, and the journey E2E suite already targets the in-house components. Rebuilding on UUI would be work performed to undo work.

### Option 3 — Hybrid (keep UUI icons, keep Tailwind layouts)

Rejected as described in the S89 prompt. The premise — "icons are already in use, keep them" — does not hold. No icon from `@untitledui/icons` is imported anywhere in the active app. "Hybrid" would require *adding* UUI icon imports to preserve a sunk cost that is already zero. The honest name for the current state is Reject, not Hybrid.

### Option 4 — Re-evaluate after a full redesign cycle

Rejected. Memory entry *Figma Redesign Pipeline* notes that Untitled UI was "chosen for full redesign" but the actual implementation diverged. Deferring the decision keeps every future UI session asking the same question. The point of an ADR is to stop the drift; deferring reopens it.

## References

- Audit grep output: `aiflow-admin/src` on 2026-04-26 (captured inline above).
- `aiflow-admin/src/router.tsx` lines 7–31: all routed pages resolve to `./pages-new/…`.
- `aiflow-admin/vite.config.ts`: proxy `/api` and `/health` → `http://localhost:8102` (no UI-library coupling).
- Skill `aiflow-ui-pipeline`: 7 HARD GATES stay authoritative for UI pipeline, this ADR only constrains the library choice.
- Memory entries affected: *UI hard gates*, *Figma quality*, *Figma Redesign Pipeline* (to be updated after cleanup session ratifies removal).
