# AIFlow v1.4.1 Phase 1b — Source Adapters

> **Branch:** `feature/v1.4.1-phase-1b-sources` → `main`
> **Tag on merge:** `v1.4.1-phase-1b`
> **Sprint:** E (sessions S55–S70, 15 working days, 2026-04-21 → 2026-05-06)
> **Scope:** 5 source adapters (Email, File, Folder, Batch, API), N4 file↔description associator, `POST /api/v1/intake/upload-package` multipart endpoint.

---

## Summary

Phase 1b layers the ingestion surface on top of the Phase 1a `IntakePackage` foundation. Every new source — email inbox, file upload, watched folder, ZIP/tar batch, webhook push — now produces a canonical `IntakePackage` routed through the Phase 1a policy + provider chain, with no changes to skill-facing code.

- **5 source adapters** implementing the `SourceAdapter` ABC, registered via `SourceAdapterRegistry`.
- **N4 association** (file ↔ description matching) with 4 modes: `explicit`, `filename_match`, `order`, `single_description`.
- **1 new public endpoint:** `POST /api/v1/intake/upload-package` (multipart) + webhook `POST /api/v1/sources/webhook`.
- **2 new Alembic migrations** (additive-only): `034_source_type`, `035_association_mode`.
- **+198 unit tests, +35 Phase 1b E2E tests, +11 integration tests** — 199 Phase 1a E2E tests frozen and regressed on every run.
- **Backward compat:** no skill API, no pipeline adapter, no policy engine behaviour changed. Phase 1a regression gate runs inside Phase 1b E2E suite.

---

## Deliverables (by session)

| Session | Commit   | Deliverable |
|---------|----------|-------------|
| S55 / E0.1     | (kickoff)  | `SourceAdapter` ABC + `SourceAdapterMetadata` descriptor + 7-file E2E skeleton (all skipped) |
| S56 / E0.2     |            | Source registry (`SourceAdapterRegistry`) + Alembic `034_source_type` + per-test fixtures |
| S57 / E1.1-A   |            | `EmailSourceAdapter` IMAP backend — MIME parse, attachment spill, auth + size guards |
| S58 / E1.1-B   |            | `EmailSourceAdapter` Outlook COM backend (opt-in, env `AIFLOW_EMAIL_BACKEND`); IMAP stays default |
| Week 1 Day 4   |            | `FileSourceAdapter` single-file entry + MIME detection + Week 1 E2E gate |
| S61 / E2.1     |            | `FolderSourceAdapter` (`watchdog`), debounce + mid-write detection |
| S62 / E2.2     |            | `BatchSourceAdapter` ZIP/tar unpack + zip-bomb + symlink-escape guards |
| S63 / E2.3-A   |            | `ApiSourceAdapter` webhook adapter + HMAC signature verify + replay window |
| S64 / E2.3-B   |            | `POST /api/v1/sources/webhook` router + idempotency key handling |
| S65 / E2.4     | `f2647f8`  | Week 2 exit gate: 5-adapter parametrized ABC contract + OpenAPI baseline |
| S66 / E3.1-A   | `5aa53fc`  | `aiflow.intake.associator` core + Alembic `035_association_mode` + 27 unit tests |
| S67 / E3.1-B   | `3b1c35c`  | `BatchSourceAdapter` wiring + `association_mode` round-trip through `IntakeRepository` |
| S68 / E3.2     | `e5ae658`  | `POST /api/v1/intake/upload-package` multipart router + 11 integration + 2 E2E |
| S69 / E3.3     | `fcb1c29`  | Multi-source E2E acceptance (5-adapter matrix + 4 N4 modes) + Phase 1a subprocess regression gate |
| S70 / E3.4     | *this PR*  | `test_alembic_034.py` resync (head 035), acceptance report, PR description, CLAUDE.md refresh |

---

## Migration plan

### Forward path (production)

```bash
# From v1.4.0 Phase 1a (head 033)
alembic upgrade head    # applies 034_source_type, then 035_association_mode
```

Both migrations are **additive-only**:

- `034_source_type` backfills `intake_packages.source_type` with `'legacy'` for any pre-Phase-1b rows, then sets NOT NULL and adds the `ck_intake_source_type` CHECK constraint (whitelist: `email`, `file_upload`, `folder_import`, `batch_import`, `api_push`, `legacy`).
- `035_association_mode` creates the `association_mode_enum` type and adds a **nullable** `association_mode` column. Existing rows stay NULL; a future migration will backfill + set NOT NULL once every adapter path populates it.

### Rollback path

```bash
alembic downgrade 033   # drops association_mode column/type (035), then lifts CHECK + NOT NULL (034)
```

Round-trip is covered by `tests/e2e/v1_4_1_phase_1b/test_alembic_034.py::test_migration_034_source_type_hardening`, which verifies that the 034 contract survives `head → downgrade -1 → upgrade head`.

### Staging rehearsal (operator responsibility)

1. `alembic upgrade head` on a staging DB populated with prod-shape data.
2. POST a representative payload to `POST /api/v1/intake/upload-package` and to `POST /api/v1/sources/webhook`; verify an `IntakePackage` row appears.
3. `alembic downgrade 033` and confirm legacy `extract(file)` code path still works through the Phase 1a shim.
4. `alembic upgrade head` again, sign off in the acceptance report.

