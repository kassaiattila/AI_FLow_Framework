# AIFlow v2.0.0 Phase 1a — Foundation (IntakePackage + Policy + Providers)

> **Branch:** `feature/v2.0.0-phase-1a-foundation` → `main`
> **Tag on merge:** `v1.4.0-phase-1a`
> **Sprint:** D (sessions S44–S54, 10 sessions over 2026-04-10 → 2026-04-17, demo+PR 2026-04-18)
> **Scope:** Domain contracts, state machines, policy engine, provider abstraction, backward-compat shim. **No skill-facing API changes.**

---

## Summary

Phase 1a is the foundation layer for AIFlow v2. It introduces the IntakePackage domain model, a policy-driven execution engine, and a provider abstraction that lets parsers/classifiers/extractors/embedders be swapped per tenant — **all without breaking any existing pipeline or skill.**

- **3 new top-level modules** under `src/aiflow/`: `intake/`, `policy/`, `providers/`
- **2 new Alembic migrations** (additive-only): `032_intake_tables`, `033_policy_overrides`
- **1 backward-compat shim layer** (`DocumentExtractorService.extract()` + `pipeline/compatibility.py`) — legacy `extract(file)` callers keep working unchanged
- **199 new E2E tests** covering the full Phase 1a surface area + regression of legacy paths

---

## Deliverables (by session)

| Session | Commit   | Deliverable |
|---------|----------|-------------|
| D0.1    | `ed7b8ab`| IntakePackage domain contracts + state machines (7 states, transition validator) |
| D0.2    | `e5ae658`| Alembic `032_intake_tables` + `IntakeRepository` (asyncpg, atomic status transitions) |
| D0.3    | `ff622d9`| `PolicyEngine` + `config/profiles/profile_a.yaml`, `profile_b.yaml` |
| D0.4    | `c2678a5`| `ProviderRegistry` + 4 ABCs (Parser / Classifier / Extractor / Embedder) + contract tests |
| D0.5    | `d11eecd`| Alembic `033_policy_overrides` + PolicyEngine DB integration (tenant-level overrides) |
| D0.6    | `bf8680c`| `SkillInstanceConfig.policy_override` + triple-merge (profile→tenant→instance) |
| D0.7    | `fee3d56`| Backward-compat shim + pipeline auto-upgrade |
| D0.8    | `0baed5e`| Phase 1a E2E acceptance suite (85 tests) |
| D0.9    | `f2c0cfc`| Backward-compat regression suite (+114 tests → 199 total) |
| D0.10   | `8457eff`| Documentation refresh (CLAUDE.md, 01_PLAN/CLAUDE.md, 58_, 104_, FEATURES, OpenAPI) |
| D0.11   | *this PR*| Acceptance report, PR description, Phase 1b kickoff prompt, retro |

---

## Migration plan

### Forward path (production)

```bash
# From v1.3.0 (Sprint B baseline, migration 031)
alembic upgrade head    # applies 032_intake_tables, then 033_policy_overrides
```

Both migrations are **additive-only**: new tables only, no column drops, no data rewrites. Legacy code paths continue to operate unchanged.

### Rollback path

```bash
alembic downgrade 031   # drops policy_overrides (033) and intake_* (032), safe because nothing legacy references them
```

**Migration numbering note:** The plan (`106_*` Section 9.2) references numbers `030/031` for intake/policy. In implementation these became `032/033` because `030_add_generated_specs` and `031_add_verification_edits` were already merged during Sprint B. Semantics are identical.

### Staging rehearsal (operator responsibility)

1. `alembic upgrade head` on a staging DB populated with prod-shape data.
2. Smoke-test: run one representative pipeline per skill (document_extractor, aszf_rag, invoice_processor).
3. `alembic downgrade 031` and repeat smoke test to confirm rollback safety.
4. Sign off in the acceptance report (Section 9.2 item 4).

---

## Key-number delta (CLAUDE.md)

