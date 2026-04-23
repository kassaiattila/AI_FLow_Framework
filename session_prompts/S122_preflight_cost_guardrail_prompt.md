# AIFlow v1.4.10 Sprint N — Session 122 Prompt (pre-flight cost guardrail + structured refusal)

> **Datum:** 2026-04-27
> **Branch:** `feature/v1.4.10-cost-guardrail-budget`
> **HEAD (parent):** `483bd86` (feat(sprint-n): S121 — tenant_budgets table + TenantBudgetService + CRUD endpoint)
> **Port:** API 8102 | UI 5173
> **Elozo session:** S121 — Alembic 045 `tenant_budgets` + `TenantBudgetService` (get/list/upsert/delete/get_remaining) + `/api/v1/tenants/{id}/budget` CRUD. +16 unit, +2 Alembic integration, +3 API integration (2073 -> 2089 unit baseline, Alembic head 045).
> **Terv:** `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` S3 S122; STOP §5.1, §5.3; rollback §7.
> **Session tipus:** IMPLEMENTATION + HARDENING — new guardrail module wired at 3 enforcement points. Feature-flag gated (DRY_RUN default).

---

## KONTEXTUS

### Honnan jottunk (S121)
- Persistence + service + API shipped. `TenantBudgetService.get_remaining(tenant_id, period)` returns a `BudgetView{limit, used, remaining, usage_pct, over_thresholds}` payload — this is the input S122 consumes.
- Zero enforcement logic today. Budgets can be set via PUT but no path reads them at runtime.
- Inventory (S120 `docs/cost_surfaces_inventory.md`): 5 recorder call sites funnel through `aiflow.api.cost_recorder.record_cost`; 2 reactive cap-check surfaces (`PolicyEngine.enforce_cost_cap` + `/api/v1/costs/cap-status`); **0 pre-flight paths**.

### Hova tartunk (S122 — pre-flight refusal + structured payload)
Wire one new guardrail module at 3 enforcement points. A call must be **refused before a cost is incurred** when projected cost > remaining budget. Feature flag gates the whole thing; default off (DRY_RUN logs only, no refusal).

1. **`CostPreflightGuardrail`** under `src/aiflow/guardrails/cost_preflight.py` — stateless, deps injected: `TenantBudgetService`, cost estimator (wraps litellm pricing), clock. Returns `PreflightDecision{allowed, projected_usd, remaining_usd, reason, dry_run}`.
2. **`CostEstimator`** helper — given `(model, input_tokens_estimate, max_output_tokens)` return projected USD using the litellm pricing table (`litellm.cost_per_token`). Fallback to a per-tier ceiling if model missing from table (see STOP §5.3).
3. **Settings** — `AIFLOW_COST_GUARDRAIL__ENABLED` (bool, default false), `AIFLOW_COST_GUARDRAIL__DRY_RUN` (bool, default true), `AIFLOW_COST_GUARDRAIL__PERIOD` (literal `daily`|`monthly`, default `daily`).
4. **Wire 3 enforcement points** (call sites per plan S3 S122):
   - `src/aiflow/pipeline/runner.py` — before a pipeline run starts, resolve tenant_id, call guardrail; on refusal raise `CostGuardrailRefused` (new AIFlowError subclass, HTTP 429 mapping mirroring `CostCapBreached`).
   - `src/aiflow/services/rag_engine/service.py` — before the embed/chat step; already has `enforce_cost_cap` call at line 559, layer pre-flight above it.
   - `src/aiflow/models/client.py` — final backstop at the LLM client boundary so a rogue single call cannot burn the remainder.
5. **Structured refusal payload** — `CostGuardrailRefused.details = {refused: true, reason, projected_usd, remaining_usd, period, dry_run}`. API layer already maps `AIFlowError.http_status` → HTTP status; the JSON body surfaces `details` verbatim.
6. **Tests** — ~15 unit (estimator math + decision logic + DRY_RUN path + 3 wiring smoke tests) + 2 integration (full pipeline refusal against seeded `tenant_budgets` + `cost_records`; DRY_RUN logs but lets the run proceed).

### Jelenlegi allapot
```
27 service | 190 endpoint (+1: tenant-budget CRUD) | 50 DB table | 45 Alembic (head: 045)
2089 unit | 422 e2e | 90+ integration | 8 skill | 23 UI page
Branch: feature/v1.4.10-cost-guardrail-budget (S121 shipped @ 483bd86)
```

---

## ELOFELTETELEK

```bash
git branch --show-current                         # feature/v1.4.10-cost-guardrail-budget
git log --oneline -3                              # HEAD 483bd86
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current  # 045 (head)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1  # 2089 pass
docker ps | grep -E 'postgres|redis'              # real services required (no mocks)
# Confirm S121 surfaces are live:
PYTHONPATH="src;." .venv/Scripts/python.exe -c "from aiflow.services.tenant_budgets import TenantBudgetService, BudgetView; print('ok')"
```

