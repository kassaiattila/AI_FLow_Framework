# AIFlow v1.4.10 Sprint N — Session 121 Prompt (`tenant_budgets` + `TenantBudgetService` + CRUD endpoint)

> **Datum:** 2026-04-27
> **Branch:** `feature/v1.4.10-cost-guardrail-budget`
> **HEAD (parent):** `89e8c7a` (chore(sprint-n): S120 kickoff — cost guardrail + per-tenant budget plan + inventory)
> **Port:** API 8102 | UI 5173
> **Elozo session:** S120 — Sprint N kickoff: inventory + plan doc. 2073 unit / 422 e2e / Alembic head `044`.
> **Terv:** `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` §3 S121; inventory §5–§8.
> **Session tipus:** IMPLEMENTATION — new DB table + service + CRUD endpoint. Additive migration. No guardrail wiring yet (that is S122).

---

## KONTEXTUS

### Honnan jottunk (S120 kickoff)
- Plan doc locked; session queue S121→S124.
- Inventory confirmed: 0 pre-flight paths, 5 recorders funnel through `record_cost`, 2 reactive cap-checks only.
- Abstraction decision recorded: `tenant_budgets` ships as a **sibling** to `teams.budget_monthly_usd` (Alembic 006) — tenant ≠ team; v2 multi-tenant isolation boundary is tenant.

### Hova tartunk (S121 — persistence + service layer)
Ship the DB + service + API contract that S122 (pre-flight guardrail) will consume. No enforcement logic here — only CRUD + read-side aggregation hook.

1. **Alembic 045** — create `tenant_budgets` table with tenant-scoped rows per period (daily + monthly), alert thresholds, enabled flag, updated_at. Additive; no existing columns touched.
2. **`TenantBudgetService`** under `src/aiflow/services/tenant_budgets/` — async CRUD (`get`, `upsert`, `list`, `delete`) + one read helper `get_remaining(tenant_id, period)` that subtracts `CostAttributionRepository.aggregate_running_cost` from the period's limit.
3. **CRUD endpoint** `/api/v1/tenants/{tenant_id}/budget` — GET + PUT + DELETE on the `TenantBudgetService`. Respect existing auth/role gates (see `src/aiflow/api/v1/costs.py` as the closest sibling; use the same router registration pattern).
4. **Unit tests** — ~10 (service CRUD + `get_remaining` math on fixture) + 1 integration test (Alembic 045 upgrade/downgrade round-trip) + 1 API test (GET/PUT/DELETE round-trip with fake auth).

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB table | 44 Alembic (head: 044)
2073 unit | 422 e2e | 88+ integration | 8 skill | 23 UI page
Branch: feature/v1.4.10-cost-guardrail-budget (pushed, tracking origin)
```

---

## ELOFELTETELEK

```bash
git branch --show-current                         # feature/v1.4.10-cost-guardrail-budget
git log --oneline -3                              # HEAD 89e8c7a
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current  # 044 (head)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2073 pass
docker ps | grep -E 'postgres|redis'              # real services required (no mocks)
```

---

## FELADATOK

### LEPES 1 — Alembic 045 `tenant_budgets` (~30 min)

```
Cel:    new table for per-tenant budget rows, additive
Fajlok: alembic/versions/045_tenant_budgets.py
Forras: 01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md §3 S121
```

Schema:
```python
tenant_budgets:
  id              UUID PK default gen_random_uuid()
  tenant_id       VARCHAR(255) NOT NULL
  period          VARCHAR(20) NOT NULL  -- 'daily' | 'monthly'
  limit_usd       NUMERIC(12,6) NOT NULL
  alert_threshold_pct  INT[] NOT NULL DEFAULT '{50,80,95}'  -- percent points for warning emission
  enabled         BOOLEAN NOT NULL DEFAULT TRUE
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
UNIQUE (tenant_id, period)  -- one row per (tenant, period)
INDEX idx_tenant_budgets_tenant_id ON tenant_budgets(tenant_id)
```

Constraints:
- `period IN ('daily','monthly')` CHECK.
- `limit_usd >= 0` CHECK.
- `alert_threshold_pct` — each element in `[1,100]`, sorted ascending (validate in service, not DB — Postgres array CHECK too ceremony).

Run migration round-trip:
```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic upgrade head
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic downgrade -1
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic upgrade head
```

### LEPES 2 — `TenantBudgetService` (~45 min)

```
Cel:    async CRUD + get_remaining hook (no enforcement)
Fajlok: src/aiflow/services/tenant_budgets/__init__.py
        src/aiflow/services/tenant_budgets/service.py
        src/aiflow/services/tenant_budgets/contracts.py (Pydantic TenantBudget + BudgetView)
