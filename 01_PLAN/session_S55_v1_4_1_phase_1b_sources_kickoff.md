# AIFlow Phase 1b — Sprint Plan (v1.4.1: Source Adapters)

> **Status:** FINALIZED in S55 / E0.1 (2026-04-15).
> **Datum (planned start):** 2026-04-21 (Monday after Phase 1a merge).
> **Branch:** `feature/v1.4.1-phase-1b-sources` (created from `main`, tag `v1.4.0-phase-1a`).
> **Phase 1a close:** commit `f48ee77` on `main` (merged PR #2).
> **Plan sources:** `01_PLAN/101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` (N2 email, R1 file-connector wrap, N4 association), `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` Section 4.
> **Predecessor:** S54 / D0.11 — Phase 1a demo + PR + skeleton.

---

## KONTEXTUS

### Phase 1a (v1.4.0) — CLOSED

- Foundation layer merged to `main` 2026-04-15 (squash commit `f48ee77`), tag `v1.4.0-phase-1a`.
- IntakePackage + PolicyEngine + ProviderRegistry + SkillInstance.policy_override + backward compat shim.
- 199 Phase 1a E2E tests, 1674 unit tests, 114 backward-compat regression tests, Alembic 032 + 033.

### Phase 1b (v1.4.1) — THIS SPRINT

Source adapters take raw inputs (email, file, folder, batch, webhook) and produce `IntakePackage` objects ready for the policy/provider pipeline built in Phase 1a. Phase 1b also closes N4 (file ↔ description association) and adds the canonical `POST /api/v1/intake/upload-package` multipart endpoint.

---

## SPRINT OVERVIEW

```
Phase 1b (v1.4.1) — 3 weeks / 15 working days / 5 source adapters + association + endpoint
  Week 0 Day 0       : Sprint kickoff (THIS session — E0.1)
  Week 1 Day 1-5     : SourceAdapter ABC impl polish + Email + File adapters
  Week 2 Day 6-10    : Folder + Batch + API (webhook) adapters
  Week 3 Day 11-15   : N4 association + upload-package endpoint + multi-source E2E + gate
```

---

## WEEK 0 — Kickoff (Day 0, session E0.1 — THIS session)

**Goal:** lay the shared foundation so Week 1 can start implementing adapters on Day 1 without rework.

- [x] Create `feature/v1.4.1-phase-1b-sources` from `main` after Phase 1a merge.
- [x] `src/aiflow/sources/__init__.py` + `src/aiflow/sources/base.py` — `SourceAdapter` ABC + `SourceAdapterMetadata` Pydantic descriptor.
- [x] `tests/unit/sources/test_base.py` — ≥10 contract tests (ABC enforcement, metadata shape, lifecycle invariants).
- [x] `tests/e2e/v1_4_1_phase_1b/` — 7 placeholder files, all `pytest.mark.skip(reason="Phase 1b implementation pending")`.
- [x] Sprint plan finalized (this document).

**Day 0 exit:** `ruff check` clean, `pytest tests/unit/` still 1674 PASS + new sources contract tests, E2E collect adds 7 skipped without errors.

---

## WEEK 1 — Email + File source adapters

### Day 1 — `SourceAdapter` integration wiring
- Wire `ProviderRegistry`-style helper (`SourceAdapterRegistry`) for `source_type` lookup.
- Alembic migration `034_source_type.py`: backfill `intake_packages.source_type` default `"legacy"`, add CHECK constraint.
- Shared test fixtures in `tests/e2e/v1_4_1_phase_1b/conftest.py` (tenant, storage root, intake repo, policy engine).

### Day 2 — `EmailSourceAdapter` IMAP backend (E1.1-A)
- `src/aiflow/sources/email_adapter.py` — `EmailSourceAdapter` class, `ImapBackend` impl.
- MIME parsing: subject/body text, attachments → `IntakeFile` with `raw_bytes_ref`.
- Unit tests: ≥15 (IMAP auth fail, multipart, attachment size guard, charset fallback).

### Day 3 — `EmailSourceAdapter` Outlook COM backend (E1.1-B) — optional
- `OutlookComBackend` impl using `pywin32`. **STOP feltetel:** if pywin32 unavailable on target host → downgrade to IMAP-only for v1.4.1, file tech-debt ticket for v1.4.2.
- Backend auto-selection (env `AIFLOW_EMAIL_BACKEND`, default `imap`).
- Unit tests: ≥10 (COM presence probe, folder walk, attachment extraction).

### Day 4 — `FileSourceAdapter` (E1.2)
- `src/aiflow/sources/file_adapter.py` — single-file entry producing `IntakePackage` with exactly 1 `IntakeFile`.
- Routes via existing `PolicyEngine` for parser/classifier resolution (no new policy code).
- Unit tests: ≥15 (MIME detection, size guard, tenant storage prefix).

### Day 5 — E2E round 1 (Email + File) + Week 1 gate
- Un-skip `test_email_source.py` + `test_file_source.py` — implement success + rejection path each (≥4 tests).
- Regression: 199 Phase 1a E2E still PASS.
- **Week 1 exit:** 2 adapters, ≥40 unit tests, ≥4 un-skipped E2E tests, ruff clean.

---

## WEEK 2 — Folder + Batch + API adapters

### Day 6 — `FolderSourceAdapter` (E2.1)
- `src/aiflow/sources/folder_adapter.py` using `watchdog` observer.
- Debounce + mid-write detection via stable mtime sampling.
- Unit tests: ≥15 (file lock, permission error, partial write, debounce window).

### Day 7 — `BatchSourceAdapter` ZIP/tar (E2.2)
- `src/aiflow/sources/batch_adapter.py` — unpack to per-tenant tmp dir, max-size guardrail 500 MB (configurable).
- Zip-bomb protection via nested compression ratio check.
- Unit tests: ≥15 (mixed formats, max-size reject, corrupt archive, symlink escape).

### Day 8 — `ApiSourceAdapter` webhook (E2.3-A)
- `src/aiflow/sources/api_adapter.py` — adapter core + HMAC signature verify.
- Unit tests: ≥10 (sig valid, sig mismatch, replay window, clock skew tolerance).

### Day 9 — Webhook FastAPI router (E2.3-B)
- `src/aiflow/api/v1/sources.py` — `POST /api/v1/sources/webhook` returns `{intake_package_id}`.
- OpenAPI schema regen + contract test.
- Unit tests: ≥8 (auth, idempotency key, malformed payload).

### Day 10 — E2E round 2 (Folder + Batch + API) + Week 2 gate
- Un-skip `test_folder_source.py` + `test_batch_source.py` + `test_api_source.py` — ≥6 tests each adapter (success + rejection + edge).
- **Week 2 exit:** 5 total adapters conforming to `SourceAdapter` ABC (contract test parametrized over all 5), OpenAPI diff reviewed.

---

## WEEK 3 — N4 Association + upload-package + acceptance

### Day 11 — N4 Associator core (E3.1-A)
- `src/aiflow/intake/associator.py` — modes `explicit`, `filename_match`, `order`, `single_description` per `101_*` N4.
- Alembic `035_association_mode.py` — `intake_packages.association_mode` enum column.
- Unit tests: ≥20 (one per mode × success/failure, plus precedence rules).

### Day 12 — N4 wired into adapters (E3.1-B)
- `BatchSourceAdapter` + upload-package endpoint honour `association_mode` input.
- Integration tests via `test_multi_source_e2e.py` (still skipped stubs for now).

### Day 13 — `POST /api/v1/intake/upload-package` (E3.2)
- `src/aiflow/api/v1/intake.py` (extend) — multipart: N files + M descriptions + mode.
- Returns 201 with full `IntakePackage` summary (mask signed URLs).
- Contract test + OpenAPI.

### Day 14 — Multi-source E2E acceptance (E3.3) — DONE 2026-05-05 (S69)
- `test_multi_source_e2e.py` un-skipped and implemented: 5-adapter matrix (parametrized `source_type`) + 4 N4 association modes + Phase 1a regression gate.
- End-to-end per adapter: `adapter.enqueue/fetch_next` → storage spill + sha256 → `PolicyEngine.get_for_tenant()` → `IntakeRepository.insert_package` + `get_package` round-trip. **5 parametrize cases PASS**.
- N4 modes: ORDER / FILENAME_MATCH / SINGLE_DESCRIPTION via `POST /api/v1/intake/upload-package`, EXPLICIT via direct adapter + associator path (HTTP multipart cannot carry server-generated file_ids). **All 4 modes PASS round-trip**.
- Backward-compat regression: subprocess-spawned pytest run of `tests/e2e/v1_4_0_phase_1a/` asserts exit=0 + summary `199 passed`. **PASS**.
- Phase 1b E2E total: 27 → **34 PASS** (1 pre-existing `test_alembic_034.py` still asserting head 034 deselected per STOP feltetel).
- Exit-gate summary: `out/week_3_exit_gate.md`.

### Day 15 — Acceptance gate + PR draft
- **Phase 1b acceptance checklist** (see `Exit Criteria` below) walked through and signed.
- `docs/phase_1b_acceptance_report.md` + `docs/phase_1b_pr_description.md` drafted.
- CLAUDE.md key numbers refreshed (adapters, endpoints, DB tables, migrations, E2E count).
- `/review` run → zero blockers.

---

## PHASE 1b ACCEPTANCE GATE CHECKLIST

Analog to Phase 1a gates 9.1-9.6. Each item MUST be checked before merge to `main`.

- [ ] **G1 — ABC contract:** All 5 adapters pass the parametrized `SourceAdapter` contract test suite.
- [ ] **G2 — Domain alignment:** Every adapter produces `IntakePackage` conforming to `100_b` contracts (tenant_id, package_id UUID, state machine entry).
- [ ] **G3 — Policy integration:** PolicyEngine selects parser/classifier for every new `source_type` path (tested per adapter).
- [ ] **G4 — N4 association:** All 4 modes implemented + tested (≥20 unit tests + E2E coverage).
- [ ] **G5 — API surface:** `POST /api/v1/intake/upload-package` + `POST /api/v1/sources/webhook` documented in `docs/api/openapi.yaml`.
- [ ] **G6 — Backward compat:** 114-test Phase 1a regression suite unchanged PASS, no legacy pipeline behavior drift.
- [ ] **G7 — DB migration safety:** Alembic 034 + 035 idempotent upgrade + downgrade verified, default `legacy` backfill.
- [ ] **G8 — Observability:** Every adapter emits `source.package_received` + `source.package_rejected` structlog events with tenant_id, source_type, package_id.
- [ ] **G9 — Test counts:** Unit ≥ +200 new tests, E2E ≥ +30 un-skipped tests, ruff 0 error.

---

## EXIT CRITERIA (gate to Phase 1c)

All of G1-G9 above PASS + PR approved + tag `v1.4.1-phase-1b` pushed.

---

## STOP FELTETELEK

- **HARD:** Phase 1a PR not merged / tag missing → revert to the 3-precondition block in session prompt.
- **HARD:** Outlook COM unavailable on dev host → downgrade E1.1 to IMAP-only, file ticket for v1.4.2 rather than block the sprint.
- **SOFT:** `SourceAdapter` ABC contract test parametrization >2x larger than budget → split into dedicated session (E2.4).
- **SOFT:** N4 association modes require schema changes beyond `association_mode` column → split E3.1 across Day 11-12-13 instead of compressing.

---

## REFERENCIAK

- `01_PLAN/101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` — N2, R1, N4 full spec.
- `01_PLAN/100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` — IntakePackage / IntakeFile / IntakeDescription.
- `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` Section 4 — Phase ordering.
- `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md` — Phase 1a reference patterns (ABC + registry + metadata).
- `src/aiflow/providers/interfaces.py` + `src/aiflow/providers/registry.py` — template for `SourceAdapter` ABC + registry.
- `docs/phase_1a_pr_description.md`, `docs/phase_1a_acceptance_report.md`, `docs/phase_1a_retro.md` — Phase 1a close-out.

---

## SESSION CHAINING

```
S55 / E0.1 (THIS) — kickoff + ABC + E2E skeleton + sprint plan
S56 / E0.2        — Week 1 Day 1: source registry + Alembic 034
S57 / E1.1        — Week 1 Day 2: EmailSourceAdapter IMAP
S58 / E1.2        — Week 1 Day 3: EmailSourceAdapter Outlook COM (or IMAP-only fallback)
...
S69 / E3.3 / Day 15 — Phase 1b acceptance gate + PR
```

At end of each session: `/session-close <id>` generates `session_prompts/NEXT.md` for the next Day N.

---

*Phase 1b session: S55 = E0.1 (Source Adapters kickoff — finalized plan).*
