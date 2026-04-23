# Sprint N — Retrospective (v1.4.10 LLM cost guardrail + per-tenant budget)

> **Sprint window:** 2026-04-26 → 2026-04-28 (5 sessions, S120 → S124)
> **Branch:** `feature/v1.4.10-cost-guardrail-budget` (cut from `feature/v1.4.9-vault-langfuse` tip `d3e2d4a` while Sprint M PR #17 stayed OPEN, MERGEABLE)
> **Tag:** `v1.4.10` — queued for post-merge on `main`
> **PR:** opened at S124 against `main`, queued behind Sprint M PR #17 — see `docs/sprint_n_pr_description.md`
> **Predecessor:** `v1.4.9` (Sprint M Vault + self-hosted Langfuse, DONE 2026-04-25, PR #17 OPEN)
> **Plan reference:** `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` + `docs/sprint_n_plan.md` + `docs/cost_surfaces_inventory.md`

## Scope delivered

Per-tenant cost budgets are now a first-class domain (DB + service + API +
admin UI), and a pre-flight guardrail can refuse pipeline, RAG, and direct
LLM-client calls whose projected cost exceeds the tenant's remaining budget.
Everything ships flag-gated (`AIFLOW_COST_GUARDRAIL__ENABLED=false`) with a
dry-run default (`__DRY_RUN=true`) so a merge is a no-op for existing deploys.
Sprint L's reactive cap (`PolicyEngine.enforce_cost_cap` → HTTP 429) stays in
place as the second gate.

| Session | Commit | Deliverable |
|---|---|---|
| **S120** | `89e8c7a` | Kickoff: branch cut + `docs/cost_surfaces_inventory.md` (5 recorder / 2 cap-check / 4 aggregation / 2 config / **0 pre-flight** — the GAP) + `01_PLAN/111_SPRINT_N_COST_GUARDRAIL_BUDGET_PLAN.md` + `docs/sprint_n_plan.md` + CLAUDE.md banner. |
| **S121** | `483bd86` | Alembic 045 `tenant_budgets` (UUID PK, `(tenant_id, period)` unique, `limit_usd >= 0`, period ∈ {daily, monthly}, `alert_threshold_pct int[]`, `enabled`, timestamps); `TenantBudgetService` (`get` / `list` / `upsert` / `delete` / `get_remaining`) under `src/aiflow/services/tenant_budgets/`; `/api/v1/tenants/{tenant_id}/budget[/{period}]` router (list / get / upsert / delete), each read pairs the persisted `TenantBudget` with the live `BudgetView`. +16 unit + 2 Alembic integration + 3 API integration. Baseline 2073 → 2089. |
| **S122** | `8541857` | `src/aiflow/guardrails/cost_estimator.py` (wraps `litellm.cost_per_token` + per-tier fallback for missing models) + `src/aiflow/guardrails/cost_preflight.py` (`CostPreflightGuardrail` + `PreflightDecision` + `PreflightReason` enum); new `CostGuardrailRefused` error (`core/errors.py`) carrying `{refused, tenant_id, projected_usd, remaining_usd, period, reason, dry_run}`; `api/app.py` handler maps it to HTTP 429 (mirrors `CostCapBreached`); three wiring points — `pipeline/runner.py` pre-flight at pipeline entry (step-count scaled), `services/rag_engine/service.py` (above the existing S112 reactive cap), `models/client.py` LLM-client backstop via optional `tenant_id` kwarg (internal calls with no tenant are never gated); `CostGuardrailSettings` on `AIFlowSettings` (`enabled=false`, `dry_run=true`, per-tier ceiling map). +24 unit + 3 integration. Baseline 2089 → 2113. |
| **S123** | `f39309d` | `aiflow-admin/src/pages-new/BudgetManagement/` — `index.tsx` (tenant input + deep-link via `?tenant=`, daily + monthly `BudgetCard` side-by-side) + `BudgetCard.tsx` (live projection, threshold-aware progress bar, over-threshold chip row, editor form with Save disabled until diff) + `ThresholdEditor.tsx` (React Aria chip input: Enter/comma adds, backspace removes, blur commits, dedup + sort, aria-describedby errors) + `types.ts` (mirrors `aiflow.services.tenant_budgets.contracts`); `journeys/budget_management.md`; new `/budget-management` route + `aiflow.menu.budgets` nav item (Monitoring group); EN + HU locale strings; 2 Python Playwright E2E (`tests/e2e/test_budget_management.py`: render round-trip + threshold edit + hard-reload regression); `/live-test` report at `tests/ui-live/budget-management.md`. No backend surface added, no Alembic. |
| **S124** | _(this commit)_ | Sprint close — `docs/sprint_n_retro.md`, `docs/sprint_n_pr_description.md`, CLAUDE.md numbers + Sprint N DONE block (Sprint M DONE block preserved), PR cut against `main` with the Sprint M PR #17 dependency noted in the body. Tag `v1.4.10` queued (post-merge). |

## Test deltas

| Suite | Before (Sprint M tip = v1.4.9 candidate) | After (S123 tip) | Delta |
|---|---|---|---|
| Unit | 2073 | **2113** | **+40** (16 tenant_budgets S121 + 24 guardrail S122 + 0 UI-only S123) |
| Integration | 88+ | **~96** | **+8** (2 Alembic 045 upgrade/round-trip + 3 API CRUD + 3 cost_preflight_guardrail scenarios) |
| E2E collected | 422 | **424** | **+2** (S123 `test_budget_management.py`: render + edit round-trip) |
| Alembic head | 044 | **045** | **+1** (S121 `tenant_budgets`) |
| API endpoints | 189 | **190** (29 routers) | **+1** router surface (`/api/v1/tenants/{id}/budget[/{period}]`). List/get/put/delete are counted under the single tenant-budgets router, matching the S112 router-level convention CLAUDE.md uses. |
| UI pages | 23 | **24** | **+1** (`/budget-management`) |
| Ruff / OpenAPI | clean | clean | 0 new ruff errors; OpenAPI drift is bounded to the new `tenant-budgets` tag. |

`/live-test` report: `tests/ui-live/budget-management.md` — PASS on the
golden path + edit round-trip + reload persistence against real FastAPI +
PostgreSQL (documents the stale-API-process gotcha below).

## Contracts + architecture delivered

- **`tenant_budgets` (Alembic 045 — S121)** — additive table, UUID PK,
  `UNIQUE(tenant_id, period)`, `CHECK period IN ('daily','monthly')`,
  `CHECK limit_usd >= 0`, `alert_threshold_pct integer[]`, `enabled bool`,
  `created_at / updated_at`. Sibling to `teams.budget_monthly_usd` — the
  inventory explicitly keeps the team-scoped monthly column as-is (different
  cardinality, different period semantics; deprecation is a separate sprint).
- **`TenantBudgetService` (S121)** — async `get` / `list` / `upsert` /
  `delete`; `get_remaining(tenant_id, period)` subtracts
  `CostAttributionRepository.aggregate_running_cost` over the period window
  (24h daily, 720h monthly) and returns a `BudgetView` with
  `{tenant_id, period, limit_usd, used_usd, remaining_usd, usage_pct,
  over_thresholds}` — `over_thresholds` sorted ascending for stable UI
  rendering.
- **`TenantBudgetUpsertRequest` (S121)** — `alert_threshold_pct` validator
  rejects values outside `[1, 100]` and dedups + sorts on write; path
  params (`tenant_id`, `period`) are immutable — the PUT body carries only
  `limit_usd` / `alert_threshold_pct` / `enabled`. `Annotated[..., Path(...)]`
  aliases pin the validators in one place (ruff B008 clean).
- **`CostEstimator` (S122)** — wraps `litellm.cost_per_token(model, ...)` with
  a per-tier fallback when litellm's pricing table lacks the model
  (premium/standard/cheap/tiny → fixed per-1k-token ceilings). Pipeline
  pre-flight scales by projected step count; LLM-client pre-flight estimates
  off token counts that the client already has.
- **`CostPreflightGuardrail` + `PreflightDecision` (S122)** — pure module:
  returns `{allowed, projected_usd, remaining_usd, reason}` with
  `reason ∈ {disabled, no_budget, under_budget, over_budget,
  dry_run_over_budget}`. The **caller** raises `CostGuardrailRefused` on
  `allowed=False` — keeps the module test-friendly, lets each wiring site
  shape its own logging/retry.
- **`CostGuardrailRefused` (S122)** — new `PermanentError`, HTTP 429
  (mirrors `CostCapBreached`), `details` payload is the structured refusal
  shape consumed by the admin UI and by clients.
- **`CostGuardrailSettings` (S122)** — nested pydantic-settings on
  `AIFlowSettings` (env prefix `AIFLOW_COST_GUARDRAIL__`): `enabled=false`,
  `dry_run=true`, per-tier fallback ceilings, window-picker knob. Flag-off
  is identical to Sprint M tip.
- **Admin UI `/budget-management` (S123)** — read-only projection + write
  form on the same card; the `ThresholdEditor` chip pattern is transplantable
  to any future 1..100 integer-list editor (owner expressed interest in
  reusing it for SLA configurators).

## Key numbers (Sprint N tip)

```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2113 unit PASS / 1 skip / 1 xpass (resilience quarantine, unchanged since Sprint L)
~96 integration PASS (incl. 2 Alembic 045 + 3 tenant_budgets API + 3 cost_preflight_guardrail + Sprint M's 14 live-Vault/resolver)
424 E2E collected (+2 S123 budget-management)
0 ruff error | 0 TSC error | OpenAPI drift bounded to /api/v1/tenants/{id}/budget[/{period}]
Branch: feature/v1.4.10-cost-guardrail-budget (HEAD 751107d, 9 commits ahead of Sprint M tip)
Flag defaults on merge: AIFLOW_COST_GUARDRAIL__ENABLED=false / __DRY_RUN=true
```

## What worked

- **Flag-gated ship with `dry_run=true` default (S122).** The three rollout
  states — flag-off (no-op), flag-on + dry-run (log-only), flag-on + enforced
  (refuse) — compose as a clean ladder. An operator can enable the guardrail
  per tenant, watch the `cost.preflight.dry_run_over_budget` structlog event,
  and only then flip `dry_run=false`. No big-bang enforcement.
- **`CostPreflightGuardrail` returns a decision, the caller raises.** Keeping
  the module pure meant the unit tests don't fiddle with exception plumbing
  and each of the three wiring sites (`pipeline/runner.py`,
  `rag_engine/service.py`, `models/client.py`) could shape its own logging
  and retry semantics. The LLM-client backstop only gates when a caller
  passes `tenant_id=`; every internal / maintenance call is by construction
  exempt.
- **Sibling `tenant_budgets` table, not replacement of
  `teams.budget_monthly_usd` (S121).** The inventory called this out loud:
  tenants ≠ teams under the v2 contract. Keeping both lets the v1 team-monthly
  view stay readable while the new tenant-scoped window drives Sprint N. A
  unification (or deprecation) is a separate sprint — documented in the
  plan's §6 "out of scope".
- **S120 inventory before any code (plan §2).** `docs/cost_surfaces_inventory.md`
  caught two silent assumptions before they could burn time:
  `AIFLOW_MAX_DAILY_COST_USD` does **not** exist (grep 0 hits), and
  `CostAttributionRepository` duplicates `record_cost`'s write path
  (flagged as a soft follow-up, not expanded).
- **Single admin page, chip editor, Save-disabled-until-diff (S123).** The
  UI was scoped to one page deliberately — owner confirmed "don't split into
  a list view + an editor view" at S123 kickoff. Result: one round-trip per
  save, no optimistic-only state, hard-reload passes the same assertions.
- **`/live-test` regression: hard reload asserts the same DOM.** The
  Playwright E2E explicitly reloads the page after save and re-asserts the
  threshold chips — caught the classic optimistic-update bug class at spec
  level, not after the fact.
- **Annotated path validators (S121).** `TenantIdPath = Annotated[str,
  Path(min_length=1, max_length=255)]` is reused across the four handlers.
  One line, four enforcement points, ruff B008 quiet.

## What surprised us

- **Stale uvicorn process on port 8102 held the v1.4.4 OpenAPI.** During
  S123 `/live-test`, the initial seed PUT 404'd because the running uvicorn
  had been started at Sprint L tip and never reloaded the
  S121 `tenant_budgets` router. Fix:
  `python -m uvicorn aiflow.api.app:create_app --factory --port 8102`. The
  tests/ui-live report documents this — promoted here because it's the kind
  of operator footgun that recurs.
- **litellm pricing table has gaps.** `litellm.cost_per_token` returns
  `None` for several models we nominally support (`openai/o3-mini-2025-*`,
  some Anthropic Haiku variants) because the table isn't updated every
  release. Fallback tier ceilings in `CostEstimator` cover this, but there
  is a follow-up: audit the full model catalog on every litellm upgrade and
  add a CI warn when a model is listed in policy but missing from pricing.
- **The S122 wiring at `rag_engine/service.py:559` **above** the existing
  reactive cap means two gates fire on a truly over-budget query** — pre-flight
  refuses first; if the flag is off, the reactive cap still triggers. That's
  the designed behaviour (pre-flight is additive), but it means observability
  needs to distinguish `cost_guardrail_refused` from `cost_cap_breached` on
  the dashboard. Documented in the admin UI, not yet surfaced as a metric
  panel — carried.
- **`AIFlowSettings` now has two cost-related nested classes** — Sprint L's
  `BudgetSettings` + Sprint N's `CostGuardrailSettings`. Cleanliness win
  would be a single `CostSettings` umbrella, but not worth a rename mid-PR.
  Carried.
- **React Aria chip editor needs `aria-describedby` for inline errors.** The
  first S123 pass put validation error text below the input without the ARIA
  link; screenreader users would miss it. Fixed in `ThresholdEditor.tsx`
  before the /live-test run — added `aria-describedby="threshold-error"` on
  the input, kept the chip commit logic unchanged.

## What we'd change

- **Consolidate `CostAttributionRepository.insert_attribution` +
  `cost_recorder.record_cost`.** Both write to `cost_records`; the former is
  the v2 contract path, the latter is the legacy best-effort path. Nothing in
  Sprint N expanded the duplication (soft STOP condition in plan §5b), but
  they should merge before the next cost-touching sprint.
- **Model-tier fallback defaults live in code, not config.** `CostEstimator`
  hard-codes `{premium: 0.01, standard: 0.003, cheap: 0.0005, tiny: 0.0001}`
  per-1k-token ceilings. Moving to `CostGuardrailSettings` would let
  operators tune without a rebuild; pushed to a follow-up.
- **`/live-test` regression guard — the stale-uvicorn catch belongs in
  `/status`.** If `/status` pinged `/openapi.json` and diffed the
  tag set against a known baseline, S123's gotcha would have surfaced at
  session start instead of mid-journey.
- **Add a Grafana panel for `cost_guardrail_refused` vs
  `cost_cap_breached`.** Today both land in structlog; a single dashboard
  panel would make the two-gate distinction visible to SREs without
  grepping logs.

## Decisions log

| # | Decision | Alternative considered | Rationale |
|---|---|---|---|
| SN-1 | **`tenant_budgets` sibling table, not extending `teams.budget_monthly_usd`.** | Add a `period` column + tenant_id to the existing table. | Tenants ≠ teams in v2. Different cardinality, different periods. Extending would bloat a team-scoped table with tenant-scoped rows and couple the v1 monthly view to Sprint N's semantics. Sibling is cheap, reversible, and keeps the v1 view untouched. |
| SN-2 | **`CostPreflightGuardrail` returns a decision; caller raises.** | Have the guardrail raise `CostGuardrailRefused` directly. | Keeps the module pure (unit tests don't mock exceptions) and lets each wiring site shape retry / logging / metric semantics. Cleanest separation of "policy" from "transport". |
| SN-3 | **Flag-gated + dry-run default (`ENABLED=false`, `DRY_RUN=true`).** | Ship enabled + enforced at merge. | A pre-flight refusal is a user-visible 429. Staging operators deserve a soak window where dry-run logs the projected refusals without actually refusing. Flag-off regression is identical to Sprint M tip. |
| SN-4 | **LLM-client backstop only gates when `tenant_id=` is passed.** | Gate every `client.generate()` call unconditionally. | Internal / maintenance / bootstrap calls do not carry a tenant; failing those on "no budget" would break startup. The backstop opts in explicitly — callers who want the guard pass `tenant_id`; everyone else sees no behaviour change. |
| SN-5 | **Per-tier fallback ceilings for litellm pricing gaps.** | Hard-fail on missing pricing (raise). | A missing pricing entry is a litellm lag, not an operator error. Failing the call on it would make the guardrail more fragile than the reactive cap. Tier fallback errs on the side of over-projecting cost (the guardrail is then pessimistic, which is the right side to err on). |
| SN-6 | **One admin page, not list + detail.** | Separate `/budgets` list + `/budgets/:tenant/:period` editor. | Tenant count in practice is 1–20 per deploy; card grid on one page is readable at that scale. List+detail would add an extra click and orphan the daily/monthly pair visually. Revisit at ≥50 tenants per deploy. |
| SN-7 | **Chip editor with dedup + sort on every mutation.** | Preserve insertion order and let the server sort. | ARIA live regions + keyboard repeat on backspace interact badly with insertion order. Dedup + sort is O(n log n) on a list capped at ~10 thresholds; the UX feedback ("the chips always line up") is worth the lost ordering affordance. |

## Follow-up issues (filed into Sprint N+1 backlog)

1. **`CostAttributionRepository` ↔ `cost_recorder.record_cost` consolidation.** Two write paths to `cost_records`; Sprint N did not expand the duplication but it's two things to keep in sync during the next schema change. Soft STOP hit in plan §5b #1.
2. **Model-tier fallback ceilings → `CostGuardrailSettings`.** Hard-coded today; operator tuning requires a rebuild.
3. **Grafana panel for `cost_guardrail_refused` vs `cost_cap_breached`.** Two-gate distinction is invisible to SREs today.
4. **litellm pricing coverage audit on every upgrade.** CI step that warns when a policy-referenced model has no `litellm.cost_per_token` entry.
5. **`/status` command should fetch `/openapi.json` and diff tags.** Would catch the stale-uvicorn class of bug at session start.
6. **`CostSettings` umbrella class.** Consolidate `BudgetSettings` (Sprint L) + `CostGuardrailSettings` (Sprint N). Rename only; no behavioural change.
7. **Soft-quota / over-draft semantics.** Out-of-scope per plan §6; remains a customer ask for a future sprint.
8. **Budget seeding script for demos.** `scripts/seed_vault_dev.py` has a mirror pattern; a `scripts/seed_tenant_budgets_dev.py` would smooth onboarding.
9. **eval/promptfoo blanket bypass flag — NOT added (by design).** Every request goes through the guardrail when enabled; if a specific eval harness needs to bypass, it should pass `tenant_id=None` at the LLM-client boundary (already the exempt path). Documented here so the next sprint doesn't re-litigate.

**Carried from earlier sprints (unchanged, still open):**

10. **Sprint M carry** — live Vault token rotation E2E, `AIFLOW_ENV=prod` root-token guard, `make langfuse-bootstrap`, AppRole prod IaC, Langfuse v3→v4 self-host migration, `SecretProvider` slot on `ProviderRegistry`.
11. **Sprint J carry** — BGE-M3 weight cache as CI artifact, Azure OpenAI Profile B live (credits pending), resilience `Clock` seam (deadline 2026-04-30 — still xfails), coverage uplift (issue #7).
12. **Sprint L carry** — `/live-test` Playwright `--network=none` variant (air-gap E2E already covers the DNS-level equivalent).

## Process notes

- **Auto-sprint ran clean S120 → S123.** Each session closed with
  `/session-close`, NEXT.md regenerated, next session fired on the
  `ScheduleWakeup ~90s` loop. S124 (this session) is the manual sprint
  close — same pattern as Sprint M S119.
- **Sprint M PR #17 stayed OPEN the entire sprint.** The branch was cut from
  Sprint M tip intentionally; the Sprint N PR notes the dependency in its
  body ("rebase onto `main` after #17 merges") rather than blocking on a
  Sprint M merge that wasn't in the critical path for this work.
- **Plan exit gates, per plan §8:**
  - Pre-flight refuses on near-zero budget with `{refused: true,
    reason, projected_usd, remaining_usd}` — covered by S122's
    `test_cost_preflight_guardrail.py::test_over_budget_enforced`.
  - Admin UI surfaces tenant budget, thresholds editable, changes persist
    — covered by S123's `test_budget_management.py::test_edit_round_trip`.
  - No regression in Sprint L reactive cap — S112
    `test_cost_cap_enforcement.py` stays green.
  - Estimation accuracy — benchmark fixture TBD; the closest proxy is the
    unit table in `test_cost_estimator.py`. Full benchmark deferred (the
    `|projected - actual| / actual <= 0.30` at p95 target needs a replay
    harness we don't have today; filed as follow-up under #4 above).
  - Baseline unit count 2073 → ≥ 2110: **actual 2113**, target met.
- **No production secrets, no DSN, no API keys in the retro or PR body.** `.env*`
  patterns unchanged; `config/policies/` still gitignored from Sprint M.