Optional sanity (will be consumed by S122 tests):
```bash
PYTHONPATH="src;." .venv/Scripts/python.exe -c "import litellm; print(litellm.cost_per_token(model='gpt-4o-mini', prompt_tokens=1000, completion_tokens=100))"
```

---

## FELADATOK

### LEPES 1 — `CostPreflightGuardrail` module (~60 min)

```
Cel:    stateless pre-flight decision — projected_usd <= remaining_usd else refuse
Fajlok: src/aiflow/guardrails/cost_preflight.py
        src/aiflow/guardrails/cost_estimator.py
        src/aiflow/core/errors.py  (add CostGuardrailRefused)
Forras: 01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md S3 S122
```

API shape:
```python
class PreflightDecision(BaseModel):
    allowed: bool
    projected_usd: float
    remaining_usd: float | None   # None when no budget row exists (= unlimited for this period)
    reason: str                    # "under_budget" | "over_budget" | "no_budget" | "dry_run_over_budget"
    period: BudgetPeriod
    dry_run: bool

class CostPreflightGuardrail:
    def __init__(self, budgets: TenantBudgetService, estimator: CostEstimator,
                 enabled: bool = False, dry_run: bool = True,
                 period: BudgetPeriod = "daily") -> None: ...

    async def check(self, tenant_id: str, *, model: str,
                    input_tokens: int, max_output_tokens: int) -> PreflightDecision: ...
```

Decision table:
- `enabled=False` -> return `allowed=True, reason="disabled"` (zero I/O).
- `enabled=True, no budget row` -> `allowed=True, reason="no_budget"`.
- `enabled=True, projected <= remaining` -> `allowed=True, reason="under_budget"`.
- `enabled=True, projected > remaining, dry_run=True` -> `allowed=True, reason="dry_run_over_budget"` + `structlog.warning("cost_preflight_over_budget_dry_run", ...)`.
- `enabled=True, projected > remaining, dry_run=False` -> `allowed=False, reason="over_budget"` -> caller raises `CostGuardrailRefused`.

`CostEstimator`:
- `estimate(model, input_tokens, max_output_tokens) -> float` using `litellm.cost_per_token(...)`. On `KeyError`/missing-model fallback to a per-tier ceiling constant (premium=$0.03/1k in, standard=$0.01/1k in, cheap=$0.001/1k in — keep constants colocated, not in env vars).
- Log `structlog.info("cost_estimated", ...)` with `provider_pricing_used: bool`.

### LEPES 2 — `CostGuardrailRefused` error (~10 min)

```
Cel:    AIFlowError subclass mirroring CostCapBreached — HTTP 429, error_code="COST_GUARDRAIL_REFUSED"
Fajlok: src/aiflow/core/errors.py  (append after CostCapBreached)
```

Structured `details`:
```python
{
  "refused": True,
  "tenant_id": ...,
  "projected_usd": ...,
  "remaining_usd": ...,
  "period": ...,
  "reason": "over_budget",
  "dry_run": False,
}
```
`is_transient=False` (refusal is deterministic).

### LEPES 3 — Settings (~15 min)

```
Cel:    one Pydantic settings block that the 3 call sites read
Fajlok: src/aiflow/config.py  (or nearest global settings module — inspect)
```

```python
class CostGuardrailSettings(BaseModel):
    enabled: bool = False
    dry_run: bool = True
    period: BudgetPeriod = "daily"
```

Env prefix: `AIFLOW_COST_GUARDRAIL__*` (matches existing `AIFLOW_DATABASE__*`, `AIFLOW_LANGFUSE__*` convention).

### LEPES 4 — Wire 3 enforcement points (~60 min)

Each wiring MUST:
- Resolve `tenant_id` from the caller's context (ExecutionContext / request principal). If missing, log `structlog.warning("cost_preflight_skipped_no_tenant")` and proceed.
- Pass a sensible `input_tokens` estimate (pipeline: sum of prompt sizes or a configured ceiling; rag_engine: current query + retrieved chunks; models/client: measured prompt tokens).
- Be guarded behind a try/except so a guardrail bug never 500s the request — log + continue in DRY_RUN, log + re-raise only in enforced mode.

#### 4a. `src/aiflow/pipeline/runner.py`
Insert pre-flight at the pipeline entry (before any adapter runs). Raise `CostGuardrailRefused` on refusal — existing error-handling middleware will map it to 429.

#### 4b. `src/aiflow/services/rag_engine/service.py`
Layer pre-flight before the existing `enforce_cost_cap` call (line ~559). Pre-flight is the **first** gate; `enforce_cost_cap` remains as the reactive second gate.

#### 4c. `src/aiflow/models/client.py`
Backstop at the LLM client call boundary. Guard ONLY calls that have a resolvable `tenant_id` on the context — internal maintenance calls (eval harness, promptfoo) must not be gated.

