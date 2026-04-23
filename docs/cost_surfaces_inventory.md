# AIFlow Cost-Surface Inventory — Sprint N S120

> **Generated:** 2026-04-26 during S120 kickoff on `feature/v1.4.10-cost-guardrail-budget`.
> **Purpose:** Catalog every place in `src/aiflow/` that records, aggregates, or checks cost,
> classified as **Recorder**, **Cap-check (reactive)**, or **Pre-flight gap (NEW for Sprint N)**.
> **Source of truth:** `src/aiflow/` as of HEAD of Sprint M tip (`d3e2d4a`).

---

## 1. Summary

| Category                      | Count | Notes                                                                 |
|-------------------------------|-------|-----------------------------------------------------------------------|
| **Recorder call sites**       | 5     | All funnel through `aiflow.api.cost_recorder.record_cost`.            |
| **Cap-check (reactive)**      | 2     | `PolicyEngine.enforce_cost_cap` + `/api/v1/costs/cap-status`.         |
| **Aggregation / query**       | 4     | `CostAttributionRepository`, `/costs/*` endpoints, 2 SQL views.       |
| **Config surfaces**           | 2     | `PolicyConfig.cost_cap_usd` + `teams.budget_monthly_usd` column.      |
| **Pre-flight guardrail (GAP)**| 0     | **Nothing checks budget before work starts.** Sprint N target.        |

---

## 2. Recorders — where cost is written

All five call sites route through `aiflow.api.cost_recorder.record_cost()`
(`src/aiflow/api/cost_recorder.py:14`), which inserts into `cost_records`
best-effort (logs + swallows exceptions).

| # | Site                                                   | Trigger                              | Tenant scope        |
|---|--------------------------------------------------------|--------------------------------------|---------------------|
| 1 | `src/aiflow/api/v1/rag_engine.py:564`                  | RAG engine retrieval cost            | via `team_id`       |
| 2 | `src/aiflow/api/v1/rag_engine.py:635`                  | RAG engine answer generation         | via `team_id`       |
| 3 | `src/aiflow/api/v1/process_docs.py:116, 309`           | Document processing pipeline         | via `team_id`       |
| 4 | `src/aiflow/api/v1/documents.py:460`                   | Document ingestion                   | via `team_id`       |
| 5 | `src/aiflow/pipeline/runner.py:382` (`_record_pipeline_cost`) | Generic pipeline step        | via `team_id`       |

**Shape of the row:** `{workflow_run_id (nullable since S112), step_name, model,
provider, input_tokens, output_tokens, cost_usd, team_id, tenant_id, recorded_at}`.
Note Sprint L S112 added `cost_records.tenant_id` (Alembic 043) and Sprint L S112b
made `workflow_run_id` nullable (Alembic 044).

**There is also `CostAttributionRepository.insert_attribution`
(`src/aiflow/state/cost_repository.py:30`)** — an alternate path for v2 contract
writes (`CostAttribution` → `cost_records`). Not hit by any `record_cost` consumer yet;
Sprint N should decide whether to consolidate.

**Secondary / in-memory:** `aiflow.observability.cost_tracker.CostTracker` is an
in-process tracker used in tests; not a production recorder. Skip for Sprint N
pre-flight design.

---

## 3. Cap-checks — reactive enforcement (Sprint L baseline)

| # | Site                                                | Semantics                                                           |
|---|-----------------------------------------------------|---------------------------------------------------------------------|
| 1 | `src/aiflow/policy/engine.py:149` `enforce_cost_cap` | Reads `PolicyConfig.cost_cap_usd`, aggregates over `cost_cap_window_h`, raises `CostCapBreached` when `current_usd >= cap_usd`. |
| 2 | `src/aiflow/services/rag_engine/service.py:559`      | Sole caller of `enforce_cost_cap` today (per-query reactive check).  |
| 3 | `src/aiflow/api/v1/costs.py:213` `cost_cap_status`   | Read-only utilisation endpoint (used by UI).                         |
| 4 | `src/aiflow/api/app.py:204` `cost_cap_breached_handler` | Maps `CostCapBreached` → HTTP 429.                                |

**Key limitation:** the check fires *after* the request has already committed to
running. There is no pre-flight path; no step refuses to start because the
projected cost would exceed the tenant's remaining budget.

**`PolicyConfig.cost_cap_usd` is tenant-aware** via `tenant_overrides`
(`src/aiflow/policy/engine.py:132` `get_for_tenant`), but the cap value itself
lives in config/tenant-override maps, not a DB table — it cannot be edited from
the admin UI.

---

## 4. Aggregation + query surfaces

