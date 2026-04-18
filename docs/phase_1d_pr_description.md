# Phase 1d — Adapter orchestration through `IntakePackageSink` (v1.4.3)

## Summary

- **All 5 source adapters now persist via a single canonical `IntakePackageSink`** — replacing per-adapter ad-hoc inserts (or, in the webhook case, no inserts at all). Adapters stay pure I/O transformers; the sink handles association resolution + insert + canonical event emission.
- **Webhook durability fix**: `POST /api/v1/sources/webhook` previously returned 202 + queued into the adapter's in-memory deque, but **nothing drained the queue → packages dropped on the floor**. G0.6 wires the sink directly into the route (Path A — sync); status changes 202→201.
- **Single FILE_UPLOAD persistence path**: `upload_package` HTTP route now delegates to the sink (G0.3) — eliminates the architectural risk of two writers for the same `FILE_UPLOAD` source_type.
- **Pre-existing failure triage**: `multi_source_e2e[email|file_upload]` (flagged in G0.2/G0.3) root-caused — test bypassed sink, hit 037 CHECK trigger. Fix: route through sink (G0.5/S84). Now 7/7.

## What changed

### Source code (4 files)

| File | Change | Driver |
|---|---|---|
| `src/aiflow/sources/sink.py` | **NEW** — `IntakePackageSink` orchestrator + `process_next` helper | G0.2 (architect Path B verdict) |
| `src/aiflow/intake/association.py` | **NEW** — shared associator helper extracted from `intake.py` | G0.2 |
| `src/aiflow/api/v1/intake.py` | `upload_package` → `sink.handle()` (single FILE_UPLOAD writer) | G0.3 |
| `src/aiflow/api/v1/sources_webhook.py` | `accept_webhook` → `sink.handle()`, status 202→201, new `get_intake_package_sink` dep | G0.6 |

Plus 1 sink bug fix:
- `_SOURCE_TYPE_LABELS` dict was keyed by `IntakeSourceType.name` but lookup uses `.value`. EMAIL passed by accident (value == name lowercased); File/Folder/Batch/Api would emit wrong labels in the persisted event. Re-keyed to `.value` strings (G0.3).

### Tests (8 new files, 1 updated)

| File | Tests | Driver |
|---|---|---|
| `tests/e2e/sources/conftest.py` | autouse `_deps._pool` reset (asyncpg loop binding trap) | G0.3 |
| `tests/e2e/sources/test_email_adapter_persistence.py` | 1 E2E (1 file + 1 desc → ORDER) | G0.2 |
| `tests/e2e/sources/test_file_adapter_persistence.py` | 1 E2E (description-bearing → ORDER) | G0.3 |
| `tests/e2e/sources/test_folder_adapter_persistence.py` | 1 E2E (deterministic `_note_event` path) | G0.3 |
| `tests/e2e/sources/test_batch_adapter_persistence.py` | 1 E2E (sink "mode-already-set" guard verified) | G0.4 |
| `tests/e2e/sources/test_api_adapter_persistence.py` | 1 E2E (HMAC signed, no descriptions) | G0.4 |
| `tests/e2e/sources/test_webhook_router_e2e.py` | 2 E2E (HTTP DB round-trip + invalid-sig negative) | G0.6 |
| `tests/integration/sources/test_webhook_router.py` | 8 tests updated (status 201, per-tenant cleanup, pool reset) | G0.6 |
| `tests/e2e/v1_4_1_phase_1b/test_multi_source_e2e.py` | repo.insert_package() → sink.handle() (triage) | S84 (G0.5) |

### Plan + infra docs

- `01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md` — G-matrix filled in (G1-G11, see below)
- `CLAUDE.md` — Session Workflow updated with `/auto-sprint` autonomous mode (DOHA-adapted, file-log notification)
- `.claude/commands/auto-sprint.md` (NEW, 283 lines) — autonomous session loop
- `scripts/send_notification.py` (NEW, 115 lines) — file-log notification helper

