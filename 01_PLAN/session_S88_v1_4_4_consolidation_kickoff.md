# AIFlow Sprint H — v1.4.4 Consolidation Sprint Kickoff

> **Datum:** 2026-04-25
> **Branch:** `feature/v1.4.4-consolidation`
> **Base tag:** `v1.4.3-phase-1d` (merge commit `0d669aa`)
> **Scope:** NOT a feature sprint. 4-session stabilization to close drift from Phase 1a-1d, get frontend dev-env green, and write the master roadmap that will feed the next auto-sprint.

---

## Why this sprint exists

Post-Phase-1d audit (2026-04-25) revealed:

1. **Version drift**: `src/aiflow/_version.py = "1.3.0"`, `pyproject.toml = "1.4.0"`, tag `v1.4.3-phase-1d`, CLAUDE.md claims v1.4.3. `/health` endpoint serves a stale version string.
2. **Frontend dev-env not demo-ready**: CLAUDE.md documents port `5174`; `aiflow-admin/vite.config.ts` binds `5173`. UI is not running. 6 journey E2E tests exist but no recent pass evidence.
3. **Stale test**: `tests/e2e/v1_4_1_phase_1b/test_alembic_034.py` asserts head == `"035"`, but head has been `"037"` since Phase 1c (2026-04-16). Flagged in Phase 1d retro as v1.4.4 backlog.
4. **Coverage gate deferred**: issue #7 — `65.67%` actual, `80%` floor. Deferred from Phase 1d.
5. **No master roadmap**: `01_PLAN/` has 169 files but no single-source forward-looking queue. Auto-sprint has to reconstruct scope from phase-kickoff docs each time.
6. **Stale session-prompt disk debt**: `session_prompts/S46_*.md` through `S72_*.md` (~25 untracked files) are archives of already-merged Sprint D/E/F work. Cleaning them clears signal from the git status pane.
7. **Untitled UI fragmentation**: new `aiflow-admin/src/pages-new/` bypasses the Untitled UI component layer in `src/components/`. No ADR documenting the choice. Future UI sessions will ask "which path?" each time.

Addressing items 1–6 unblocks efficient, one-feature-per-session auto-sprints. Item 7 gets a decision ADR (not a full rewrite).

---

## Session breakdown (4 sessions)

| Session | Scope | Deliverable |
|---|---|---|
| **S88 / v1.4.4.1** | Version reconcile, port doc fix, stale session-prompt archive, `test_alembic_034` fix, NEXT.md cleanup | 1 commit, all regression green |
| **S89 / v1.4.4.2** | Frontend dev-env live: UI up on correct port, 6 journey E2E green `--headed`, Untitled UI ADR | `01_PLAN/ADR-UI-Library.md`, E2E report in `out/` |
| **S90 / v1.4.4.3** | Coverage gate uplift: 65.67% → 80%. Issue #7 closes. | Coverage report, gate flip to `fail_under=80` |
| **S91 / v1.4.4.4** | Master `01_PLAN/ROADMAP.md` — Phase 1e (worker-loop), Phase 1f (skill system modernize), v1.4.x housekeeping queue, Phase 2 (Gmail OAuth, multi-tenant DWH). PR cut + tag `v1.4.4`. | Roadmap, PR, tag |

After S91: `/auto-sprint max_sessions=12` can consume the ROADMAP queue, one-feature-per-session.

---

## Invariants for this sprint

- **No new features.** Only drift-close, cleanup, documentation.
- **No DB migrations.** Alembic head stays at `037` across this sprint.
- **Hard-green regression per session.** Any red test that wasn't pre-existing → halt.
- **One PR total** at S91 end. S88-S91 land as consecutive commits on one branch.
- **Coverage gate does NOT flip to 80% until S90.** Keep existing waiver through S88-S89.

---

## Stop conditions

- **HARD:** Any Phase 1a-1d test breaks during version/port reconcile → halt, root-cause.
- **HARD:** UI journey E2E in S89 reveals a real backend regression (not env) → halt, open bug.
- **HARD:** Coverage uplift in S90 forces changes to shipped Phase 1a-1d contracts → halt, scope-check.
- **SOFT:** S91 roadmap doc grows past 2 hours of writing → cut scope to "next 2 phases only", rest follow-up.

---

## References

- Phase 1d retro: `docs/phase_1d_retro.md`
- Issue #7 (coverage): deferred in Phase 1d G0.7
- Stale test: `tests/e2e/v1_4_1_phase_1b/test_alembic_034.py:118,137`
- Port source-of-truth: `aiflow-admin/vite.config.ts:9` (`5173`)
- Version source-of-truth: `src/aiflow/_version.py` (currently `1.3.0`, must bump)

*Sprint H = v1.4.4 Consolidation. 4 sessions projected. Target close: 2026-04-28.*