| Endpoint / query                             | File                                             | Purpose                                          |
|----------------------------------------------|--------------------------------------------------|--------------------------------------------------|
| `/api/v1/costs/summary`                      | `src/aiflow/api/v1/costs.py:66`                  | Global: per-skill + 30-day daily rollup.         |
| `/api/v1/costs/team-daily` (view)            | `src/aiflow/api/v1/costs.py:127` + view `v_daily_team_costs` | Daily team costs (last 100 rows).       |
| `/api/v1/costs/budget` (view)                | `src/aiflow/api/v1/costs.py:152` + view `v_monthly_budget`   | **Already returns per-team budget + alert_level** — but view-only, team-scoped, monthly, no pre-flight. |
| `/api/v1/costs/cap-status`                   | `src/aiflow/api/v1/costs.py:213`                 | Tenant utilisation vs policy cap.                |
| `/api/v1/costs/breakdown`                    | `src/aiflow/api/v1/costs.py:263`                 | Per-model breakdown from `cost_records`.         |
| `CostAttributionRepository.aggregate_running_cost` | `src/aiflow/state/cost_repository.py:65`   | Window-scoped tenant sum — used by cap check.    |

---

## 5. Config surfaces

### 5.1 Policy-level (Sprint L)
`src/aiflow/policy/__init__.py:95`:
```python
cost_cap_usd: float | None            # None = no cap
cost_cap_window_h: int = 24           # rolling window in hours
```
Tenant override via `tenant_overrides[tenant_id]` map (not DB-persisted).
**No pre-flight estimate field.**

### 5.2 Team-level (pre-existing, Alembic 006)
`teams.budget_monthly_usd` — feeds the `v_monthly_budget` view.
**Team-scoped, calendar-month-scoped, view-only — no enforcement.**

### 5.3 Env var audit
Grep for `AIFLOW_MAX_DAILY_COST_USD` / `AIFLOW_COST_` in `src/aiflow/` returns
**zero hits** — no env-var-driven global cap exists today (the kickoff prompt's
reference to a `AIFLOW_MAX_DAILY_COST_USD` env var is aspirational, not
current). Sprint N should not reintroduce a global env cap; budgets belong in
the DB on a per-tenant row.

---

## 6. Gaps Sprint N must close (pre-flight surface)

1. **Pre-flight budget check at the pipeline/step boundary** — nothing today
   refuses to start work because the projected cost would exceed remaining
   budget. Call sites to instrument:
   - `src/aiflow/pipeline/runner.py` — pipeline step entry.
   - `src/aiflow/services/rag_engine/service.py:559` — already has a reactive
     cap; add a pre-flight pairing that consults estimated cost.
   - `src/aiflow/api/v1/process_docs.py:116` / `:309` — document processing
     entry points.

2. **Per-tenant budget row** — a `tenant_budgets` table (Alembic 045) with
   {tenant_id, period, limit_usd, alert_thresholds[], enabled, updated_at}.
   Chosen instead of extending `teams.budget_monthly_usd` because:
   - Tenant boundary ≠ team boundary (v2 contract).
   - Needs multiple periods (daily + monthly) + alert thresholds.
   - UI needs to write to it without ALTER-ing `teams`.

3. **LLM pre-call cost guardrail** — a pre-call estimator that refuses a
   single LLM request projected to exceed a per-step ceiling, with a
   **structured refusal payload** (`{refused: true, reason, projected_usd,
   remaining_usd}`), not an exception. Fits between
   `aiflow.models.client` / `litellm_backend` and the call site.

4. **Admin UI budget surface** — page showing per-tenant budget, utilisation,
   alert thresholds, edit controls. Consumes a new `/api/v1/tenants/{id}/budget`
   CRUD endpoint backed by the new table.

---

## 7. Tests today

| Scope        | File                                                            | Purpose                                   |
|--------------|-----------------------------------------------------------------|-------------------------------------------|
| Unit         | `tests/unit/observability/test_cost_tracker.py`                 | In-memory `CostTracker` behaviour.        |
| Unit         | `tests/unit/policy/test_policy_engine_cost_cap.py` (Sprint L)   | `enforce_cost_cap` semantics.             |
| Integration  | `tests/integration/` — 3 S112 cost-cap enforcement tests        | Real DB aggregation, 429 mapping.         |
| E2E          | 3 Sprint L S111 Monitoring/Runs golden-path                     | Admin UI consumption.                     |

Sprint N must add: pre-flight refusal path unit tests, `tenant_budgets` CRUD
integration tests, pre-flight E2E across UC2/UC3, and an alert-threshold unit
matrix.

---

## 8. Risks flagged for plan-doc

- **Abstraction collision:** `teams.budget_monthly_usd` + `v_monthly_budget`
  already encode "team budget". Decide up-front whether `tenant_budgets` is a
  sibling or a replacement. Current call: sibling, because tenant ≠ team in v2
  and teams are human-grouping, tenants are isolation-boundary.
- **Recorder vs attribution duplication:** two write paths (`record_cost` and
  `CostAttributionRepository.insert_attribution`) target the same table with
  slightly different columns. Sprint N should not expand this; consolidate or
  explicitly document the split.
- **Estimation accuracy:** pre-flight check needs a cost estimator per model.
  litellm provides pricing, but prompt/output token predictions are only
  approximate — STOP condition §5 in the plan doc flags >30% prediction error.
