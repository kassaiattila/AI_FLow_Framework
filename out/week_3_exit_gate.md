# Phase 1b Week 3 Exit Gate — E3.3 Acceptance Report

**Session:** S69 / E3.3 (Week 3 Day 14)
**Date:** 2026-05-05
**Branch:** `feature/v1.4.1-phase-1b-sources`
**Scope:** multi-source E2E acceptance + Phase 1a backward-compat regression gate

## Acceptance criteria

| # | Gate | Status |
|---|------|--------|
| 1 | 5 adapter coexist (email / file_upload / folder_import / batch_import / api_push) produce unified `IntakePackage` | PASS |
| 2 | Each adapter product survives `IntakeRepository.insert_package` + `get_package` round-trip | PASS |
| 3 | `PolicyEngine.get_for_tenant(tenant_id)` resolves for all 5 source types under `profile_a` | PASS |
| 4 | N4 association modes (EXPLICIT / FILENAME_MATCH / ORDER / SINGLE_DESCRIPTION) round-trip end-to-end | PASS |
| 5 | Phase 1a E2E regression stays at 199/199 PASS | PASS |

## New tests

File: `tests/e2e/v1_4_1_phase_1b/test_multi_source_e2e.py`

| Test | Cases | Notes |
|------|-------|-------|
| `test_all_sources_produce_valid_intake_package` | 5 (parametrized) | adapter → storage spill → sha256 match → `PolicyEngine` → DB round-trip per case (own asyncpg pool per `asyncio.run`) |
| `test_n4_association_modes_roundtrip` | 4 modes inline | ORDER/FILENAME_MATCH/SINGLE_DESCRIPTION via `POST /api/v1/intake/upload-package`; EXPLICIT via direct adapter path (HTTP multipart cannot bind server-generated file_ids) |
| `test_phase_1a_regression_unchanged` | 1 | Subprocess-spawned pytest run of `tests/e2e/v1_4_0_phase_1a/`, asserts exit=0 + summary line reports 199 passed |

## Validation commands

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/                                          # 0 errors
.venv/Scripts/python.exe -m pytest tests/unit/ -q                                           # 1872 PASS
.venv/Scripts/python.exe -m pytest tests/integration/ -q                                    # 38 PASS
.venv/Scripts/python.exe -m pytest tests/e2e/v1_4_0_phase_1a/ -q                            # 199 PASS
.venv/Scripts/python.exe -m pytest tests/e2e/v1_4_1_phase_1b/ -q \
    --deselect tests/e2e/v1_4_1_phase_1b/test_alembic_034.py                                # 34 PASS, 1 deselected
```

Combined `tests/unit + tests/integration` shows 1 pre-existing failure
(`test_from_env_production_requires_keys`) caused by env-var leakage between
suites; reproduces on the pre-E3.3 baseline and is unrelated to Phase 1b work.

## Known carry-over (not in scope for E3.3)

* `tests/e2e/v1_4_1_phase_1b/test_alembic_034.py` still asserts head == "034"
  but live Alembic head is "035" (shipped by S66). Tracking as a standalone
  ticket per S69 prompt STOP FELTETEL.

## Deltas vs E3.2

* +7 Phase 1b E2E tests (5 matrix + 1 N4 + 1 regression gate).
* Phase 1b E2E total: 27 → 34 (34 passing, 1 deselected pre-existing failure).