| Metric            | Before (v1.3.0) | After (v1.4.0 Phase 1a) | Δ    |
|-------------------|-----------------|-------------------------|------|
| DB tables         | 48              | **49**                  | +1 group (intake_* + policy_overrides) |
| Alembic migrations| 31              | **33**                  | +2   |
| Unit tests        | 1443            | **1674**                | +231 |
| E2E tests         | 169             | **368**                 | +199 (8 new Phase 1a files) |
| Top-level modules | — (existing)    | +3 (`intake/`, `policy/`, `providers/`) | — |
| Pipeline adapters | 22              | 22                      | 0 (shim only) |
| Services          | 27              | 27                      | 0 (additive) |
| Skills            | 7               | 7                       | 0 |

---

## Acceptance matrix (106_ Section 9)

See `docs/phase_1a_acceptance_report.md` for the full item-by-item walkthrough.

| Section | PASS | PARTIAL | N/A / DEFERRED | PENDING | FAIL |
|---------|------|---------|----------------|---------|------|
| 9.1 Implementation | 13 | 1 | 0 | 0 | 0 |
| 9.2 Database       | 3  | 0 | 1 | 0 | 0 |
| 9.3 Tests          | 6  | 0 | 1 | 0 | 0 |
| 9.4 Quality        | 2  | 0 | 2 | 0 | 0 |
| 9.5 Docs           | 5  | 0 | 0 | 0 | 0 |
| 9.6 Business       | 1  | 0 | 0 | 2 | 0 |
| **TOTAL**          | **30** | **1** | **4** | **2** | **0** |

**Verdict:** Technical gates (9.1–9.5) are met. Business gates (9.6 — customer notification, architect sign-off) execute after PR approval.

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Legacy pipeline regression via shim | Low | High | 114 regression tests in `test_extract_shim_regression.py` + `test_legacy_pipeline_regression.py` all PASS |
| `SkillInstance.policy_override` merge semantics surprise users | Medium | Medium | Triple-merge (profile→tenant→instance) documented in 100_b_* Section 1; 6 dedicated E2E tests including partial-override + multi-instance isolation |
| Alembic 033 `policy_overrides` clashes with manual edits | Low | Medium | Table is new, no existing data is touched. Rollback is a clean `DROP TABLE`. |
| Backward-compat shim drifts from v2 canonical path | Medium | Medium | Phase 1b includes explicit deprecation timeline; shim tests will continue to run on every PR |
| Async event-loop issues with new `IntakeRepository` | Low | Medium | Uses shared `aiflow.api.deps.get_pool()` (per `feedback_asyncpg_pool_event_loop` memory), 103 unit tests + E2E lifecycle tests pass |

---

## Rollback plan

- **During deploy, migration fails:** `alembic downgrade 031`, investigate on local clone, re-issue. No user data lost (tables are empty on first upgrade).
- **Shim regression discovered post-deploy:** forward-fix in `src/aiflow/services/document_extractor/` + `src/aiflow/pipeline/compatibility.py`, patch release as `v1.4.0.1`. Downgrade is not required — shim is a runtime layer.
- **Nuclear option:** revert merge commit on `main`, re-branch from last green tag. Detailed in `100_d_*` Section 12.

---

## Test plan (reviewer checklist)

- [ ] `pytest tests/unit/ -x -q` → 1674 passed
- [ ] `pytest tests/e2e/v1_4_0_phase_1a/ -q` → 199 passed
- [ ] `ruff check src/ tests/` → All checks passed
- [ ] `alembic upgrade head` on fresh DB, followed by `alembic downgrade 031`, followed by `alembic upgrade head` again — all three succeed without error
- [ ] Run one legacy `extract(file)` call on a representative skill (e.g. via the admin UI Document page) and confirm it completes through the shim
- [ ] Review `docs/phase_1a_acceptance_report.md` and sign off on Section 9.6 (architect + lead engineer)

---

## References

- **Implementation guide:** `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md`
- **Master index:** `01_PLAN/104_AIFLOW_v2_FINAL_MASTER_INDEX.md` Section 8.1
- **Migration playbook:** `01_PLAN/100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` Section 2 + 12
- **Contract schemas:** `01_PLAN/100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md`
- **State machines:** `01_PLAN/100_c_AIFLOW_v2_STATE_MACHINES.md`
- **Component transformation (N2/R1/N4):** `01_PLAN/101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md`
- **Acceptance report (this PR):** `docs/phase_1a_acceptance_report.md`
- **Next sprint prompt (Phase 1b):** `01_PLAN/session_S55_v1_4_1_phase_1b_sources_kickoff.md`

---

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
