# v1.4.2 Phase 1c — Association Backfill + Observability Harden + CI Hygiene

Closes the Phase 1b architect "GO WITH CONDITIONS" list (C1-C5) and issues #3, #5.

## Scope (5 incremental sessions)

| Session | Commit | Work |
|---------|--------|------|
| F0.2 | `6191748` | **CI hygiene** — pin `python-multipart>=0.0.9`, triage kernel mypy errors (closes #5) |
| F0.3 | `193d717` | **OpenAPI regen + drift CI gate** — regen `docs/api/openapi.{yaml,json}` for `upload-package` + `sources/webhook`; add drift job to `ci-framework.yml` (closes #3, architect C3) |
| F0.4 | `053d3fb` | **Canonical observability events** — all 5 source adapters (email/file/folder/batch/api) emit `source.package_received` + `source.package_rejected` with `package_id`+`tenant_id`+`source_type` via `emit_package_event` (architect C4) |
| F0.5 | `be0f1bb` | **Alembic 036 backfill** — chunked + advisory-locked data-only migration backfills historical `intake_packages.association_mode`. Heuristic: `0 desc → NULL`, `1 desc → single_description`, `N/N → order`, `N/M → NULL + WARN`. Dev DB: 2 `order` + 4 `single_description`, 0 ambiguous (architect C5a) |
| F0.6 | *(this PR)* | **Alembic 037 CHECK trigger** — AFTER INSERT OR UPDATE on `intake_descriptions`: reject row if parent `intake_packages.association_mode IS NULL`. Negative integration test. Phase 1c acceptance report (architect C5b) |

## Design — 037 CHECK trigger

PostgreSQL row-level `CHECK` cannot reference a second table, so the invariant

> a description may not exist under a parent package with `association_mode IS NULL`

is enforced by an `AFTER INSERT OR UPDATE OF package_id` trigger on `intake_descriptions` that looks up the parent mode and raises with `ERRCODE = check_violation` (→ client-side `asyncpg.exceptions.CheckViolationError`). The trigger catches both:

* INSERT of a new description under a NULL-mode parent, and
* UPDATE re-parenting a description to a NULL-mode parent.

The symmetric direction (writer UPDATE-ing `intake_packages.association_mode` back to NULL while descriptions exist) is **not** guarded because no current writer exercises that path — `src/aiflow/state/repositories/intake.py` only `UPDATE`s `status`. A mirror trigger can be added later if the surface grows.

## Writer audit

| Path | `association_mode` handling |
|------|-----------------------------|
| `api/v1/intake.py:465` (POST /upload-package) | set from user form or `_infer_mode` when descriptions present; `None` only when empty |
| `state/repositories/intake.py:38` `insert_package` | atomic tx — package INSERTed before descriptions, mode already set |
| `state/repositories/intake.py:241` `transition_status` | does not touch `association_mode` |
| `sources/*_adapter.py` | in-memory only today; no DB insert caller. Trigger protects future orchestration wiring |

## Phase 1c gates

| Gate | Status |
|------|--------|
| G1 — CI hygiene | **PASS** |
| G2 — OpenAPI regen | **PASS** |
| G3 — OpenAPI drift gate | **PASS** |
| G4 — Canonical events (5 adapters) | **PASS** |
| G5 — No PII leak | **PASS** |
| G6 — Backfill correctness (036) | **PASS** |
| G7 — CHECK trigger (037) + negative test | **PASS** |
| G8 — 199 Phase 1a + 35 Phase 1b E2E compat | **PASS** (collect-only local; full run in CI) |
| G9 — Test counts / ruff 0 | **PASS** (+15 unit, +4 integration, 403 E2E unchanged) |

See `docs/phase_1c_acceptance_report.md` for full evidence table.

## Test summary

* ruff: 0 error, 511 files formatted
* mypy scoped modules: 0 issue in 23 files
* unit: **1886 PASS** (24.25 s)
* integration/alembic: **4 PASS** (4.07 s)
* e2e collect-only: **403 tests** (5.62 s)
* alembic round-trip `upgrade head → downgrade -1 → upgrade head`: all PASS

## Migrations (v1.4.2)

| Revision | Purpose | Reversible? | Data change? |
|----------|---------|-------------|--------------|
| `035` | (v1.4.1) add `intake_packages.association_mode` enum column | yes | no |
| `036` | Backfill `association_mode` via heuristic | downgrade = no-op | **yes** |
| `037` | AFTER INSERT/UPDATE trigger on `intake_descriptions` requiring parent mode | yes (drop trigger + function) | no |

Zero-downtime per `aiflow-database` rules; advisory-locked; chunked; idempotent on re-upgrade.

## Out of scope

* Adapter → `insert_package()` orchestration wiring — Phase 1d+
* `GENERATED ALWAYS AS` materialized `has_descriptions` boolean (rejected — cross-table aggregates disallowed)
* Mirror trigger on `intake_packages.association_mode` UPDATE — deferred until a writer actually needs it

## Post-merge

* Tag `v1.4.2-phase-1c`
* Close architect C5 (both parts) and issues #3, #5
* Update `CLAUDE.md` key numbers (Alembic 35 → 37)