## Test deltas

| Suite | Before | After | Notes |
|---|---|---|---|
| Unit | 1898 | 1898 | Stable — sink + helper add no unit tests in this PR (covered by E2E) |
| Integration | 42 | 42 | 8 webhook tests updated (status 201, per-tenant cleanup) |
| E2E sources/ | 0 | **7** | 5 adapter (1 each) + 2 webhook |
| E2E v1_4_1_phase_1b/ | 7 (5 PASS + 2 FAIL) | **9 PASS** | multi_source 5/7 → 7/7, upload_package 2/2 |
| **Total E2E delta** | — | **+7 new + 2 fixed** | — |

## Acceptance Matrix (G-matrix)

| Gate | Description | Status |
|---|---|---|
| G1 | All 5 adapters persist via sink | PASS |
| G2 | 037 trigger never rejects live writes | PASS |
| G3 | Tenant isolation maintained | PASS |
| G4 | `source.package_persisted` event fires per adapter | PASS |
| G5 | ≥ 1 new E2E per adapter (delivered: 7) | PASS |
| G6 | Regression suite green | PASS |
| G7 | No Alembic migration added (037 head) | PASS |
| G8 | OpenAPI drift (webhook 202→201) | PARTIAL — regen due in G0.8 |
| G9 | Coverage gate (issue #7) | DEFERRED to v1.4.4 |
| G10 | multi_source_e2e triage | PASS |
| G11 | Webhook router sink wiring | PASS |

Full G-matrix with commit-level evidence in `01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md`.

## Migration notes

- **No new Alembic migration.** Head remains 037 (Phase 1c).
- **037 CHECK trigger behavior verified end-to-end**: blocks `intake_descriptions` insert when parent `intake_packages.association_mode` IS NULL. The new sink guarantees mode resolution before insert for description-bearing packages, so the trigger never fires on a live adapter write.
- **Webhook status code change (202 → 201)** is a contract change for HMAC-signed webhook callers. Documented in OpenAPI; drift-gate regen required pre-merge (queued for G0.8).

## Issue #7 (coverage gate) — DEFERRED

Decision (S86/G0.7): defer to **v1.4.4**. Phase 1d focused on adapter orchestration; coverage uplift from 65.67% → 80% requires test additions across 4 modules (provider abstractions, policy engine, observability glue, the new sink helper itself) and is out of scope. ADR note will be added to `docs/phase_1d_retro.md` (queued S87/G0.8).

## Out of scope

- **Webhook async-worker variant (Path B)**: would require a real persistent queue (Redis/SQS) for durability. Not justified by current webhook volume; revisit if scale demands it.
- **Gmail OAuth for `/auto-sprint`**: deferred to a separate session. File-log notification is the v1 mode.
- **Phase-merge / tag-cut hard boundary regex** for the auto-sprint loop — current STOP feltetel + iteration cap is sufficient.

## Sessions in this PR

| Session | Iter | Commit | Title |
|---|---|---|---|
| S80 | G0.1 | `d915594` + `3762fad` | Kickoff plan + writer audit |
| S81 | G0.2 | `44c1e6c` | EmailSourceAdapter wiring + sink + helper + E2E |
| S82 | G0.3 | `8f7d0c6` | File + Folder wiring + sink label fix + upload_package collapse |
| S83 | G0.4 | `abe402a` | Batch + Api wiring + 2 E2E |
| S83.5 (infra) | — | `ad3af7f` | `/auto-sprint` command + notification helper |
| S84 | G0.5 | `53a2d8f` | multi_source_e2e triage (sink-routed) |
| S85 | G0.6 | `6e5d4b1` | Webhook router sink wiring (Path A) + 2 E2E |
| S86 | G0.7 | `<this commit>` | G-matrix evidence + PR draft + issue #7 decision |

S87 / G0.8 (queued): PR cut on GitHub (`gh pr create`) + tag `v1.4.3-phase-1d` after merge + retro write (`docs/phase_1d_retro.md`).
