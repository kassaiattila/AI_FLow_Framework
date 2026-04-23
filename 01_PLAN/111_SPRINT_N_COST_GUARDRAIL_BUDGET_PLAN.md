# AIFlow v1.4.10 Sprint N — LLM Cost Guardrail + Per-Tenant Budget

> **Status:** ACTIVE — kickoff S120 on 2026-04-26.
> **Branch:** `feature/v1.4.10-cost-guardrail-budget` (cut from `feature/v1.4.9-vault-langfuse` tip `d3e2d4a` while PR #17 is OPEN, MERGEABLE).
> **Predecessor:** v1.4.9 Sprint M DONE 2026-04-25 (Vault + self-hosted Langfuse).
> **Target tag (post-merge):** `v1.4.10`.
> **Parent plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 (Sprint L cost enforcement recap) + §7 (test strategy).

---

## 1. Why this sprint

Sprint L (v1.4.8) delivered **reactive** cost enforcement — when a tenant's
running cost (sum of `cost_records.cost_usd` over `cost_cap_window_h`) crosses
`PolicyConfig.cost_cap_usd`, `PolicyEngine.enforce_cost_cap` raises
`CostCapBreached` and the API returns HTTP 429. That protects the tenant from
unbounded cost, but it fires **after** a run has already started.

Three gaps surfaced in customer feedback after Sprint L:

1. **No pre-flight refusal.** A pipeline run starts, hits the cap mid-run,
   and half the work is already spent. Customers want a pre-flight gate: "if
   remaining budget < estimated cost, refuse this run now."
2. **No per-tenant budget configuration.** The cap lives in
   `PolicyConfig.cost_cap_usd` and `tenant_overrides` (in-process config), not
   in a DB table surfaced to the admin UI. `teams.budget_monthly_usd` exists
   but is team-scoped, monthly, and view-only (see inventory §5).
3. **No LLM-call-level guardrail.** A single rogue request (very large prompt,
   expensive model) can burn remaining budget in one call. Customers want a
   refusal at the LLM client boundary with a structured reason, not an
   exception.

Sprint N closes all three.

---

## 2. Discovery outcome

Full inventory: `docs/cost_surfaces_inventory.md` (produced S120).

**Key findings:**

- **5 recorder call sites**, all funnel through
  `aiflow.api.cost_recorder.record_cost` → `cost_records` table. Writers are
  best-effort (swallow errors). Sprint L added `cost_records.tenant_id`
  (Alembic 043) and nullable `workflow_run_id` (Alembic 044) — the schema is
  ready for tenant-scoped aggregation.
- **2 cap-check surfaces** (`PolicyEngine.enforce_cost_cap` +
  `/api/v1/costs/cap-status`). Only one caller (`rag_engine/service.py:559`);
  process-docs and pipeline runner recorders have **no** pre-flight pairing.
- **0 pre-flight paths** today — the whole category is greenfield.
- **Pre-existing abstractions to respect:** `teams.budget_monthly_usd` +
  `v_monthly_budget` view (Alembic 006). Sprint N ships a **sibling**
  `tenant_budgets` table (tenants ≠ teams under the v2 contract; different
  cardinality, different period semantics).
- **Env var gap:** `AIFLOW_MAX_DAILY_COST_USD` does NOT exist today (grep
  returns zero hits). Sprint N will not introduce a global env cap; budgets
  belong in per-tenant DB rows.

---

## 3. Session queue (locked)

| Session | Scope                                                                                     | Artifacts                                                            | Alembic |
|---------|-------------------------------------------------------------------------------------------|----------------------------------------------------------------------|---------|
| **S120** | Kickoff — branch cut, cost-surface inventory, plan doc, CLAUDE.md banner.                | `docs/cost_surfaces_inventory.md`, `docs/sprint_n_plan.md`, this file. | 0       |
| **S121** | `tenant_budgets` table + `TenantBudgetService` + CRUD endpoint.                           | Alembic 045, `src/aiflow/services/tenant_budgets/`, `/api/v1/tenants/{id}/budget` GET/PUT. | 1 |
| **S122** | Pre-flight guardrail at pipeline + step + LLM-call boundary. Structured refusal payload. | `src/aiflow/guardrails/cost_preflight.py`, hooks into `pipeline/runner.py` + `services/rag_engine/service.py` + `models/client.py`. Feature flag `AIFLOW_COST_GUARDRAIL__ENABLED=false` default. | 0 |
| **S123** | Admin UI budget dashboard + alert threshold editor.                                       | `aiflow-admin/src/pages/BudgetManagement/`, 2 Playwright E2E.        | 0       |
| **S124** | Sprint N close — PR cut, retro, tag `v1.4.10`, CLAUDE.md numbers.                         | `docs/sprint_n_retro.md`, `docs/sprint_n_pr_description.md`.         | 0       |

Total: 1 new Alembic migration (additive), 1 new service, 1 new guardrail
module, 1 new UI page, 1 new feature flag. No existing table altered.

---

## 4. Dependencies + blockers

**Ready to go (confirmed S120):**
- `cost_records.tenant_id` (Alembic 043) — present.
- `cost_records.workflow_run_id` nullable (Alembic 044) — present, verified
  via `runtime DO $$ ... DROP NOT NULL` in `record_cost`.
- `CostAttributionRepository.aggregate_running_cost` — window-scoped tenant sum
  already exists; S122 reuses it.
- `PolicyEngine.get_for_tenant` — tenant-scoped config already in place; S122
  layers pre-flight on top.

**Needed but not blocking kickoff:**
- `TenantService` for tenant-id resolution in UI (exists; verify it exposes a
  listing endpoint before S123).
- litellm pricing table for cost estimation (present via `litellm_backend`;
  S122 wraps it).

**Cross-sprint carry-overs (non-blocking for Sprint N):**
- Sprint M follow-ups: live rotation E2E, `AIFLOW_ENV=prod` root-token guard,
  `make langfuse-bootstrap` target, AppRole prod IaC example.
- Resilience `Clock` seam — deadline 2026-04-30 (separate issue).
- BGE-M3 weight cache as CI artifact.
- Azure OpenAI Profile B live (credits pending).

---

## 5. STOP conditions (hard)

1. **Budget math drift** — sum of `cost_records.cost_usd` for a tenant over
   the last `window_h` hours ≠ pre-flight projection error within ±5% on a
   fixed replay fixture. Halt S122 until reconciled.
2. **UI cannot render real-time with Redis down** — if the budget dashboard
   hard-depends on Redis for aggregation (it should not; aggregation must be
   DB-direct), halt S123 and refactor.
3. **LLM cost estimation prediction error > 30%** on the benchmark run (UC2
   RAG + UC3 email on a 100-request fixture). Halt S122 and fall back to a
   fixed-ceiling estimate per model tier.
4. **PR #17 (Sprint M) gets CLOSED without MERGE** before Sprint N ships —
   Sprint N branch is cut from the Sprint M tip, so a Sprint M rejection
   invalidates the base. Halt and hand back to user.

## 5b. STOP conditions (soft — proceed with note)

1. **`CostAttributionRepository` vs `record_cost` duplication** — both write to
   `cost_records`. Sprint N must not expand this; flag in retro if a
   consolidation opportunity is obvious.
2. **More than 8 pre-flight call sites needed** — inventory already lists 3
   call sites; if S122 discovers more (>8), split into S122a/S122b per retro
   template.

---

## 6. Out of scope (explicit)

- External billing integration (Stripe, invoicing).
- Automated refund / credit issuance on over-spend.
- Per-user (not per-tenant) budget granularity.
- Soft quota "over-draft" (allow run, charge premium).
- Historical budget backfill — budgets take effect from insertion forward.
- Retiring `teams.budget_monthly_usd` / `v_monthly_budget` — kept in place as
  a sibling; deprecation is a separate sprint.

---

## 7. Rollback plan

Each session lands as a standalone commit; each is independently reversible.

- **S121** (Alembic 045) — migration is additive (new table + indexes). Revert
  = `alembic downgrade -1`. No data loss because no existing data is modified.
- **S122** (guardrail) — gated behind `AIFLOW_COST_GUARDRAIL__ENABLED=false`
  default. Revert = flip flag; code stays dormant. Full revert = `git revert`
  the commit; no DB state depends on it.
- **S123** (UI) — pure admin-dashboard page; revert = remove the route, no
  backend coupling beyond S121's CRUD endpoint.
- **S124** (close) — docs + PR; revert is a git operation only.

**Production rollout gate:** ship S121–S123 with the flag OFF. Flip on per
tenant via env override after a soak period with pre-flight logs only (no
refusals yet, wired via a `DRY_RUN` flag on the guardrail).

---

## 8. Success metrics

- **Pre-flight refusal works end-to-end:** a pipeline run against a
  near-zero budget refuses at the pipeline boundary with a structured
  `{refused: true, reason, projected_usd, remaining_usd}` payload — no
  `cost_records` rows written for the refused run.
- **Admin UI surfaces tenant budget:** dashboard renders current utilisation,
  alert thresholds editable, changes persist to `tenant_budgets` round-trip.
- **No regression** in Sprint L's reactive cap behaviour — existing S112
  cost-cap enforcement integration tests stay green.
- **Estimation accuracy:** on the benchmark fixture (UC2 + UC3, 100 requests),
  `|projected - actual| / actual <= 0.30` at p95.
- **Baseline unit count:** 2073 → ≥ 2110 (S121 ~ +10, S122 ~ +15, S123 ~ +5
  API contract tests).

---

## 9. Reference

- Parent plan: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 (Sprint L recap) + §7
  (test strategy).
- Inventory: `docs/cost_surfaces_inventory.md`.
- Sprint M retro (precedent): `docs/sprint_m_retro.md`.
- Predecessor plan doc (structural template): `docs/sprint_m_plan.md`.
- Domain contract for cost: `src/aiflow/contracts/cost_attribution.py`.
- Policy config: `src/aiflow/policy/__init__.py:95` (`cost_cap_usd`).
