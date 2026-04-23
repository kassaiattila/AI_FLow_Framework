# Sprint N (v1.4.10) — LLM cost guardrail + per-tenant budget

> **Depends on:** Sprint M PR #17 (`feature/v1.4.9-vault-langfuse` → `main`).
> This branch was cut from Sprint M tip `d3e2d4a` while #17 was OPEN,
> MERGEABLE. After #17 merges, rebase this branch onto fresh `main`
> before squash-merging. Do not force-rebase until #17 lands.

## Summary

- **`tenant_budgets` — new per-tenant, per-period budget domain** (Alembic
  045). DB table + `TenantBudgetService` + `/api/v1/tenants/{id}/budget[/{period}]`
  router (list / get / upsert / delete). Sibling to `teams.budget_monthly_usd`
  (kept as-is — tenants ≠ teams under v2).
- **`CostPreflightGuardrail` — pre-flight refusal before work starts,
  flag-gated and dry-run by default.** Wired at three boundaries:
  `pipeline/runner.py`, `services/rag_engine/service.py`, and
  `models/client.py`. Returns a `PreflightDecision`; callers raise
  `CostGuardrailRefused` (HTTP 429, structured `{refused, projected_usd,
  remaining_usd, period, reason, dry_run}` payload). Sprint L's reactive cap
  (`CostCapBreached`) stays as the second gate.
- **Admin UI `/budget-management`** — single page, daily + monthly card
  grid per tenant, React Aria chip editor for `alert_threshold_pct`, live
  projection (`used / limit / remaining / usage_pct / over_thresholds`), 2
  Playwright E2E (render round-trip + threshold edit with hard-reload
  regression guard). `/live-test` report at
  `tests/ui-live/budget-management.md`.
- **Rollout is a no-op for existing deploys.** `AIFLOW_COST_GUARDRAIL__ENABLED=false`
  (default) and `AIFLOW_COST_GUARDRAIL__DRY_RUN=true` (default). Per-tenant
  flip is the enablement gate.

## Acceptance criteria (per `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` §3 + §8)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `tenant_budgets` table with tenant-scoped period budgets, alert thresholds, enabled flag | ✅ | `alembic/versions/045_tenant_budgets.py`, `tests/integration/alembic/test_045_tenant_budgets.py` (2 tests — upgrade round-trip + data round-trip) |
| 2 | `TenantBudgetService` with `get / list / upsert / delete / get_remaining` against real Postgres | ✅ | `src/aiflow/services/tenant_budgets/service.py`, `contracts.py`; 16 unit + 3 API integration tests |
| 3 | `/api/v1/tenants/{tenant_id}/budget[/{period}]` CRUD behind `AuthMiddleware` | ✅ | `src/aiflow/api/v1/tenant_budgets.py`; `tests/integration/api/test_tenant_budgets_api.py` |
| 4 | Pre-flight guardrail at pipeline + RAG + LLM-client boundaries, structured refusal payload | ✅ | `src/aiflow/guardrails/cost_preflight.py`, `cost_estimator.py`; `src/aiflow/core/errors.py::CostGuardrailRefused`; wiring in `pipeline/runner.py`, `services/rag_engine/service.py`, `models/client.py`; 24 unit + 3 integration tests |
| 5 | Feature flag + dry-run default (`AIFLOW_COST_GUARDRAIL__ENABLED=false`, `__DRY_RUN=true`); flag-off is identical to Sprint M tip | ✅ | `src/aiflow/core/config.py::CostGuardrailSettings`; flag-off regression covered by existing suites (no change when flag off). |
| 6 | Admin UI budget dashboard + alert threshold editor, 2 Playwright E2E, `/live-test` PASS | ✅ | `aiflow-admin/src/pages-new/BudgetManagement/` + `tests/e2e/test_budget_management.py` + `tests/ui-live/budget-management.md` |
| 7 | No regression in Sprint L reactive cap (S112 `cost_cap_enforcement` stays green) | ✅ | Unit + integration baseline stable (2113 unit / ~96 integration). |
| 8 | Plan exit gate: structured refusal `{refused, reason, projected_usd, remaining_usd}` with no `cost_records` written for a refused run | ✅ | Covered by `test_cost_preflight_guardrail.py::test_over_budget_enforced` (no row inserted when `allowed=False`). |

**Sprint N closes green on criteria 1–8.** Guardrail enforcement remains
flag-gated per plan §7 rollback: staging operators enable per-tenant with
`DRY_RUN=true` first, watch the `cost.preflight.dry_run_over_budget`
structlog events, then flip `DRY_RUN=false`. Rollback is a flag flip.