Forras: inventory §4 (CostAttributionRepository), plan doc §3 S121
```

Service API (async):
```python
class TenantBudgetService:
    def __init__(self, pool: asyncpg.Pool, cost_repo: CostAttributionRepository) -> None: ...

    async def get(self, tenant_id: str, period: str) -> TenantBudget | None: ...
    async def list(self, tenant_id: str) -> list[TenantBudget]: ...  # all periods for a tenant
    async def upsert(self, budget: TenantBudget) -> TenantBudget: ...  # insert or update by (tenant_id, period)
    async def delete(self, tenant_id: str, period: str) -> bool: ...

    async def get_remaining(self, tenant_id: str, period: str) -> BudgetView | None:
        """limit - aggregate_running_cost over period window. None if no budget row."""
```

Window mapping:
- `period='daily'`  → `window_h=24`
- `period='monthly'` → `window_h=24*30` (calendar-month approximation; S122 can refine if needed)

**Do not** write enforcement here — just aggregation + return `BudgetView{limit_usd, used_usd, remaining_usd, usage_pct, over_thresholds: list[int]}`.

### LEPES 3 — CRUD endpoint `/api/v1/tenants/{tenant_id}/budget` (~30 min)

```
Cel:    GET/PUT/DELETE endpoint, same auth as /api/v1/costs/*
Fajlok: src/aiflow/api/v1/tenant_budgets.py  (new router)
        src/aiflow/api/app.py               (router include)
Forras: src/aiflow/api/v1/costs.py (pattern), plan §3 S121
```

Endpoints:
- `GET /api/v1/tenants/{tenant_id}/budget` → list all periods for the tenant.
- `GET /api/v1/tenants/{tenant_id}/budget/{period}` → single budget + live `BudgetView`.
- `PUT /api/v1/tenants/{tenant_id}/budget/{period}` → upsert body `{limit_usd, alert_threshold_pct, enabled}`.
- `DELETE /api/v1/tenants/{tenant_id}/budget/{period}` → delete row (soft: `enabled=false` instead? → plan says hard-delete, soft is out of scope).

Respond with `BudgetView` on reads for UI consumption in S123.

### LEPES 4 — Teszt (~60 min)

Unit (~10):
- Service `get` / `list` / `upsert` (insert + update paths) / `delete` happy + missing row.
- `get_remaining` math: limit=100, aggregate=30 → remaining=70, usage_pct=30, over_thresholds=[].
- `get_remaining`: limit=100, aggregate=85 → over_thresholds=[50,80] (sorted).
- `get_remaining` on non-existent budget → `None`.
- Pydantic validator: `alert_threshold_pct` sort + range rejection.

Integration (1):
- Alembic 045 upgrade/downgrade round-trip against real Postgres — row survives upgrade → downgrade → upgrade replay.

API (1):
- Round-trip: `PUT` creates, `GET` returns it with `BudgetView` + correct `used_usd` from a pre-seeded `cost_records` fixture, `DELETE` removes it, `GET` → 404.

No E2E in S121 (reserved for S123 UI).

### LEPES 5 — Validacio + commit

```bash
.venv/Scripts/python.exe -m ruff check src/aiflow/services/tenant_budgets/ src/aiflow/api/v1/tenant_budgets.py tests/unit/services/tenant_budgets/ tests/integration/ --quiet
.venv/Scripts/python.exe -m ruff format src/aiflow/services/tenant_budgets/ src/aiflow/api/v1/tenant_budgets.py tests/unit/services/tenant_budgets/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/services/tenant_budgets/ -v --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/ -k "tenant_budget or alembic_045" --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # full baseline — no regression
git add alembic/versions/045_tenant_budgets.py \
        src/aiflow/services/tenant_budgets/ \
        src/aiflow/api/v1/tenant_budgets.py \
        src/aiflow/api/app.py \
        tests/unit/services/tenant_budgets/ \
        tests/integration/
git commit -m "feat(sprint-n): S121 — tenant_budgets table + TenantBudgetService + CRUD endpoint"
/session-close S121
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. Alembic 045 upgrade fails on dev DB (schema conflict with an existing `tenant_budgets` — inventory §8 SOFT stop becomes HARD). Plan needs revision.
2. `CostAttributionRepository.aggregate_running_cost` signature change required — touches the Sprint L S112 contract; confirm before editing.
3. Auth model for `/api/v1/tenants/{id}/budget` does not fit the existing costs router pattern (e.g., needs new role) — pause to align with user.

**SOFT (proceed with note):**
1. `alert_threshold_pct` array validation feels heavy in Pydantic — acceptable to land as a simple `list[int]` with service-side sort + range check; flag for retro.
2. `period` enum only covers daily/monthly — if a stakeholder needs weekly later, note in retro; don't expand now.

---

## NYITOTT (cross-sprint)

- Sprint M follow-ups (carried): live rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC example.
- Resilience `Clock` seam — deadline 2026-04-30 (still xfails).
- BGE-M3 weight cache as CI artifact.
- Azure OpenAI Profile B live (credits pending).
- Rebase Sprint N onto `main` once PR #17 (Sprint M) merges.

---

## SESSION VEGEN

```
/session-close S121
```

Utana: `/clear` -> `/next` -> S122 (pre-flight guardrail wiring + structured refusal payload).
