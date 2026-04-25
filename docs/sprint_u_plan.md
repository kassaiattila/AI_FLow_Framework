# Sprint U (v1.5.4) — Operational hardening

> **Status:** ACTIVE — kickoff S152 on 2026-04-25.
> **Branch:** `feature/u-s{N}-*` (one branch per session → squash-merge to `main`).
> **Full plan:** `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md`.
> **Predecessor:** v1.5.3 Sprint T MERGED 2026-04-25 (PromptWorkflow consumer migration, tag `v1.5.3` queued).
> **Target tag (post-merge):** `v1.5.4`.

## TL;DR

Eight feature sprints (M / N / O / P / Q / R / S / T) each closed with a tail of operability follow-ups. Individually small, collectively meaningful: CI gates that would have caught regressions earlier, two parallel cost-recording paths begging for consolidation, prompt-workflow descriptors that cover only one of three personas, operator scripts with inconsistent flags, the `issue_date` extraction miss from Sprint Q. Sprint U is the **catch-up sprint** — zero new functional capability, zero customer-visible feature. The win is operability.

Two carry-forwards from the Sprint T close (PR #43) trigger this scope: the Sprint T retro logged ST-FU-2/3/4/5, and Sprint R's SR-FU-4/5/6 sat unaddressed for two sprints. The S152 kickoff triages 20+ carry-forward IDs into 4 execution sessions + close, with explicit deferral of infrastructure-tier work (Langfuse v3→v4, live Vault rotation, AppRole prod IaC) to Sprint V.

## 4 deliveries in 4 sessions

| ID   | Theme                                       | Headline wins | Gate threshold |
|------|---------------------------------------------|---------------|----------------|
| S153 | CI hookups + tooling fixes                  | OpenAPI drift CI step · weekly 4-combo matrix as GHA · `vite build` pre-commit · ruff-strips-imports fix · BGE-M3 weight cache as standard CI artifact | All existing CI green; 0 new red, 0 flake injection |
| S154 | Cost / Settings consolidation               | `CostSettings` umbrella class · `record_cost` ↔ `CostAttributionRepository` consolidation · per-step cost ceiling into `CostPreflightGuardrail.check_step()` · model-tier fallback ceilings as env-tunable | UC3 4/4 + UC1 ≥ 75% · invoice_number ≥ 90% + UC2 MRR@5 ≥ 0.55 unchanged (zero behaviour change refactor) |
| S155 | PromptWorkflow ergonomics + persona parity  | Expert + mentor `aszf_rag_chain_<role>` descriptors · live-stack Playwright for `/prompts/workflows` · Langfuse workflow listing surface | Baseline UC2 MRR@5 unchanged; expert/mentor flag-on **prompt-resolution** parity (deterministic, no LLM call) |
| S156 | Sprint Q polish + operator script parity    | `issue_date` prompt + post-extract validator · `make api`-time docling warmup · `_parse_date` ISO normalization · uniform `--output` flag on operator scripts | UC1 ≥ 75% / invoice_number ≥ 90% (CI) · operator-run `issue_date` ≥ 90% with no other-field regression |

S157 closes the sprint — retro + PR description + CLAUDE.md banner flip + tag `v1.5.4`.

## What stays unchanged

- `AIFLOW_PROMPT_WORKFLOWS__ENABLED` default **`false`**.
- `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` default **`""`** (empty).
- 0 Alembic migrations (head stays at 047).
- 0 new endpoints (196 — S155 Langfuse listing extends an existing route).
- 0 new admin UI pages (26).
- `EmailDetailResponse.extracted_fields` Pydantic schema byte-identical (Sprint Q S136 contract preserved; S156 `_parse_date` normalization is a value-shape fix, not a schema change).
- Old env names (`AIFLOW_BUDGET__*`, `AIFLOW_COST_GUARDRAIL__*`) keep working for one minor version via Pydantic `validation_alias` (S154).
- `aszf_rag_chat` baseline persona path unchanged on flag-off (S155 only adds the new descriptors; the resolver carve-out from S150 is preserved).

## Carry-forward (not Sprint U scope, deferred to Sprint V)

- **`SM-FU-langfuse`** — Langfuse v3→v4 server migration. Server migration; needs runbook + staging.
- **`SM-FU-rotation`** — live Vault rotation E2E. Infrastructure-tier; needs staging Vault.
- **`SM-FU-prod`** — `AIFLOW_ENV=prod` root-token guard + AppRole prod IaC.
- **`SS-FU-1` / `SS-FU-5`** — `customer` → `tenant_id` model rename. Wide cross-call surface; separate refactor sprint per Sprint S close.
- **`SS-SKIP-2` / `ST-SKIP-1`** — Profile B Azure OpenAI live MRR@5. Azure billable credit pending.
- **`SQ-FU-3`** — UC1 corpus extension to 25 fixtures. Operator-curation work; defer if S156 full.
- **`SN-FU-Grafana`** — `cost_guardrail_refused` vs `cost_cap_breached` Grafana panel. Batch with Langfuse v4 in Sprint V.
- **`SP-FU-3`** — UC3 `024_complaint_about_invoice` body-vs-attachment conflict. Needs UI escalation surface, not classifier fix.
- **Cost-aware routing escalation** — Candidate A from S152 triage (`PolicyEngine.pick_model_tier()`, pipeline-level cumulative budget tracker). Sprint V or later.

## Operator activation

Sprint U deliverables are **default-on** for the cohorts that don't have a tenant blast radius:
- S153 CI gates / hooks fire automatically on the `main` branch + pre-commit.
- S154 cost-settings consolidation is a refactor with a backward-compat env-alias shim — no operator action required; old env names keep working.
- S156 `issue_date` fix + `_parse_date` normalization land on the existing extraction path; flag-off-path is the existing path with a better prompt.

The single **opt-in** cohort is **S155 expert / mentor persona descriptors**, which gate behind:
```
AIFLOW_PROMPT_WORKFLOWS__ENABLED=true
AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV="email_intent_processor,invoice_processor,aszf_rag_chat"
```
With both flags on, the resolver returns the expert/mentor descriptor when the persona matches; with either flag off (or `aszf_rag_chat` absent from the CSV), the legacy direct-prompt path runs unchanged.

## STOP conditions (recap)

- Any per-session golden-path threshold failed → halt + escalate.
- Flag-off smoke regression on UC3 4/4 / UC1 / UC2 baselines → halt; revert.
- `alembic upgrade head` ≠ 047 at any session start → drift outside Sprint U; investigate.
- Env-alias shim raises `AmbiguousEnvAlias` on a real deployment → halt; sequence the rollout.
- `issue_date` fix regresses an already-correct field on the 10-fixture corpus → halt; validator too aggressive.
- Operator declines mid-sprint → reschedule to Sprint V.

See `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` for the full plan, gate matrix, risk register, and skipped-items tracker.