## What changed

### Source code

| File | Change | Session |
|---|---|---|
| `alembic/versions/045_tenant_budgets.py` | **NEW** — additive migration: `tenant_budgets` UUID PK, `UNIQUE(tenant_id, period)`, `CHECK period IN ('daily','monthly')`, `CHECK limit_usd >= 0`, `alert_threshold_pct integer[]`, `enabled`, `created_at / updated_at` | S121 |
| `src/aiflow/services/tenant_budgets/__init__.py` | **NEW** — module facade (re-exports) | S121 |
| `src/aiflow/services/tenant_budgets/contracts.py` | **NEW** — `BudgetPeriod`, `TenantBudget`, `BudgetView` Pydantic models | S121 |
| `src/aiflow/services/tenant_budgets/service.py` | **NEW** — `TenantBudgetService` (async CRUD + `get_remaining` over `CostAttributionRepository.aggregate_running_cost`) | S121 |
| `src/aiflow/api/v1/tenant_budgets.py` | **NEW** — FastAPI router, `TenantIdPath`/`PeriodPath` `Annotated` aliases, `TenantBudgetUpsertRequest` with threshold validator | S121 |
| `src/aiflow/api/app.py` | Router registration + `CostGuardrailRefused` handler → HTTP 429 | S121 / S122 |
| `src/aiflow/guardrails/cost_estimator.py` | **NEW** — `CostEstimator` wrapping `litellm.cost_per_token` with per-tier fallback | S122 |
| `src/aiflow/guardrails/cost_preflight.py` | **NEW** — `CostPreflightGuardrail` + `PreflightDecision` + `PreflightReason` enum; pure decision, no exception raising | S122 |
| `src/aiflow/core/errors.py` | Added `CostGuardrailRefused` (`PermanentError`, HTTP 429, structured `details`) | S122 |
| `src/aiflow/core/config.py` | Added `CostGuardrailSettings` nested config (enabled / dry_run / per-tier ceilings) | S122 |
| `src/aiflow/pipeline/runner.py` | Pre-flight hook at pipeline entry (step-count scaled) | S122 |
| `src/aiflow/services/rag_engine/service.py` | Pre-flight above the existing S112 reactive cap | S122 |
| `src/aiflow/models/client.py` | LLM-client backstop — opts in via `tenant_id=` kwarg; no-tenant calls are never gated | S122 |
| `aiflow-admin/src/pages-new/BudgetManagement/index.tsx` | **NEW** — tenant input + daily/monthly `BudgetCard` grid | S123 |
| `aiflow-admin/src/pages-new/BudgetManagement/BudgetCard.tsx` | **NEW** — live projection + editor form, Save disabled until diff | S123 |
| `aiflow-admin/src/pages-new/BudgetManagement/ThresholdEditor.tsx` | **NEW** — React Aria chip input, Enter/comma adds, backspace removes, dedup+sort, aria-describedby errors | S123 |
| `aiflow-admin/src/pages-new/BudgetManagement/types.ts` | **NEW** — mirrors `services/tenant_budgets/contracts` | S123 |
| `aiflow-admin/src/router.tsx` | Added `/budget-management` route | S123 |
| `aiflow-admin/src/layout/Sidebar.tsx` | Added `aiflow.menu.budgets` nav item (Monitoring group) | S123 |
| `aiflow-admin/src/locales/{en,hu}.json` | Title, subtitle, menu labels | S123 |

### Tests

| File | Added | Session |
|---|---|---|
| `tests/unit/services/tenant_budgets/test_contracts.py` | 127 lines (contracts validation — period enum, threshold bounds, alphabetical sort invariant) | S121 |
| `tests/unit/services/tenant_budgets/test_service.py` | 141 lines (service math, window mapping, over_thresholds ordering) | S121 |
| `tests/integration/alembic/test_045_tenant_budgets.py` | 205 lines (upgrade/downgrade round-trip + data round-trip against real Postgres) | S121 |
| `tests/integration/api/test_tenant_budgets_api.py` | 212 lines (PUT/GET/DELETE round-trip with seeded `cost_records`; invalid period / threshold rejection) | S121 |
| `tests/unit/guardrails/test_cost_estimator.py` | 79 lines (litellm hit / miss / per-tier fallback / token-count edge cases) | S122 |
| `tests/unit/guardrails/test_cost_preflight.py` | 210 lines (decision table — disabled / no_budget / under / over / dry_run_over; refusal error shape) | S122 |
| `tests/unit/guardrails/test_cost_preflight_wiring.py` | 179 lines (5 wiring smoke tests across pipeline / rag_engine / models.client) | S122 |
| `tests/integration/test_cost_preflight_guardrail.py` | 196 lines (real Postgres, seeded `tenant_budgets` + `cost_records` — under-budget allowed, over-budget enforced, over-budget dry-run logs only) | S122 |
| `tests/e2e/test_budget_management.py` | 180 lines (2 Python Playwright E2E: render live view after seeded PUT; edit thresholds + Save + hard reload round-trip) | S123 |
| `tests/ui-live/budget-management.md` | **NEW** — `/live-test` Playwright MCP report, PASS | S123 |