---

## Breaking changes

**None.** Phase 1b is strictly additive: no skill API change, no pipeline adapter behaviour change, no policy engine change. The Phase 1a backward-compat shim (`src/aiflow/pipeline/compatibility.py`) is untouched, and the 114-test backward-compat suite (plus the broader 199 Phase 1a E2E suite) regresses on every PR and on every CI build.

---

## Key-number delta (CLAUDE.md)

| Metric | Before (v1.4.0 Phase 1a) | After (v1.4.1 Phase 1b) | Δ |
|--------|--------------------------|--------------------------|---|
| Source adapters | 0 | **5** | +5 (`Email`, `File`, `Folder`, `Batch`, `API`) |
| DB tables | 49 | 49 | 0 (additive columns only) |
| Alembic migrations | 33 | **35** | +2 |
| API endpoints | 175 | **176** | +1 net (`upload-package` added; webhook existed as stub) |
| Unit tests | 1674 | **1872** | +198 |
| Integration tests | 27 | **38** | +11 |
| E2E Phase 1a | 199 | 199 | 0 (frozen) |
| E2E Phase 1b | — | **35** | +35 |
| Services | 27 | 27 | 0 |
| Skills | 7 | 7 | 0 |

---

## Acceptance matrix (S55 plan, gates G1-G9)

Full walkthrough: `out/phase_1b_acceptance_report.md`.

| Gate | Title | Status |
|------|-------|--------|
| G1 | ABC contract across 5 adapters | PASS |
| G2 | Domain alignment (IntakePackage) | PASS |
| G3 | Policy integration | PASS |
| G4 | N4 association modes | PASS |
| G5 | API surface in static `openapi.yaml` | WAIVED (regen ticket) |
| G6 | Backward compat (Phase 1a 199 E2E) | PASS |
| G7 | DB migration safety | PASS |
| G8 | Observability canonical events | PARTIAL (rename ticket) |
| G9 | Test counts | PASS |

**Verdict:** technical gates (G1–G4, G6, G7, G9) all PASS. G5 and G8 drift from spec are scoped to follow-up tickets per S70 STOP feltételek; neither affects runtime correctness or security.

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Folder adapter misses mid-write / partial files | Medium | Medium | `FolderSourceAdapter` stable-mtime sampling + debounce window (unit tests assert partial-write detection) |
| Batch adapter zip-bomb / symlink escape | Low | High | Nested compression ratio guard + symlink rejection in `tests/unit/sources/test_batch_adapter.py` |
| Webhook replay/replay-window skew | Medium | Medium | HMAC signature + replay window + idempotency key; unit tests cover sig mismatch, clock skew, idempotent retry |
| `association_mode` column NULL for legacy rows | Low | Low | Column intentionally nullable in 035; backfill migration filed as Phase 1c task |
| Static `docs/api/openapi.yaml` drifts from live schema | High | Low | Flagged as G5 follow-up; runtime `/openapi.json` is the authoritative contract and is exercised by integration + E2E tests |
| Structlog event naming not canonical | High | Low | Events are emitted (G8 PARTIAL); follow-up session standardizes names + adds `tenant_id`/`source_type` keys |

---

## Rollback plan

- **Migration fails during deploy:** `alembic downgrade 033`; no data lost (new tables/columns are empty on first upgrade).
- **Adapter regression post-deploy:** forward-fix in `src/aiflow/sources/*`, patch release `v1.4.1.1`. Rolling back the migrations is not required — the shim, skill code, and legacy pipeline paths are untouched.
- **Nuclear option:** revert merge commit on `main`, re-branch from `v1.4.0-phase-1a`. Detailed in `01_PLAN/100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` §12.

---

## Test plan (reviewer checklist)

- [ ] `pytest tests/unit/ -q` → **1872 passed**
- [ ] `pytest tests/integration/ -q` → **38 passed**
- [ ] `pytest tests/e2e/v1_4_1_phase_1b/ -q` → **35 passed**
- [ ] `pytest tests/e2e/v1_4_0_phase_1a/ -q` → **199 passed** (Phase 1a regression)
- [ ] `ruff check src/ tests/` → All checks passed
- [ ] On a fresh DB: `alembic upgrade head` → `alembic downgrade 033` → `alembic upgrade head` — all three succeed, `intake_packages.association_mode` survives round-trip
- [ ] Manually POST a payload to `POST /api/v1/intake/upload-package` (admin UI or curl) and verify an `IntakePackage` row with the requested `association_mode` is persisted
- [ ] Review `out/phase_1b_acceptance_report.md` and confirm G5/G8 follow-up tickets are filed before merge

---

## References

- **Sprint plan:** `01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md`
- **Acceptance report (this PR):** `out/phase_1b_acceptance_report.md`
- **Week 3 exit-gate report (S69):** `out/week_3_exit_gate.md`
- **Component transformation (N2/R1/N4):** `01_PLAN/101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md`
- **Domain contracts:** `01_PLAN/100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md`
- **Phase 1a close:** `docs/phase_1a_pr_description.md`, `docs/phase_1a_acceptance_report.md`
- **Master index:** `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` §4

---

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
