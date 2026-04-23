# Sprint N (v1.4.10) — LLM Cost Guardrail + Per-Tenant Budget

> **Status:** ACTIVE — kickoff S120 on 2026-04-26.
> **Branch:** `feature/v1.4.10-cost-guardrail-budget`.
> **Full plan:** `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md`.
> **Inventory:** `docs/cost_surfaces_inventory.md`.
> **Predecessor:** v1.4.9 Sprint M DONE 2026-04-25 (Vault + self-hosted Langfuse).

## TL;DR

Sprint L shipped **reactive** cost caps (a run hits the cap mid-way and stops).
Sprint N ships **proactive** cost control:

1. **Pre-flight budget check** at pipeline / step / LLM-call boundary — refuse
   before work starts when projected cost > remaining budget.
2. **Per-tenant budget table** (`tenant_budgets`, Alembic 045) — editable from
   the admin UI. Sibling to the pre-existing team-scoped `teams.budget_monthly_usd`
   (not a replacement).
3. **LLM cost guardrail** at the model client boundary — structured refusal
   payload, not an exception.

Feature flag: `AIFLOW_COST_GUARDRAIL__ENABLED=false` by default.

## Sessions

| ID   | Scope                                                              | Alembic |
|------|--------------------------------------------------------------------|---------|
| S120 | Kickoff — inventory + plan doc (this file).                        | 0       |
| S121 | `tenant_budgets` + `TenantBudgetService` + CRUD endpoint.          | 1 (045) |
| S122 | Pre-flight guardrail + structured refusal.                         | 0       |
| S123 | Admin UI budget dashboard + alert thresholds.                      | 0       |
| S124 | Sprint close — PR, retro, tag `v1.4.10`.                           | 0       |

## STOP conditions (summary)

- Budget math drift > ±5% on fixture replay → halt S122.
- UI blocked on Redis for aggregation (must be DB-direct) → halt S123.
- LLM cost estimation p95 error > 30% on UC2+UC3 benchmark → halt S122.
- Sprint M PR #17 CLOSED without MERGE → invalidates base, hand back to user.

## Out of scope

External billing, refund automation, per-user budgets, over-draft soft quotas,
`teams.budget_monthly_usd` deprecation — explicitly deferred.

See full plan doc for rationale, rollback, and success metrics.