### Docs + plan

- `docs/cost_surfaces_inventory.md` (**NEW** — S120) — catalog of 5 recorder / 2 cap-check / 4 aggregation / 2 config / **0 pre-flight** sites; confirms `AIFLOW_MAX_DAILY_COST_USD` does not exist in the current code; flags `CostAttributionRepository` vs `record_cost` duplication as soft follow-up.
- `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` (**NEW** — S120) — full plan: session queue S120–S124, Alembic scope (one additive), STOP conditions (math drift ±5%, estimation error > 30%), rollback, success metrics.
- `docs/sprint_n_plan.md` (**NEW** — S120) — short summary pointing at the full plan doc.
- `aiflow-admin/src/journeys/budget_management.md` (**NEW** — S123) — user journey + API contract spec.
- `docs/sprint_n_retro.md` (**NEW** — S124) — scope, test deltas, decisions log SN-1..SN-7, 12 follow-up issues.
- `docs/sprint_n_pr_description.md` (this file — S124).
- `CLAUDE.md` — Overview flipped to Sprint N **DONE 2026-04-28**, Key Numbers updated (190 endpoints / 29 routers / 45 Alembic / 2113 unit / 424 E2E / 24 UI pages); Sprint M DONE block preserved (append-style history).

## Test deltas

| Suite | Before (Sprint M tip = v1.4.9 candidate) | After (Sprint N tip) | Delta |
|---|---|---|---|
| Unit | 2073 | **2113** | +40 (16 S121 tenant_budgets + 24 S122 guardrail; S123 UI-only) |
| Integration | 88+ | **~96** | +8 (2 Alembic 045 + 3 tenant_budgets API + 3 cost_preflight_guardrail) |
| E2E collected | 422 | **424** | +2 (S123 `test_budget_management.py`) |
| Alembic head | 044 | **045** | +1 (S121 `tenant_budgets`) |
| API endpoints | 189 | **190** (29 routers) | +1 router (`tenant-budgets`, 4 routes) — router-level count per CLAUDE.md convention |
| UI pages | 23 | **24** | +1 (`/budget-management`) |
| Ruff / TSC | clean | clean | 0 new errors. |

## Validation evidence

```bash
# All commands on HEAD 751107d (S123 shipped)
git branch --show-current                # feature/v1.4.10-cost-guardrail-budget
git log --oneline d3e2d4a..HEAD          # 9 commits (1 kickoff + 3 feat + 4 chore + 1 close)

PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# 2113 passed, 1 skipped, 1 xpassed

PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e --collect-only -q --no-cov
# 424 tests collected

PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current
# 045 (head)

.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet       # exit 0
.venv/Scripts/python.exe -m ruff format --check src/ tests/      # exit 0
cd aiflow-admin && npx tsc --noEmit                              # exit 0

# Integration (requires Postgres on 5433)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest \
  tests/integration/alembic/test_045_tenant_budgets.py \
  tests/integration/api/test_tenant_budgets_api.py \
  tests/integration/test_cost_preflight_guardrail.py -q
# 8 passed

# /live-test (requires uvicorn on 8102 + Vite on 5173)
cat tests/ui-live/budget-management.md   # PASS report, Playwright MCP
```

## Breaking changes

**None.** Every change is additive:

- `AIFLOW_COST_GUARDRAIL__ENABLED=false` (default) — pre-flight is a no-op. Behavior identical to Sprint M tip.
- `AIFLOW_COST_GUARDRAIL__DRY_RUN=true` (default, when enabled) — over-budget logs but does not refuse.
- `TenantBudgetService` is a new service; no existing service changed signature.
- `/api/v1/tenants/{id}/budget[/{period}]` is a new router; no existing route changed.
- `CostGuardrailRefused` is a new error class; Sprint L `CostCapBreached` (HTTP 429) unchanged.
- `models.client.generate()` gains an **optional** `tenant_id=` kwarg; existing callers unchanged.
- Alembic 045 is additive (new table + indexes + constraints). `alembic downgrade -1` drops the table only; no existing data touched.