### LEPES 5 — Teszt (~60 min)

Unit (~15):
- `CostEstimator.estimate` — known model (gpt-4o-mini) returns positive cost matching `litellm.cost_per_token` shape.
- `CostEstimator.estimate` — unknown model falls back to per-tier ceiling; emits the `provider_pricing_used=False` log key.
- `CostPreflightGuardrail.check`:
  - `enabled=False` -> `allowed=True, reason="disabled"`, zero `budgets.get_remaining` calls.
  - `no budget row` (`get_remaining` returns None) -> `allowed=True, reason="no_budget"`.
  - `projected < remaining` -> `allowed=True, reason="under_budget"`.
  - `projected > remaining, dry_run=True` -> `allowed=True, reason="dry_run_over_budget"`.
  - `projected > remaining, dry_run=False` -> `allowed=False, reason="over_budget"`.
  - `projected == remaining` boundary case -> allowed (strict `>` refusal).
  - Monthly vs daily period routing passed through to `get_remaining`.
- `CostGuardrailRefused` shape: `http_status == 429`, `error_code == "COST_GUARDRAIL_REFUSED"`, `details` contains the 6 required keys.
- 3 wiring smoke tests: call each wired site with `enabled=False` and assert zero `get_remaining` calls (proves the short-circuit).

Integration (~2, both real Postgres):
- Full pipeline runner refusal: seed `tenant_budgets(limit=$0.01, period=daily)` + `cost_records` sum=$0.009; start a pipeline whose estimate is $0.005 -> allowed; estimate $0.02 -> refused with structured 429 payload, no cost rows written for the refused run.
- DRY_RUN end-to-end: same setup, `AIFLOW_COST_GUARDRAIL__DRY_RUN=true`, over-budget request proceeds, `structlog` emits `cost_preflight_over_budget_dry_run` record.

No E2E in S122 (admin UI budget dashboard + its Playwright E2E is S123).

### LEPES 6 — Validacio + commit

```bash
.venv/Scripts/python.exe -m ruff check src/aiflow/guardrails/cost_preflight.py src/aiflow/guardrails/cost_estimator.py src/aiflow/core/errors.py src/aiflow/pipeline/runner.py src/aiflow/services/rag_engine/service.py src/aiflow/models/client.py tests/unit/guardrails/ tests/integration/ --quiet
.venv/Scripts/python.exe -m ruff format src/aiflow/guardrails/cost_preflight.py src/aiflow/guardrails/cost_estimator.py tests/unit/guardrails/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/guardrails/ -v --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/ -k "cost_preflight or cost_guardrail" --no-cov
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # >= 2104 expected
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/test_cost_cap_enforcement.py --no-cov 2>&1 | tail -5  # no regression on S112
git add src/aiflow/guardrails/cost_preflight.py \
        src/aiflow/guardrails/cost_estimator.py \
        src/aiflow/core/errors.py \
        src/aiflow/config.py \
        src/aiflow/pipeline/runner.py \
        src/aiflow/services/rag_engine/service.py \
        src/aiflow/models/client.py \
        tests/unit/guardrails/ \
        tests/integration/
git commit -m "feat(sprint-n): S122 — pre-flight cost guardrail + structured refusal (flag-gated, dry-run default)"
/session-close S122
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. **Budget math drift** (plan §5.1) — estimator projection vs. actual `aggregate_running_cost` deviates >5% on the replay fixture. Halt and reconcile before wiring enforcement.
2. **Estimation accuracy failure** (plan §5.3) — `|projected - actual| / actual > 0.30` at p95 on the UC2 + UC3 benchmark. Fall back to fixed-ceiling per tier and flag in retro.
3. **More than 8 pre-flight call sites discovered** (plan §5b.2) — split S122 into S122a (module + 3 planned sites) and S122b (remainder); update the plan.
4. **`CostPreflightGuardrail` needs a new DB table or Alembic migration** — out of scope for S122 (S121 shipped the only migration this sprint). Pause before adding.

**SOFT (proceed with note):**
1. `models/client.py` wiring exposes internal-call leakage risk (eval / promptfoo gated) — flag in retro, do NOT add a blanket bypass flag.
2. litellm pricing table missing a production model — ship with per-tier fallback + retro note.

---

## NYITOTT (cross-sprint, carried)

- Sprint M follow-ups: live rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC example.
- Resilience `Clock` seam — deadline 2026-04-30 (still xfails).
- BGE-M3 weight cache as CI artifact.
- Azure OpenAI Profile B live (credits pending).
- Rebase Sprint N onto `main` once PR #17 (Sprint M) merges.

---

## SESSION VEGEN

```
/session-close S122
```

Utana: `/clear` -> `/next` -> S123 (admin UI budget dashboard + 2 Playwright E2E + alert threshold editor).
