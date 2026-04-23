# v1.4.8 Sprint L — Monitoring + Cost Enforcement

**Branch:** `feature/v1.4.8-monitoring-cost` → `main`
**Tag queued:** `v1.4.8`
**Sessions delivered:** S111 + S112 + S113

## Scope delivered

### S111 — Langfuse trace drill-down + span-metrics (commit `0351e6f`)
- `GET /api/v1/runs/{id}/trace` — Langfuse drill-down endpoint (trace tree + span timeline).
- `GET /api/v1/monitoring/span-metrics` — 24h aggregated span latency/cost metrics.
- `TraceTree` UI component on `/runs/:id`; `/monitoring` page renders span-metrics block.
- 5 new integration tests (`tests/integration/api/test_runs_trace.py`).
- 3 new Playwright E2E (`tests/e2e/test_uc_monitoring_golden_path.py`).

### S112 — PolicyEngine.cost_cap + Costs cap banner (commit `58251de`)
- `PolicyEngine.cost_cap` enforcement — raises `CostCapBreached` (HTTP 429) when tenant monthly spend exceeds configured cap.
- New contract: `contracts/cost_attribution.py` — `CostAttribution` + `CapStatus` Pydantic models.
- New endpoint: `GET /api/v1/costs/cap-status` — returns `ok | warning | critical | exceeded` level + utilization %.
- New repository method: `state/cost_repository.py::aggregate_tenant_cost()` — tenant-isolated monthly rollup.
- Alembic 043 — `cost_records.tenant_id` column + `idx_cost_records_tenant_recorded` composite index.
- `aiflow-admin/src/pages-new/Costs.tsx` — 4-level alert banner (ok/warning/critical/exceeded).
- 3 new integration tests (`tests/integration/test_cost_cap_enforcement.py`).

### S113 — Cross-UC CI profile + regression matrix (this session)
- New suite `ci-cross-uc` in `tests/test_suites.yaml` — 4 UC smoke (Invoice + RAG + Email + Monitoring/Costs) with `<10 min` budget.
- `tests/regression_matrix.yaml` maps Sprint L change paths (`src/aiflow/policy/**`, `src/aiflow/state/cost_repository.py`, `src/aiflow/contracts/cost_attribution.py`, `alembic/versions/043_*`) → `ci-cross-uc` suite.
- Measured wall-clock: 42 tests in 18.65s on local dev hardware (well under the 600s budget).

## Acceptance

| Gate | Result |
|---|---|
| `1995 unit` | PASS (no regressions from Sprint L) |
| `ci-cross-uc` profile | 42 passed in ~19s (<<10 min target) |
| `test_cost_cap_enforcement` | 3/3 PASS |
| `test_runs_trace` | 5/5 PASS |
| `test_ingest_uc2` | 3/3 PASS |
| `test_scan_and_classify` + `test_intent_routing` | 6/6 PASS |
| `ruff check src/ tests/ --quiet` | GREEN |
| `ruff format --check` | GREEN |
| `alembic current` | 043 (head) |

## Breaking changes

**NONE** — Sprint L is additive only:

- New column `cost_records.tenant_id` is `NULLABLE` — pre-existing rows remain readable.
- New endpoints (`/runs/{id}/trace`, `/monitoring/span-metrics`, `/costs/cap-status`) do not alter existing routes.
- `CostAttribution` is a new contract; no existing Pydantic model was modified.

## Migration path

```bash
alembic upgrade head      # 042 → 043 (tenant_id column + composite index)
```

No data backfill required. Cost cap is opt-in per tenant via `tenant_policy.monthly_cost_cap_usd`; NULL = no cap (legacy behaviour preserved).

## Key numbers (post Sprint L)

- 27 services | 189 API endpoints | 50 DB tables | **43 Alembic migrations (head: 043)**
- 1995 unit | 75+ integration (incl. Sprint L: 5 trace + 3 cost_cap) | 420 E2E
- 8 skills | 24+ UI pages (Costs cap banner + TraceTree + span-metrics)

## Follow-ups (out of scope)

- Cost cap live alerting (email/Slack hook on `exceeded`) — queued for Sprint M.
- Langfuse SDK upgrade 3.x (current: 2.x shim) — tracked separately.
- `query()` refactor to provider registry (1024-dim queryability) — Sprint M UC2-2.
- Coverage uplift 65.67% → 80% trajectory — tracked in issue #7.