## Deployment notes

### Existing deployers — zero action

Default env is flag-off. No behaviour change. You can land this PR and not
configure anything.

### Enabling the guardrail (per tenant, recommended ladder)

1. **Seed a budget:** `PUT /api/v1/tenants/{id}/budget/daily` with `{ "limit_usd": 5.0, "alert_threshold_pct": [50, 80, 95], "enabled": true }` (or via the `/budget-management` admin page).
2. **Flip flag on, keep dry-run on:** `AIFLOW_COST_GUARDRAIL__ENABLED=true` + `AIFLOW_COST_GUARDRAIL__DRY_RUN=true`.
3. **Watch structlog:** `event=cost.preflight.dry_run_over_budget` lines show projected refusals. Let this soak for a release cycle.
4. **Flip dry-run off:** `AIFLOW_COST_GUARDRAIL__DRY_RUN=false`. Over-budget calls now raise `CostGuardrailRefused` → HTTP 429.
5. **Rollback:** flip `__ENABLED=false`. Zero code revert needed.

Full flow documented in `docs/sprint_n_retro.md` "Decisions log SN-3".

## Follow-up issues (filed into Sprint N+1 backlog)

From Sprint N retro §"Follow-up issues" — 12 entries total, key ones:

1. `CostAttributionRepository.insert_attribution` ↔ `cost_recorder.record_cost` consolidation (both write `cost_records`).
2. Model-tier fallback ceilings → `CostGuardrailSettings` (currently hard-coded in `CostEstimator`).
3. Grafana panel distinguishing `cost_guardrail_refused` vs `cost_cap_breached`.
4. litellm pricing coverage audit as CI step.
5. `/status` fetches `/openapi.json` and diffs tags (would catch stale-uvicorn class of bug).
6. `CostSettings` umbrella class (consolidate `BudgetSettings` Sprint L + `CostGuardrailSettings` Sprint N).
7. Soft-quota / over-draft semantics — customer ask, out of scope this sprint.
8. `scripts/seed_tenant_budgets_dev.py` for demo onboarding.

**Carried (unchanged):** Sprint M — live Vault rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap`, AppRole prod IaC, Langfuse v3→v4, `SecretProvider` registry slot. Sprint J — BGE-M3 weight cache CI artifact, Azure OpenAI Profile B live (credits pending), resilience `Clock` seam (deadline 2026-04-30, still xfails), coverage uplift (issue #7). Sprint L — `/live-test` `--network=none` variant.

## Post-merge

```bash
# After Sprint M PR #17 merges to main, and after this PR #18 (or whichever number it gets) merges:
git fetch origin && git checkout main && git pull
git tag v1.4.10 -a -m "Sprint N: LLM cost guardrail + per-tenant budget"
git push origin v1.4.10
```

## Test plan for reviewers

- [ ] **Rebase dependency:** confirm Sprint M PR #17 is merged before this one (or re-request review after rebase).
- [ ] `git checkout feature/v1.4.10-cost-guardrail-budget && git log --oneline d3e2d4a..HEAD` — confirm 9 commits (1 kickoff + 3 feat + 4 chore + 1 close).
- [ ] `PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov` — 2113 pass / 1 skip / 1 xpass.
- [ ] `PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e --collect-only -q --no-cov` — 424 collected.
- [ ] `PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — Alembic 045 round-trip clean.
- [ ] `cd aiflow-admin && npx tsc --noEmit` — TSC clean.
- [ ] **Flag-off regression check:** run the full unit + integration suites with `AIFLOW_COST_GUARDRAIL__ENABLED=false` (default). Expected: no change vs Sprint M tip.
- [ ] **Flag-on dry-run check:** set `AIFLOW_COST_GUARDRAIL__ENABLED=true` + `AIFLOW_COST_GUARDRAIL__DRY_RUN=true`; replay a known over-budget RAG query; expect structlog `event=cost.preflight.dry_run_over_budget` and no 429 at the wire.
- [ ] **Flag-on enforced check:** `__DRY_RUN=false`; replay same query; expect HTTP 429 with `{refused: true, reason: "over_budget", projected_usd, remaining_usd, period}`.
- [ ] Read `docs/sprint_n_retro.md` decisions log — agree with **SN-1** (sibling table vs extending `teams.budget_monthly_usd`) and **SN-4** (LLM-client backstop opts in via `tenant_id=`)?
- [ ] Read `tests/ui-live/budget-management.md` — does the journey match how you'd walk a new operator through the feature?

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
