# AIFlow Phase 1d — Sprint Plan (v1.4.3: Adapter → `insert_package()` Orchestration Wiring)

> **Status:** **KICKOFF** 2026-04-17 in S80 / G0.1 (THIS session).
> **Datum (planned start):** 2026-04-17.
> **Branch:** `feature/v1.4.3-phase-1d-adapter-orchestration` (created from `main` at tag `v1.4.2-phase-1c` in S79 / F0.7; local HEAD `d915594` carries only the S80 kickoff prompt commit on top of `origin/main` `240676e`).
> **Phase 1c close:** merge commit `bd14519` on `main`, tag `v1.4.2-phase-1c`, PR #6 (2026-04-16).
> **Plan sources:** `docs/phase_1c_retro.md` §"Open front-line gap", `out/phase_1b_architect_review.md` §C1 (adapter→repo wiring originally deferred), writer audit table below.
> **Predecessor:** S79 / F0.7 — Phase 1c merge + tag + drift-gate encoding fix + retro PR #8.

---

## KONTEXTUS

### Phase 1c (v1.4.2) — CLOSED

- Merged to `main` 2026-04-16 (merge commit `bd14519`, tag `v1.4.2-phase-1c`, PR #6).
- Delivered F0.2 CI hygiene, F0.3 OpenAPI regen + drift gate, F0.4 canonical observability events across all 5 source adapters, F0.5 Alembic 036 `association_mode` backfill, F0.6 Alembic 037 CHECK trigger on `intake_descriptions`, F0.7 encoding fix + merge + tag + retro PR #8.
- Architect verdicts: G1–G9 all PASS on the acceptance matrix.
- Retro: `docs/phase_1c_retro.md` — flagged *"defence-in-depth complete, front-line still missing"*: the 037 CHECK trigger backstops future adapter-orchestration writes but no adapter currently drives it.
- Open follow-up: **issue #7** — coverage floor 80% vs actual 65.67%. Not a Phase 1d blocker but must be resolved before the next phase PR.

### Phase 1d (v1.4.3) — THIS SPRINT

Phase 1d wires the 5 source adapters (Email, File, Folder, Batch, API) through `IntakeRepository.insert_package()` so that incoming packages actually land in Postgres under tenant isolation, with `association_mode` set on every package that has descriptions. This closes the front-line gap the Phase 1c retro flagged and validates the 037 CHECK trigger against real adapter traffic (not synthetic fixtures).

Phase 1d is scoped as **net-new write-integration on top of a clean slate**. No hidden legacy persistence paths were found in the writer audit below — the only current writer is `api/v1/intake.py:465` (push-mode file upload), which already does everything we need adapters to do: auth-resolved `tenant_id`, associator run, `association_mode` inferred, `repo.insert_package()` call, structured log. The Phase 1d work is to replicate this contract inside (or adjacent to) each adapter.

---

## WRITER AUDIT — the factual gap map

Conducted 2026-04-17 in G0.1 via `grep -rn "insert_package\|intake_packages\|intake_descriptions" src/aiflow/` and companion scans for `IntakeRepository`, `get_pool`, per-adapter `association_mode` and `source_type` assignments.

| Adapter | `source_type` | transport | Persists today? | `association_mode` handling | `tenant_id` source | Gap vs `api/v1/intake:upload_package` |
|---|---|---|---|---|---|---|
| `EmailSourceAdapter` | `EMAIL` | pull | **NO** | NO (descriptions rarely present in email) | ctor injection (clean) | associator run conditional on descriptions, `insert_package()` call |
| `FileSourceAdapter` | `FILE_UPLOAD` | push | **NO** | NO | ctor injection (clean) | associator run, `insert_package()` call **AND** coordination with `api/v1/intake.py` which also writes `FILE_UPLOAD` rows (double-writer risk — see STOP FELTETELEK below) |
| `FolderSourceAdapter` | `FOLDER_IMPORT` | pull | **NO** | NO | ctor injection (clean) | associator run, `insert_package()` call |
| `BatchSourceAdapter` | `BATCH_IMPORT` | pull | **NO** | **YES** (already sets `pkg.association_mode` at `batch_adapter.py:492` when descriptions present) | ctor injection (clean) | only `insert_package()` hookup needed (association is already done) |
| `ApiSourceAdapter` | `API_PUSH` | push | **NO** | NO | ctor injection (clean) | router wiring (no FastAPI endpoint instantiates this adapter today), associator run, `insert_package()` call |
| *Reference:* `api/v1/intake.py` `upload_package()` | `FILE_UPLOAD` | push | **YES** (line 465) | YES (`_infer_mode` at line 477) | JWT `team_id` via `Depends(get_tenant_id)` | — (this is the target contract) |

**Key findings:**

1. **No hidden persistence path exists** — only `api/v1/intake.py` calls `insert_package()` / touches `intake_packages` / `IntakeRepository` today. Greenfield write integration, no legacy code to untangle.
2. **`SourceAdapter` base class has no persistence hook.** Lifecycle is `fetch_next() → acknowledge() | reject()`. Persistence must either become a base-class method (e.g. `persist(repo) -> None`) OR be driven by an external orchestrator/sink that sits between `fetch_next()` and `acknowledge()`. ADR-worthy design decision — G0.2 will pick one with architect review.
3. **Only `BatchSourceAdapter` handles `association_mode` end-to-end today.** The other 4 adapters need the associator + `_infer_mode()` logic — a shared helper extracted from `api/v1/intake.py` (don't copy-paste into 4 adapters).
4. **Tenant isolation (G3) is structurally clean at the adapter surface** — every adapter takes `tenant_id: str` as a ctor argument, never from the package payload. The orchestrator layer still must resolve it from auth context (JWT `team_id` / api-key owner) before instantiating the adapter.
5. **`FileSourceAdapter` vs `api/v1/intake.py` overlap** — both produce `IntakeSourceType.FILE_UPLOAD` rows. Phase 1d must decide whether `FileSourceAdapter` replaces the `upload_package` endpoint's internals, or whether the two coexist with different use cases (e.g. server-side-watched directory vs HTTP upload). This is a scope-gating STOP FELTETEL.
6. **`ApiSourceAdapter` is not reachable from any FastAPI router today.** Phase 1d needs to either add a `/sources/webhook` router or treat the adapter as internal-only (invoked by a worker). Another scope-gating decision.

---

## SPRINT OVERVIEW

```
Phase 1d (v1.4.3) — proposed 6 sessions / 5 working days / 5 adapter deliverables + acceptance gate + merge
  Week 0 Day 0   : Sprint kickoff + writer audit (THIS session — G0.1)
  Week 1 Day 1   : EmailSourceAdapter wiring + shared associator helper + E2E   — G0.2 / S81
  Week 1 Day 2   : FileSourceAdapter + FolderSourceAdapter wiring + E2E         — G0.3 / S82
  Week 1 Day 3   : BatchSourceAdapter + ApiSourceAdapter wiring + E2E           — G0.4 / S83
  Week 1 Day 4   : Cross-adapter acceptance gate (G-matrix) + coverage gate (#7) — G0.5 / S84
  Week 1 Day 5   : PR review cycle + merge + tag `v1.4.3-phase-1d` + retro      — G0.6 / S85
```

**The audit does not yet justify splitting Phase 1d into 1d + 1e.** All 5 adapters have the same shape of work (associator + `insert_package` + tenant plumbing), and BatchSourceAdapter's existing `association_mode` logic is transferable to the other 4 as a shared helper. If the G0.2 design decision introduces orchestrator-layer changes that leak beyond the adapter module (e.g. into `api/v1/intake.py`'s router), reopen the split question at the STOP FELTETEL below.

---

## WEEK 0 — Kickoff (Day 0, session G0.1 — THIS session)

**Goal:** land the Phase 1d governance scaffolding — plan doc, writer audit, G-matrix skeleton, S81 prompt — so Day 1 can start on the first-adapter wiring without rework.

- [x] Branch `feature/v1.4.3-phase-1d-adapter-orchestration` already cut from `main` @ tag `v1.4.2-phase-1c` in S79 / F0.7; local HEAD `d915594` is one commit ahead of `origin/main` `240676e` (the S80 prompt commit only).
- [x] Write this plan document (`01_PLAN/session_S80_v1_4_3_phase_1d_kickoff.md`).
- [x] Run writer audit, produce the gap-map table above.
- [x] Sketch G-matrix skeleton (unticked; see next section).
- [x] Queue S81 prompt (`session_prompts/S81_G0.2_prompt.md`) for EmailSourceAdapter wiring.
- [ ] Commit + push + `/session-close G0.1`.

**Day 0 exit:** plan doc + S81 prompt committed, `ruff check src/ tests/` clean, `pytest --collect-only` unchanged from Phase 1c close, 1886 unit + 4 alembic integration tests still green (verified this session — see preconditions log).

---

## WEEK 1 — Execution

### Day 1 — EmailSourceAdapter wiring + shared associator helper (G0.2 / S81)

**Goal:** wire the first adapter end-to-end so the pattern is proven; extract the reusable associator helper now so the other 4 adapters in G0.3/G0.4 are short, repetitive PRs.

Work items:
- Design decision (ADR-style note in the PR): `persist()` method on `SourceAdapter` base class vs external orchestrator/sink. Record the trade-off: base-class method keeps lifecycle cohesive but couples adapters to `IntakeRepository`; orchestrator keeps adapters testable in isolation at the cost of one extra indirection layer. Architect review gate.
- Extract `aiflow/intake/association.py:resolve_mode_and_associations(package, *, explicit_map, filename_rules, forced_mode) -> IntakePackage` from `api/v1/intake.py` (keep `_infer_mode` and the associator-call sequence identical; add unit tests covering the 4 mode-selection branches).
- Wire `EmailSourceAdapter` through the chosen persistence path: after `fetch_next()` produces a package, call associator helper (no-op when descriptions absent), then `repo.insert_package(package)`, then emit new canonical event `source.package_persisted` (extends observability enum).
- Add 1 E2E test against real Postgres: fake IMAP → adapter → repo → read-back asserts `association_mode` + `tenant_id` + `source_type=EMAIL`.

**Day 1 exit:** 1 new E2E green, 1886 unit + new associator-helper unit tests green, `source.package_persisted` event added to `aiflow.sources.observability`, architect sign-off on persistence pattern recorded in PR body.

### Day 2 — FileSourceAdapter + FolderSourceAdapter wiring (G0.3 / S82)

**Goal:** two push/pull variants of the same pattern land together since they share the filesystem materialisation helper `aiflow/sources/_fs.py`.

Work items:
- Apply the G0.2 persistence pattern to `FileSourceAdapter`. **Pre-commit check:** does `api/v1/intake.py:upload_package` still own the HTTP-upload path, or does the new `FileSourceAdapter` wiring replace it? If replace: deprecate `upload_package` behind the new adapter instantiation and update E2E tests (scope-add — STOP FELTETEL if deeper than routing).
- Apply the G0.2 pattern to `FolderSourceAdapter`.
- 2 new E2E tests — one per adapter — against real Postgres.

**Day 2 exit:** 2 new E2E green, 3 of 5 adapters wired (Email + File + Folder), no regression in existing 403 Phase 1a/1b E2E.

### Day 3 — BatchSourceAdapter + ApiSourceAdapter wiring (G0.4 / S83)

**Goal:** finish the 5. Batch is the short one (already sets `association_mode`, only needs `insert_package()` hookup). Api is the long one (needs a FastAPI router if we decide to expose it externally).

Work items:
- `BatchSourceAdapter`: route its existing `pkg` (with `association_mode` already set at line 492) through the persistence pattern. Delete any associator no-op branch since Batch already handles that path.
- `ApiSourceAdapter`: decide exposure model (internal worker vs new `/sources/webhook` router). If router: add to `aiflow/api/v1/` with `source_type=API_PUSH`, tenant resolution via the existing `get_tenant_id` dependency. If internal: document who instantiates it (worker? cron? test harness?).
- 2 new E2E tests — one per adapter.

**Day 3 exit:** 5 of 5 adapters wired, 5 new E2E tests green, full canonical-event triple (`received`/`persisted`/`rejected`) fires on every adapter.

### Day 4 — Cross-adapter acceptance gate + coverage gate (G0.5 / S84)

**Goal:** close the G-matrix, resolve issue #7.

Work items:
- Author `docs/phase_1d_acceptance_report.md` with G1–G9 (see skeleton below) filled with commit-level evidence.
- Issue #7 coverage floor decision: either raise actual coverage to 80% by adding the obvious missing tests (preferred if the delta is < ~50 tests) or ADR-document an explicit temporary exception in the PR body with a follow-up issue for the next phase.
- OpenAPI regen + drift-gate green (no API surface changes expected if ApiSourceAdapter stays internal; if `/sources/webhook` was added in G0.4, regen + review).
- Full regression: 1886 unit + 42 integration + 408+ E2E (403 existing + 5 new) all green.

**Day 4 exit:** acceptance report committed, issue #7 either closed or explicit-deferral'd, PR body drafted, regression baseline re-captured.

### Day 5 — PR review cycle + merge + tag (G0.6 / S85)

Work items:
- Open PR against `main` with the G-matrix acceptance report linked.
- Architect + security-reviewer agent passes.
- Merge squash, tag `v1.4.3-phase-1d`, update CLAUDE.md (3 sites — overview header, git workflow branch pointer, current plan reference).
- Retro: `docs/phase_1d_retro.md`.

**Day 5 exit:** `main` at tag `v1.4.3-phase-1d`, retro committed, CLAUDE.md refreshed, NEXT.md queued for Phase 1e kickoff (adapter orchestration → state machine handoff, per 101 plan).

---

## ACCEPTANCE MATRIX (G-matrix — filled in G0.7 / S86)

| Gate | Description | Evidence (commit) | Status |
|---|---|---|---|
| **G1** | All 5 source adapters (Email, File, Folder, Batch, Api) persist through `IntakeRepository.insert_package()` via the canonical `IntakePackageSink` | `44c1e6c` (Email) + `8f7d0c6` (File+Folder) + `abe402a` (Batch+Api) | PASS |
| **G2** | Every persisted package with ≥1 description has `association_mode` set; Alembic 037 CHECK trigger on `intake_descriptions` never rejects a live adapter write during E2E. Trigger-fire count: 0 in all 7 multi_source matrix scenarios + 5 dedicated source E2E. | `8f7d0c6` (sink resolves mode for description-bearing packages) + `53a2d8f` (multi_source_e2e proves end-to-end) | PASS |
| **G3** | Tenant isolation honoured end-to-end. `tenant_id` resolved from auth context (JWT `team_id` claim or api-key owner) at adapter instantiation — never from payload/form fields. | Pre-existing baseline; unchanged by Phase 1d. `intake.py:get_tenant_id` + `sources_webhook.py` env-driven tenant. | PASS |
| **G4** | Canonical observability event `source.package_persisted` fires on every adapter in addition to the Phase-1c `source.package_received` / `source.package_rejected` triad. | `44c1e6c` (sink emits) + `8f7d0c6` (label-key bug fix: dict re-keyed `.value`) | PASS |
| **G5** | ≥ 1 new E2E test per adapter exercising a real Postgres write + read-back. Real services only — no mocks. | 5 dedicated tests `tests/e2e/sources/test_{email\|file\|folder\|batch\|api}_adapter_persistence.py` (`44c1e6c` + `8f7d0c6` + `abe402a`) + 2 webhook E2E `test_webhook_router_e2e.py` (`6e5d4b1`) | PASS (7 new E2E vs 5 planned) |
| **G6** | Regression: 1898 unit + 42 integration (incl. 4 alembic + 8 webhook) + existing E2E all green. | All baselines stable; multi_source_e2e went 5/7 → **7/7** (`53a2d8f`) | PASS |
| **G7** | No Alembic migration added (schema unchanged). | `alembic current` = 037 (Phase 1c head); no 038 added. | PASS |
| **G8** | OpenAPI drift gate. Webhook router status code 202→201 IS a schema surface change in G0.6; drift-gate regen required pre-merge. | `6e5d4b1` (status code change) — drift regen queued for G0.8 PR cut | PARTIAL — regen needed |
| **G9** | Coverage gate (issue #7) — **DEFERRED to v1.4.4** (Option A, decided in S86/G0.7). Phase 1d focused on adapter orchestration; coverage uplift requires test additions across 4 modules and is orthogonal scope. | One-liner in PR body + ADR note in `docs/phase_1d_retro.md` (queued S87) | DEFERRED |
| **G10** | multi_source_e2e triage (sink-routed) — pre-existing `test_all_sources_produce_valid_intake_package[email\|file_upload]` failures resolved by routing through `IntakePackageSink`. | `53a2d8f` | PASS |
| **G11** | Webhook router sink wiring (Path A — sync sink, status 202→201). Webhook now durable end-to-end. | `6e5d4b1` | PASS |

**Result:** 9 PASS + 1 PARTIAL (G8 — OpenAPI drift regen due in G0.8) + 1 DEFERRED (G9 — coverage to v1.4.4). Phase 1d MERGE candidate.

---

## RISK & MITIGATION

| Risk | Mitigation | Residual |
|------|------------|----------|
| G0.2 persistence pattern (base-class vs orchestrator) picks the wrong abstraction | Architect review gate in G0.2; record both options with trade-offs in the PR body so reversal in a later phase is cheap | LOW-MEDIUM |
| `FileSourceAdapter` + `api/v1/intake.py:upload_package` double-write on `FILE_UPLOAD` rows | In G0.3, either consolidate through the adapter OR keep the API endpoint and skip adapter wiring for `FILE_UPLOAD` with ADR | MEDIUM |
| `ApiSourceAdapter` exposure decision leaks scope (new router, new auth, new OpenAPI surface) | If the decision in G0.4 requires a new router, split into Phase 1e and keep Phase 1d as "4 of 5 adapters wired" | MEDIUM |
| 037 CHECK trigger fires on a live adapter write (e.g. descriptions present, mode not set) | E2E tests intentionally cover this path; trigger-fire count = 0 is a G2 assert, not an observation | LOW |
| Coverage floor (issue #7) blocks merge if delta > expected | Time-box coverage work to 1 session (G0.5); if delta requires > 1 session, accept ADR-documented deferral to Phase 1e | LOW |
| Shared associator-helper extraction breaks `api/v1/intake.py` contract | Helper is a pure refactor with unit tests in G0.2 before the adapter wiring starts; existing upload-package E2E is the regression signal | LOW |

---

## ROLLBACK PLAN

- Phase 1d introduces NO Alembic migration (G7). Rollback is pure code revert.
- Per PR: `git revert` the squash merge, roll back `v1.4.3-phase-1d` tag. Phase 1c state is immediately restored. The 037 CHECK trigger remains active regardless — it was the defence-in-depth layer, not the front-line wiring.
- If a single adapter needs to be reverted post-merge but others kept: per-adapter feature-flag via config (`adapters.email.persistence_enabled`) defaulted to `true`. Document the flag in the PR body.

---

## STOP FELTETELEK

ALLJ MEG es kerj iranymutatast, ha:

- **HARD:** writer audit surfaces a schema gap (e.g. an adapter needs a new column to carry association-mode intent or routing metadata) → scope-add requiring a new Alembic migration; user decides before planning it.
- **HARD:** `FileSourceAdapter` wiring (G0.3) would cause double-writes for `FILE_UPLOAD` rows vs `api/v1/intake.py:upload_package` → decide in-session whether to deprecate the endpoint, consolidate through the adapter, or ADR-document the coexistence.
- **HARD:** `ApiSourceAdapter` exposure (G0.4) requires a new FastAPI router + auth plumbing + OpenAPI surface changes beyond the adapter module → security-review gate before coding; likely Phase-1e split.
- **HARD:** G0.2 persistence-pattern decision (base-class vs orchestrator) cannot reach architect consensus in one session → pause and escalate before 4 adapters inherit the wrong abstraction.
- **SOFT:** issue #7 coverage resolution requires > 1 session → accept ADR-documented deferral to Phase 1e (not a merge blocker on its own if documented).
- **SOFT:** Phase 1d scope is estimated to exceed 6 sessions mid-sprint → split into Phase 1d (adapters 1–3) and Phase 1e (adapters 4–5 + acceptance).

---

## REFERENCIAK

- `docs/phase_1c_retro.md` — §"Open front-line gap" — Phase 1c's explicit hand-off to Phase 1d.
- `out/phase_1b_architect_review.md` §C1 — original deferred "adapter → repo wiring" condition.
- `src/aiflow/api/v1/intake.py:341-495` — `upload_package` reference contract (auth → package build → associator → `insert_package` → log).
- `src/aiflow/state/repositories/intake.py:32-38` — `IntakeRepository.insert_package(package)` entry point.
- `src/aiflow/sources/base.py:57-89` — `SourceAdapter` abstract interface (`fetch_next`/`acknowledge`/`reject` — no persistence hook today).
- `src/aiflow/sources/batch_adapter.py:149,207,435-492` — the one adapter that already sets `association_mode`; reference for the pattern.
- `src/aiflow/sources/observability.py` — Phase 1c canonical event helper; Phase 1d extends with `source.package_persisted`.
- `alembic/versions/037_intake_descriptions_check.py` — the CHECK trigger this phase proves against real traffic.
- `01_PLAN/session_S73_v1_4_2_phase_1c_kickoff.md` — predecessor plan (structural template for this doc).
- `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` §4 — phase ordering; Phase 1d precedes state-machine handoff (Phase 1e).
- `.claude/skills/aiflow-testing.md` — real-services testing rules (Postgres/Redis/LLM never mocked).
- `.claude/skills/aiflow-pipeline.md` — adapter conventions.
- GitHub issue #7 — coverage floor 80% vs 65.67% (G9).

---

## SESSION CHAINING

```
S80 / G0.1 (THIS) — kickoff + writer audit + plan doc + S81 queued
S81 / G0.2        — Day 1: EmailSourceAdapter wiring + shared associator helper + E2E
S82 / G0.3        — Day 2: FileSourceAdapter + FolderSourceAdapter wiring + E2E
S83 / G0.4        — Day 3: BatchSourceAdapter + ApiSourceAdapter wiring + E2E
S84 / G0.5        — Day 4: Acceptance gate (G-matrix) + coverage gate (issue #7)
S85 / G0.6        — Day 5: PR + merge + tag v1.4.3-phase-1d + retro
```

At end of each session: `/session-close <id>` generates `session_prompts/NEXT.md` for the next Day N.

---

*Phase 1d session: S80 = G0.1 (Adapter → insert_package() orchestration wiring — kickoff + audit + plan).*
