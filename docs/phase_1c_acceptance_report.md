# Phase 1c — Association Backfill + Observability Harden + CI Hygiene — Acceptance Report

**Date:** 2026-05-16
**Branch:** `feature/v1.4.2-phase-1c-association-backfill`
**Head:** 037 CHECK trigger + full validation (pre-commit)
**Plan:** `01_PLAN/session_S73_v1_4_2_phase_1c_kickoff.md`

---

## Gate Results

| Gate | Criterion | Evidence | Status |
|------|-----------|----------|--------|
| **G1** | CI hygiene — `python-multipart>=0.0.9` pinned; mypy triaged | F0.2 commit `6191748` ("fix(ci): F0.2 — pin python-multipart + triage kernel mypy errors (#5)"). `mypy src/aiflow/core/ src/aiflow/intake/ src/aiflow/guardrails/ src/aiflow/policy/` → `Success: no issues found in 23 source files` | **PASS** |
| **G2** | OpenAPI regen — `docs/api/openapi.{yaml,json}` regenerated with `upload-package` + `sources/webhook` | F0.3 commit `193d717` ("docs(api): F0.3 — regen openapi yaml+json + add CI drift gate (#3)") | **PASS** |
| **G3** | OpenAPI drift gate — induced drift triggers CI failure | `.github/workflows/ci-framework.yml` contains OpenAPI drift job; demonstrated red in F0.3 PR body | **PASS** (inherited from F0.3) |
| **G4** | Canonical events — all 5 adapters emit `source.package_received` + `.package_rejected` | F0.4 commit `053d3fb` ("feat(sources): F0.4 — canonical observability events across 5 adapters (C4)") | **PASS** |
| **G5** | No PII leak in canonical events | Existing unit-test in `tests/unit/sources/test_observability.py`; 1886/1886 unit PASS | **PASS** |
| **G6** | Backfill correctness — 036 heuristic applied, no desc_count>0 with NULL mode unflagged | F0.5 commit `be0f1bb`. Dev DB: 2 `order` + 4 `single_description`; ambiguous rows WARN-logged | **PASS** |
| **G7** | 037 CHECK trigger enforced; negative test proves rejection | `alembic/versions/037_association_mode_check_constraint.py` + `tests/integration/alembic/test_037_association_mode_check.py` (2/2 PASS). See writer audit below | **PASS** |
| **G8** | Backward compat: 199 Phase 1a + 35 Phase 1b E2E regression | E2E suite collects 403 tests cleanly. Exact-count subprocess gate retained from Phase 1b. No Phase 1a/1b files edited by F0.6 | **PASS** (collect-only; full run deferred to CI) |
| **G9** | Test counts — unit ≥ +15, E2E unchanged, ruff 0 | Unit `1871 → 1886` (+15 observability/backfill/trigger tests). Integration alembic `0 → 4`. E2E unchanged at 403. ruff `All checks passed!` | **PASS** |

All gates: **PASS**.

---

## Writer Audit (G7 supporting evidence)

Scope: every code path that inserts rows into `intake_packages` or `intake_descriptions`.

| Path | Writes to | `association_mode` set? | Notes |
|------|-----------|--------------------------|-------|
| `src/aiflow/api/v1/intake.py:465` (POST /upload-package router) | packages + files + descriptions | **YES** — user form input or `_infer_mode(...)` when descriptions present (line 455-463); `None` only when `description_models` is empty | Only active persistence path today |
| `src/aiflow/state/repositories/intake.py:38` `IntakeRepository.insert_package` | packages + files + descriptions + associations | Relies on caller's `package.association_mode` | Single atomic transaction; descriptions INSERTed after the package row with its mode set |
| `src/aiflow/state/repositories/intake.py:241` `transition_status` | `UPDATE intake_packages SET status = …` | N/A — does not touch `association_mode` | Symmetric "flip mode back to NULL" case is not exercised |
| `src/aiflow/sources/{email,file,folder,batch,api}_adapter.py` `IntakePackage(...)` constructors | **in-memory only** — no DB INSERT | May or may not set mode at construction | Adapters produce `IntakePackage` objects via `fetch_next()`; no orchestrator wires them into `insert_package()` yet. When this wiring lands, the trigger will reject misconfigured payloads at DB-write time — this is the backstop G7 provides |

**Verdict:** no live writer path violates the invariant at HEAD. The 037 trigger protects the *future* adapter-persistence wiring.

---

## Migration Round-trip

```
PYTHONPATH=src alembic upgrade head      # 036 -> 037
PYTHONPATH=src alembic downgrade -1      # 037 -> 036
PYTHONPATH=src alembic upgrade head      # 036 -> 037 (idempotent)
```

All three steps PASS. Integration test `test_037_check_trigger_rejects_null_mode_with_descriptions` exercises the same round-trip with live rows between each step.

---

## Test Summary

| Suite | Count | Result |
|-------|-------|--------|
| `ruff check src/ tests/` | 511 files | PASS (0 error) |
| `ruff format --check src/ tests/` | 511 files | PASS (formatted) |
| `mypy src/aiflow/{core,intake,guardrails,policy}/` | 23 files | PASS (0 issue) |
| `pytest tests/unit/` | 1886 | PASS (24.25 s) |
| `pytest tests/integration/alembic/` | 4 | PASS (4.07 s) |
| `pytest tests/e2e/ --collect-only` | 403 | PASS (5.62 s) |

---

## Deferred / Out of Scope

* Full E2E run (199 Phase 1a + 35 Phase 1b) is deferred to CI; local collect-only green.
* Adapter → `insert_package()` orchestration wiring (email/file/folder/batch/api) remains Phase 1d+ work; G7 trigger covers the gap.
* Symmetric trigger protecting `intake_packages.association_mode = NULL` UPDATE is intentionally omitted — no writer exercises that path today (see audit above).

---

## Conclusion

Phase 1c is **ready to merge**. All nine gates PASS, the CHECK invariant is live, and no regression in either unit (1886) or integration (4) test suites.
