# AIFlow v1.4.10 Sprint N — Session 120 Prompt (Kickoff: LLM cost guardrail + per-tenant budget)

> **Datum:** 2026-04-26
> **Branch:** `feature/v1.4.10-cost-guardrail-budget` (cut from `main` AFTER Sprint M PR #17 merges; fallback: cut from `50a9428` on `feature/v1.4.9-vault-langfuse` if PR stays open)
> **HEAD (parent):** `50a9428` (docs(sprint-m): S119 close — Sprint M retro + vault rotation runbook + PR description)
> **Port:** API 8102 | UI 5173 | Vault dev 8210 | Langfuse dev 3000
> **Elozo session:** S119 — Sprint M closed; PR #17 opened against `main` (state: OPEN, MERGEABLE); tag `v1.4.9` queued post-merge. 2073 unit / 88+ integration / 422 e2e (baseline).
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §5 (Sprint L cost enforcement recap) + §7 (test strategy) — this kickoff writes `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` + `docs/sprint_n_plan.md`.
> **Session tipus:** KICKOFF — branch cut, discovery, inventory, plan doc (no production code change).

---

## KONTEXTUS

### Honnan jottunk (Sprint M tip)
- **v1.4.9 Sprint M DONE 2026-04-25** — Vault hvac + self-hosted Langfuse + air-gap Profile A. PR #17 open against `main`; tag `v1.4.9` queued post-merge.
- Every HIGH/MEDIUM secret flows through the resolver chain `cache → Vault → env → default`.
- Self-hosted Langfuse v3 + dedicated Postgres 16 overlay (ports 3000 / 5434), bootstrap script, air-gap E2E harness.

### Hova tartunk (Sprint N — cost guardrail + per-tenant budget)
Sprint L (v1.4.8) landed cost **cap enforcement** (`cost_records.workflow_run_id` null-able for tenant-level aggregation, `costs.cap_status` endpoint in S112). That was reactive — a run bumps against a cap and stops. Sprint N takes it **proactive**:

1. **Pre-flight budget check** — a pipeline/step refuses to start if the tenant's projected remaining budget is below the estimated cost for this run.
2. **Per-tenant budget rollout** — budgets are configurable per tenant (currently a global `AIFLOW_MAX_DAILY_COST_USD`), surfaced in admin UI, alertable before hitting the hard cap.
3. **LLM cost guardrail** — a pre-call guardrail that refuses individual LLM calls projected to exceed a per-step or per-tenant ceiling, with a structured refusal reason (not an exception).

### Jelenlegi allapot
```
27 service | 189 endpoint | 50 DB table | 44 Alembic migration (head: 044)
2073 unit | 422 e2e | 88+ integration | 8 skill | 23 UI page
hvac 2.4.0 | langfuse 4.3.1 | PR #17 OPEN, MERGEABLE
Sprint M follow-ups carried: live rotation E2E, AIFLOW_ENV=prod root-token guard,
  make langfuse-bootstrap target, AppRole prod IaC, Clock seam (deadline 2026-04-30),
  BGE-M3 weight CI artifact, Azure OpenAI Profile B live (credits pending).
```

---

## ELOFELTETELEK

```bash
git branch --show-current                         # feature/v1.4.9-vault-langfuse (expected before merge)
git log --oneline -3                              # HEAD 50a9428
gh pr view 17 --json state,mergeable              # confirm OPEN, MERGEABLE
.venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2073 pass baseline
```

---

## FELADATOK

### LEPES 1 — Branch cut decision (~5 min)

```bash
# Ideal: Sprint M merged
gh pr view 17 --json state | grep MERGED && {
  git fetch origin
  git checkout main
  git pull
  git tag v1.4.9 -a -m "Sprint M: Vault hvac + self-hosted Langfuse + air-gap Profile A"
  git push origin v1.4.9
  git checkout -b feature/v1.4.10-cost-guardrail-budget
}
# Fallback: Sprint M still open — cut from the Sprint M tip; rebase onto main once PR #17 merges.
gh pr view 17 --json state | grep OPEN && {
  git checkout -b feature/v1.4.10-cost-guardrail-budget feature/v1.4.9-vault-langfuse
  echo "NOTE: branch cut from feature/v1.4.9-vault-langfuse tip; rebase onto main once PR #17 merges."
}
```

### LEPES 2 — Cost-surface inventory (~30 min)

Produce `docs/cost_surfaces_inventory.md` — every place in `src/aiflow/` that records or checks cost. Use `rg` to sweep:

```bash
rg -n 'cost|budget|cap|CostRecord|CostService|cost_records' src/aiflow/ --type py | head -200
rg -n 'AIFLOW_MAX_DAILY_COST_USD|AIFLOW_COST_' src/aiflow/ --type py
rg -n '@track_cost|record_cost|emit_cost' src/aiflow/ --type py
```

For each hit, classify:
- **Recorder** (writes `cost_records` row) — where cost is captured post-hoc.
- **Cap check** (reactive) — Sprint L S112 `costs.cap_status` semantics.
- **Pre-flight** (NEW in Sprint N) — places we need to add a budget check before work starts.

### LEPES 3 — Plan doc + session queue (~40 min)

Write `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` (mirror `docs/sprint_m_plan.md` structure):

1. **Why this sprint** — Sprint L was reactive; UC2/UC3 hosting costs climbing; customers asked for per-tenant budgets on last feedback cycle.
2. **Discovery outcome** — inventory from Step 2, pre-existing DB shape (`cost_records` table), what's missing.
3. **Session queue (locked)** — S120 kickoff, S121 `tenant_budgets` Alembic 045 + `TenantBudgetService`, S122 pre-flight guardrail at step + pipeline boundary, S123 UI surface (budget dashboard + alert thresholds), S124 Sprint N close (PR + retro + tag `v1.4.10`).
4. **Dependencies + blockers** — `cost_records.workflow_run_id` null-ability (Sprint L S112) already in place; `TenantService` needed for tenant scoping.
5. **STOP conditions (hard)** — budget math drift (sum of `cost_records` != projected), UI can't render real-time if Redis down, LLM cost estimation prediction error > 30% (needs a fallback).
6. **Out of scope** — external billing integration (Stripe etc.), refund automation, per-user (not per-tenant) budgets.
7. **Rollback plan** — each session standalone commit; S121 migration is additive (new table); S122 guardrail behind `AIFLOW_COST_GUARDRAIL__ENABLED=false` default.
8. **Success metric** — tenant-scoped budget visible in admin UI; a pipeline run against a near-zero budget refuses at pre-flight with structured reason; no regression in Sprint L's existing cap behaviour.

Also write a short `docs/sprint_n_plan.md` summary pointing at the full plan doc.

### LEPES 4 — CLAUDE.md kickoff banner (~10 min)

In the Overview block, add:
```
v1.4.10 Sprint N — LLM cost guardrail + per-tenant budget (S120 kickoff on
`feature/v1.4.10-cost-guardrail-budget`). Predecessor: v1.4.9 Sprint M DONE 2026-04-25.
```

Do **not** touch Key Numbers yet (kickoff ships no code).

### LEPES 5 — Validacio + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ scripts/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/ scripts/
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
git add 01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md docs/sprint_n_plan.md docs/cost_surfaces_inventory.md CLAUDE.md
git commit -m "chore(sprint-n): S120 kickoff — cost guardrail + per-tenant budget plan + inventory"
/session-close S120
```

---

## STOP FELTETELEK

**HARD (hand back to user):**
1. `gh pr view 17` returns `state=CLOSED` without `MERGED` — Sprint M was rejected; Sprint N plan needs revision before branch cut.
2. Cost-surface inventory surfaces a budget table that already exists (`tenant_budgets` is a pre-existing abstraction) — plan may already be half-done; user decides scope.
3. Sprint L `cost_records.workflow_run_id` null-ability not present on `main` (sanity check after merge) — block until reconciled.

**SOFT (proceed with note):**
1. PR #17 still open at branch-cut time — fall back to cutting from `feature/v1.4.9-vault-langfuse`; flag the rebase-onto-main TODO in the plan doc.
2. `docs/cost_surfaces_inventory.md` uncovers more surfaces than expected (>8) — note scope risk in the plan, propose splitting S122 into 2 sessions.

---

## NYITOTT (cross-sprint)

- **Sprint M follow-ups** (carried from retro §Follow-up issues): live rotation E2E, AIFLOW_ENV=prod root-token guard, `make langfuse-bootstrap` target, AppRole prod IaC example.
- **Resilience `Clock` seam** — deadline 2026-04-30, quarantined `test_circuit_opens_on_failures` still xfails.
- **BGE-M3 weight cache as CI artifact** (carried from Sprint J + Sprint M).
- **Azure OpenAI Profile B live** (credits pending).
- **`query()` provider-registry refactor** — Sprint J S105 follow-up, still outstanding.

---

## SESSION VEGEN

```
/session-close S120
```

Utana: `/clear` -> `/next` -> S121 (Alembic 045 + `TenantBudgetService`).
