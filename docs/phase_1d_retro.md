# Phase 1d — Retrospective

> **Sprint window:** 2026-04-17 → 2026-04-24 (8 sessions, G0.1 → G0.8)
> **PR:** [#9](https://github.com/kassaiattila/AI_FLow_Framework/pull/9) — merged 2026-04-24
> **Merge commit:** `0d669aa`
> **Tag:** `v1.4.3-phase-1d`
> **Predecessor:** `v1.4.2-phase-1c` (Phase 1c MERGED 2026-04-16, PR #6 / `bd14519`)

## Scope delivered

Adapter orchestration refactor — all 5 source adapters (Email, File, Folder, Batch, Api) + the webhook HTTP router + the `upload_package` HTTP route now persist `IntakePackage` rows through a single canonical `IntakePackageSink` that owns association-mode resolution and canonical event emission. Adapters are pure I/O transformers; persistence is centralized.

| G | Session | Commit | Deliverable |
|---|---|---|---|
| G0.1 | S80 | `d915594` + `3762fad` | Kickoff plan + writer audit (where do persistence calls live today?) |
| G0.2 | S81 | `44c1e6c` | EmailSourceAdapter → sink. Sink + helper extracted (`sources/sink.py`, `intake/association.py`). E2E `test_email_adapter_persistence.py`. |
| G0.3 | S82 | `8f7d0c6` | File + Folder → sink; `upload_package` HTTP route collapsed onto sink; `_SOURCE_TYPE_LABELS` keyed-by-value fix; autouse pool reset conftest; 3 E2E. |
| G0.4 | S83 | `abe402a` | Batch + Api → sink; 2 E2E. |
| G0.5 | S84 | `53a2d8f` | `multi_source_e2e` triage — 037 CHECK trigger root-cause, reroute test through sink; 2 subtests 5/7 → 7/7. |
| G0.6 | S85 | `6e5d4b1` | Webhook router sink wiring (Path A sync); status 202→201; 2 E2E. |
| G0.7 | S86 | `9258bdf` | G-matrix evidence filled in; PR description drafted; issue #7 deferred to v1.4.4. |
| G0.8 | S87 | `59c98b6` + `<this commit>` | OpenAPI regen (webhook 202→201 drift); PR #9 cut; merged by user; tag cut; retro. |

## Test deltas

| Suite | Before | After | Delta |
|---|---|---|---|
| Unit | 1898 | 1898 + 2 new files (`tests/unit/intake/test_association.py`, `tests/unit/sources/test_sink.py`) | Stable |
| Integration | 42 | 42 (8 webhook tests updated for status 201 + per-tenant cleanup) | Stable |
| E2E `sources/` | 0 | **7** (5 adapter × 1 each + 2 webhook) | +7 |
| E2E `v1_4_1_phase_1b/` | 5 PASS + 2 FAIL | 7 PASS (multi_source) | +2 fixed |

## G-matrix outcome

G1–G7, G10, G11, G8: **PASS**. G9 (coverage): **DEFERRED** to v1.4.4 (issue #7).

---

## What worked

- **Option B (sink + helper extraction, G0.2 architect verdict)**. Writing the sink as a standalone module (`sources/sink.py`) with a small `process_next(adapter, sink)` helper, and pulling the associator into `intake/association.py`, gave every adapter the same 3-line handoff. Once the sink existed, G0.3 (File+Folder), G0.4 (Batch+Api), and G0.6 (webhook) were routine.
- **Autouse pool reset conftest (G0.3).** `tests/e2e/sources/conftest.py` autouse-resets `aiflow.api.deps._pool` between tests. This killed the asyncpg event-loop binding trap (see `feedback_asyncpg_pool_event_loop.md`) that would otherwise silently break per-function pytest-asyncio suites. Every subsequent sources/ E2E added just one function + benefited.
- **Shortcut cap log in `/auto-sprint` (S83.5).** The loop logs before exiting on `max_sessions` cap, so you can grep the state file and see exactly which session tripped the cap without wasted wakeups.
- **Per-tenant cleanup pattern (G0.6).** Instead of `DELETE FROM intake_packages` between webhook tests, use per-tenant `tenant_id` scoping. This co-existed cleanly with autouse pool reset and avoided cross-test flakiness.
- **PR description drafted one session ahead (G0.7).** `docs/phase_1d_pr_description.md` was written in G0.7 before the PR cut, so G0.8 was mechanical: regen OpenAPI, commit, push, `gh pr create --body-file`.
- **Issue #7 defer decision documented in G0.7.** Kept scope tight. Phase 1d shipped as a focused adapter-orchestration PR instead of getting entangled with a coverage-uplift detour.

## What surprised us

- **Webhook router pre-existed but persisted nothing (G0.6).** `POST /api/v1/sources/webhook` was already wired, returned 202 Accepted, and queued into `_webhook_queue` (a module-level `collections.deque`). But nothing drained the queue → every webhook POST dropped on the floor. This was a **live durability bug** in production code, not a refactor gap. G0.6 wired the sink directly into the route (Path A sync), which flipped status to 201 Created (persisted) and closed the bug.
- **`_SOURCE_TYPE_LABELS` dict bug (G0.3).** Dict was keyed by `IntakeSourceType.name` (e.g. `"EMAIL"`) but lookup used `.value` (e.g. `"email"`). EMAIL passed by accident because its `.value` equals `.name.lower()`. File / Folder / Batch / Api would have emitted wrong labels in the persisted event. Caught only because G0.3 added concrete File + Folder assertions that compared the emitted label. **Fix:** re-key to `.value` strings. Lesson: enum `.name` vs `.value` is a common silent miscoupling — test both.
- **ruff strips unused imports mid-Edit (G0.3 + G0.6).** When adding an import + its usage across two Edit calls, ruff's format-on-save (via the `/lint-check` flow) removed the just-added import before the usage was written. Lesson: add import + usage in the **same** Edit call, or suppress the ruff hook for the interstitial edit.
- **Full-E2E sweep in G0.8 surfaced two pre-existing failures not in Phase 1d's path.** (1) UI Playwright suites (67 failed + 132 errors) need the admin UI dev server at 5174 — environmental, pre-existing baseline. (2) `test_alembic_034::test_migration_034_source_type_hardening` asserts alembic head == `"035"` but Phase 1c moved head to `"037"` on 2026-04-16. **Neither was Phase 1d-caused.** The latter is a stale test that should have been caught in the Phase 1c retro — queued as a follow-up for v1.4.4.

## What we'd change

- **Webhook async-worker variant (Path B) would have been overkill.** We picked Path A (sync sink in the route) because webhook volume doesn't justify a persistent queue (Redis/SQS). If scale demands it, Path B is still on the table, but the sync path is correct for v1.4.3.
- **Coverage gate (issue #7) could have been folded into Phase 1d if the scope budget allowed.** Current coverage sits at 65.67%; the repo-wide floor is 80%. Uplift requires test additions across provider abstractions, policy engine, observability glue, and the new sink helper itself — roughly a 2-day detour. Right call to defer to v1.4.4 and keep Phase 1d focused.
- **Stale alembic test should have been updated in Phase 1c.** `test_alembic_034` asserting head == "035" was correct at Phase 1b tip but became stale the moment Phase 1c's 036 + 037 landed. The Phase 1c retro should have swept for `head == "0N"` assertions across the test tree. Queued for v1.4.4.
- **Ruff autoformat interaction with multi-step Edits.** The ordering constraint (import + usage same Edit) should be a codified rule in `feedback_` memory. Added to backlog.

## Auto-sprint mechanism (S83.5 infra)

`/auto-sprint` was introduced at S83.5 as process infra, not scope. Outcome: validated end-to-end across **4 iterations** (S83 G0.4 → S84 G0.5 → S85 G0.6 → S86 G0.7) with the `ScheduleWakeup ~90s` loop. File-log notification mode (`.notifications.log` append-only) worked; no Gmail OAuth needed. State file (`.auto_sprint_state.json`) is durable and gitignored.

Observed iteration count at G0.8 entry: `iteration=4, max_sessions=4, last_session_id=S86, last_commit=9258bdf` — loop naturally exited on cap after G0.7.

**What we'd keep:** file-log mode as v1 default, the cap-log-on-exit shortcut, the per-iteration state snapshot.
**What we'd improve:** optional Gmail OAuth notification as v2 (already referenced in CLAUDE.md as Phase 2), a phase-merge regex hard-stop so the loop can't accidentally cross a tag boundary.

## Next sprint candidates

- **Phase 1e — worker-loop driver for `process_next` patterns.** The `process_next(adapter, sink)` helper is called by ad-hoc test code today; a framework-level driver loop (polling / queue-consumer) would make the Batch + Api adapters production-ready for long-running ingestion.
- **v1.4.4 — coverage gate uplift + alembic-test sweep.** Issue #7 (coverage 65.67% → 80% floor), plus the stale `test_alembic_034` / any other `head == "0N"` assertions across the tree.
- **Gmail OAuth for `/auto-sprint`.** Phase 2 notification mode (referenced in `DOHA/01_PLAN/19_DOHA_AUTO_SPRINT_GUIDE.md`). File-log is fine for solo dev; Gmail is needed if you want mobile push when running auto-sprint overnight.
- **Phase-merge hard-boundary regex for `/auto-sprint`.** Defensive guard so the loop stops if it detects a tag commit or merge-to-main between iterations.
