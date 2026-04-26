# Sprint U — Retrospective (v1.5.4 Operational hardening + carry-forward catch-up)

> **Sprint window:** 2026-04-25 → 2026-04-26 (5 PRs landed in 2 calendar days; 6 sessions: S152 kickoff, S153, S154, S155, S156, S157 close).
> **Branch:** `feature/u-s157-sprint-u-close` (cut from `main` @ `f5c0234`, S156 squash-merge)
> **Tag:** `v1.5.4` — queued for post-merge on `main`
> **PR:** opened at S157 against `main` — see `docs/sprint_u_pr_description.md`
> **Predecessor:** `v1.5.3` (Sprint T — PromptWorkflow per-skill consumer migration, MERGED `fd2a8bc`)
> **Plan reference:** `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` + audit `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`

## Headline

Sprint U is the **carry-forward catch-up sprint** the project owed itself after eight feature sprints (M / N / O / P / Q / R / S / T). Each retro left a tail of operability follow-ups that individually didn't justify a sprint slot but collectively formed real debt. Sprint U paid down that debt across **5 execution sessions + close**, all with zero new functional capability and zero customer-visible feature change. The win is operability: faster CI signal, fewer footguns in the cost/settings surface, parity across PromptWorkflow personas, cleaner operator ergonomics, and the first `issue_date` accuracy fix the Sprint Q corpus has carried since its 2026-04-04 close.

```
S152:  Sprint U kickoff plan + carry-forward triage              ← kickoff
S153:  CI hookups + tooling fixes (5 micro-wins)                 ← gates
S154:  Cost / Settings consolidation (4 wins)                    ← refactor
S155:  Expert + mentor persona PromptWorkflow descriptors        ← additive
S156:  Sprint Q polish (issue_date) + operator script parity     ← polish
S157:  retro + Sprint V kickoff plan publish + tag v1.5.4 prep   ← close
```

The audit `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` (added in PR #45) gave Sprint U its second purpose: **publish Sprint V's direction** while the carry-forward catch-up was still mid-flight. That direction — generalize `invoice_finder` into a parametrizable **document recognizer skill** with pluggable doc-type registry (5 initial types: `hu_invoice`, `hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`) — became the headline of the Sprint V kickoff plan published at S157 (`01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`).

## Scope by session

| Session | Commit on `main` | Deliverable |
|---|---|---|
| **S152** | `b0d430a` (PR #44) | Sprint U kickoff plan (`01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md`) + companion `docs/sprint_u_plan.md` + carry-forward triage. Operator picked Candidate B (operational hardening) at the S152 triage. 5-session plan: S153 CI gates, S154 cost consolidation, S155 PromptWorkflow ergonomics, S156 Sprint Q polish, S157 close. |
| **S153** | `4e63525` (PR #45) | **5 micro-wins:** OpenAPI drift CI step (`scripts/check_openapi_drift.py` → new `openapi-drift` job in `ci.yml`; **caught real drift on first run** — Sprint S S144 `/api/v1/rag-collections` paths missing from snapshot, refreshed in same commit) · weekly UC3 4-combo matrix as GHA (`scripts/measure_uc3_llm_context.py` + Mon 07:00 UTC cron + `OPENAI_API_KEY` skip-by-default fork-safe gate) · `vite build` pre-commit hook (`scripts/hooks/pre-commit` + `make install-hooks`) · `extend-unsafe-fixes = ["F401"]` in `pyproject.toml` (mid-Edit unused-import auto-removal mitigation, ST-FU-5) · BGE-M3 weight cache promoted from nightly to PR-time CI (new `integration-1024-dim` job) · **plus** the audit document `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` published as part of the same PR (S155 rescope decision + Sprint V direction). 0 new tests (these *are* gates). |
| **S154** | `fd69764` (PR #46) | **4 wins:** `CostSettings` umbrella class (`AIFLOW_COST__*` env prefix; legacy `AIFLOW_BUDGET__` + `AIFLOW_COST_GUARDRAIL__` continue to work via Pydantic alias chain) · `record_cost(...)` rewritten as a thin shim over `CostAttributionRepository.insert_attribution(...)` (single DB-write path; **inline `ALTER TABLE` DDL hack removed**) · `CostPreflightGuardrail.check_step(step_name, model, input_tokens, max_output_tokens, ceiling_usd)` per-step API + 4 new `PreflightReason` literals (Sprint T S149 invoice_processor pattern lifted into the framework guardrail; ST-FU-3) · `tier_fallback_in_per_1k` + `tier_fallback_out_per_1k` env-tunable JSON via `CostGuardrailSettings` (SN-FU-2). **+22 unit tests**. |
| **S155** | `97eb09b` (PR #47) | **Rescoped to ST-FU-2 only.** SR-FU-4 (live Playwright `/prompts/workflows`) and SR-FU-6 (Langfuse listing) deferred to Sprint V/W per the audit decision. 2 new PromptWorkflow descriptors (`prompts/workflows/aszf_rag_chain_expert.yaml` + `aszf_rag_chain_mentor.yaml`, mirror baseline 4-step DAG with `system_<role>` step pinned). `_PERSONA_WORKFLOW_MAP` + `_PERSONA_SYSTEM_STEP_MAP` in `skills/aszf_rag_chat/workflows/query.py` dispatches per-role; `generate_answer` now persona-aware (no longer hard-codes `system_baseline`). 4 existing S150 "expert/mentor always falls through" tests UPDATED + 4 new flag-OFF parity tests. Drive-by: `from typing import Any` import in `bpmn.py` (pre-existing F821 the S153 ruff change kept in scope). **+4 net unit (+8 new − 4 obsolete)**. |
| **S156** | `f5c0234` (PR #48) | **4 wins:** `issue_date` prompt + schema fix (SQ-FU-1: prompt now produces `issue_date`, model `Field(validation_alias=AliasChoices(...))`, dict normalization, SQL INSERT `issue_date OR invoice_date` fallback, `inv.header.invoice_date` `@property` for byte-stable callers; **no Alembic migration**) · `_parse_date_iso` ISO normalizer at JSON-payload boundary (SQ-FU-4; accepts ISO + European patterns + `date`/`datetime`; regex char-class bug fix `[./-]`) · `make api` docling warmup gate (`AIFLOW_DOCLING_WARMUP=true` env-controlled, default off so test runs don't pay; SQ-FU-2) · `argparse_output()` helper + `audit_cost_recording.py` migration to uniform `--output {text,json,jsonl}` (ST-FU-4; 4 remaining operator scripts tracked as ST-FU-4-followup). **+25 unit tests**. |
| **S157** | _(this commit)_ | Sprint close — `docs/sprint_u_retro.md`, `docs/sprint_u_pr_description.md`, `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` (Sprint V kickoff plan), CLAUDE.md numbers + Sprint U DONE banner, `session_prompts/NEXT.md` → SV-1 prompt, PR cut against `main`. Tag `v1.5.4` queued. |

## Test deltas

| Suite | Before (Sprint T tip) | After (S157 tip) | Delta |
|---|---|---|---|
| Unit | 2424 | **2475** | **+51** (0 S153 + 22 S154 + 4 net S155 + 25 S156 + 0 S157) |
| Integration | ~116 | **~116** | 0 (Sprint U did not touch integration coverage) |
| E2E collected | 432 | 432 | 0 (no UI surface change) |
| API endpoints | 196 | **196** | 0 (no new endpoints) |
| API routers | 31 | **31** | 0 |
| UI pages | 26 | **26** | 0 |
| Alembic head | 047 | **047** | 0 (no DB change) |
| PromptWorkflow descriptors on disk | 3 | **5** | **+2** (`aszf_rag_chain_expert`, `aszf_rag_chain_mentor`) |
| CI gates (`ci.yml`) | 2 | **4** | **+2** (`openapi-drift`, `integration-1024-dim`) |
| CI gates (`nightly-regression.yml`) | 4 | **5** | **+1** (`uc3-4combo-matrix` weekly) |
| Pre-commit hooks (project-managed) | 0 | **1** | **+1** (`scripts/hooks/pre-commit` vite build) |
| Settings classes | `BudgetSettings` + `CostGuardrailSettings` separate | **+ `CostSettings` umbrella** | additive |

## Decisions log

- **SU-1 — Audit-driven re-scope mid-sprint.** Between S152 kickoff and S155 execution, an audit (`01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`) was written that re-scoped S155 from "PromptWorkflow ergonomics + persona descriptors" to "ST-FU-2 expert/mentor only". SR-FU-4 (live Playwright) and SR-FU-6 (Langfuse listing) deferred to Sprint V/W where they sit naturally next to the doc-recognizer admin UI work. **Risk-down move** — kept S155 additive + low-risk; pulled the bigger items into a sprint that has the right context for them.
- **SU-2 — Sprint V direction published in Sprint U.** S157 publishes `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` rather than waiting for Sprint V kickoff. Operator instructed during S152 audit that the strategic redirection (`invoice_finder` → generic `document_recognizer` skill, support 5 doc-types: invoice / ID card / address card / passport / contract) should be captured *now* while context is fresh. Sprint V kickoff session can dive straight into SV-1 instead of re-deriving design.
- **SU-3 — Backward-compat shims preferred over hard renames.** Three places in S154 + S156 chose the shim path over a hard refactor: (a) `record_cost()` → `CostAttributionRepository.insert_attribution()` thin wrapper preserves all 6 call sites byte-stable; (b) `CostSettings` umbrella adds `AIFLOW_COST__*` while the legacy `AIFLOW_BUDGET__*` + `AIFLOW_COST_GUARDRAIL__*` env prefixes continue to work; (c) `InvoiceHeader.issue_date` is canonical with `validation_alias=AliasChoices("issue_date", "invoice_date")` + `invoice_date` `@property`. **Rule:** zero behavior change on flag-off. Hard refactors (deleting the shim, renaming the SQL column, dropping the legacy env names) are tracked as separate post-Sprint-V follow-ups.
- **SU-4 — Inline DDL hack deletion was the highest-impact line in S154.** `record_cost()` previously ran `ALTER TABLE cost_records ALTER COLUMN workflow_run_id DROP NOT NULL` on **every call** with `IF EXISTS` guards. The one-time migration had been applied long ago, so subsequent calls were no-ops, but each one still acquired a catalog lock. Dropping the inline DDL is invisible to operators but a real perf + correctness improvement.
- **SU-5 — `extend-unsafe-fixes = ["F401"]` is project policy now.** S153 added the ruff config tweak that prevents `--fix` from auto-removing unused imports mid-edit. Sprint T S150 spent ~10 min on this footgun; Sprint U S155's drive-by `bpmn.py` `from typing import Any` fix surfaced *because* of the new policy (the import was being stripped pre-policy and never noticed). **Cost: zero. Value: every multi-edit session avoids the trap.**
- **SU-6 — Pre-commit hooks ship as scripts, not framework state.** The vite-build hook lives in `scripts/hooks/pre-commit` and is installed by `make install-hooks` (no `husky/`). Two reasons: (a) keeps the project Python-managed (no Node-managed pre-commit); (b) hooks are scoped to the contributor's checkout, not enforced project-state. Operators who don't want it can skip the install step.
- **SU-7 — `make api` warmup gated by env, not always-on.** SQ-FU-2 originally read as "Promote docling warmup to make api time". The implementation gates the warmup behind `AIFLOW_DOCLING_WARMUP=true` (default off). Reason: test runs and quick dev iterations should not pay the ~60s cost. Production / demo sessions flip the env once. **Pattern carries:** other expensive warmups (BGE-M3 weights on first query) should follow the same env-gated pattern.

## What worked

- **One PR per session, all green.** 5 PRs (#44, #45, #46, #47, #48) merged across 2 calendar days. Each one was independently revertable. The audit document published in PR #45 set the rescope expectation early, so S155 came in narrower-than-planned without surprise.
- **OpenAPI drift gate caught a real bug on first run.** S153's new `openapi-drift` CI job found that Sprint S S144's `/api/v1/rag-collections` paths (3 paths + 1 tag + 4 schemas) had **never been captured** in `docs/api/openapi.json`. The same PR refreshed the snapshot. This is exactly the kind of stale-uvicorn drift the gate was designed to catch.
- **Test count grew through refactor.** Sprint U is a refactor sprint, but the test count climbed from 2424 to 2475 (+51 net). The refactors weren't "cleanup that drops tests" — each consolidation came with its own contract tests + backward-compat fixtures. The pre-commit hook (lint + 2475 unit, ~1.5min) stayed green for every session.
- **`AIFLOW_LANGFUSE__ENABLED=false` workaround documented in README.** The OneDrive-move regression session before Sprint U surfaced a Langfuse cloud teardown hang in TestClient lifespan. Sprint U's docs treat this as a known integration-test workaround. **No fix shipped** in Sprint U (would require a real `tracing.py` flush timeout) but the pattern is documented so contributors don't re-discover it.
- **Backward-compat shims are cheaper than they look.** All three S154/S156 shims (`record_cost`, `CostSettings` umbrella, `InvoiceHeader.issue_date` alias) cost ~5–15 LOC each and freed the next sprint to migrate consumers without time pressure. Shims with `--strict` audit scripts (e.g. `scripts/audit_cost_recording.py`) make the migration trackable.

## What hurt

- **Pre-existing scripts/ ruff issues blocked nothing but added noise.** S156's local sanity check ran ruff on `scripts/` (broader than the CI scope) and surfaced a long list of pre-existing F541/F401/I001/UP017 issues in 7 operator scripts. These didn't fail CI (gates run on `src/` + `tests/` only) but they create chatter when contributors lint locally with the broader scope. **Tracked as SU-FU-2** for a follow-up cleanup pass.
- **The S155 test refactor was bigger than planned.** S150's "expert/mentor always falls through" assertion was baked into 4 step-wiring tests across `test_workflow_migration.py`. S155's persona resolver change required updating all 4 tests + adding 4 flag-OFF parity counterparts. The session was still under budget, but the planning estimate (4-6 unit tests) under-counted the test-update cost. **Lesson:** when the resolver behavior changes, the wiring tests at every step need an audit, not just the resolver tests.
- **The `invoice_date` SQL column name didn't get renamed.** SQ-FU-1 left the DB column as `invoice_date` (no Alembic migration). The Python surface uses `issue_date` as canonical, but the DB column + `cost_records`-style raw SQL still have `invoice_date`. **Tracked as SU-FU-3** — Alembic migration `048_invoice_date_to_issue_date` queued for Sprint V (or post-V depending on doc-recognizer scope).
- **Sprint Q UC1 corpus extension to 25 (SQ-FU-3) deferred again.** Each new fixture is operator-curation work. Sprint U passed on this; Sprint V will likely carry it forward to a future operator-driven sprint slot.
- **No live re-measurement of UC1 `issue_date` accuracy in Sprint U.** S156 ships the prompt + schema fix, but the operator-script flag-on parity run on the full 10-fixture corpus (`scripts/measure_uc1_golden_path.py`) was not executed in Sprint U. The CI 3-fixture slice continues to run; the full 10-fixture run is queued as the first action in **Sprint V kickoff verification**.

## Open follow-ups (Sprint V or later)

| ID | Description | Target |
|---|---|---|
| **SU-FU-1** | Operator-script `--output` flag migration for the 4 remaining scripts (`measure_uc1_golden_path`, `run_nightly_rag_metrics`, `measure_uc3_*`, `bootstrap_*`) | Sprint V (during SV-5 close, parity work) |
| **SU-FU-2** | `scripts/` ruff cleanup (F541, F401, I001, UP017 across 7 operator scripts) | Sprint V (small drive-by) |
| **SU-FU-3** | Alembic `048` rename `invoice_date` SQL column to `issue_date` | Sprint V (or post-V — only matters when the doc_recognizer skill writes its own date columns) |
| **SU-FU-4** | UC1 operator-script flag-on `issue_date` accuracy ≥ 90% verification on full 10-fixture corpus | Sprint V kickoff verification (first SV-1 task) |
| **SR-FU-4** (deferred from S155) | Live-stack Playwright E2E for `/prompts/workflows` admin page | Sprint V SV-4 admin UI work (next to doc-recognizer admin page) |
| **SR-FU-6** (deferred from S155) | Langfuse workflow listing surface (`LangfuseClient.list_workflow_prompts()` + admin UI source-toggle) | Sprint V/W (re-evaluate after Langfuse v3→v4 server migration decision) |
| **ST-FU-4-followup** | The 4 remaining operator scripts adopting `argparse_output()` helper | Sprint V (during SV-5) |

## Carried (Sprint S / Q / P / N / M / J — unchanged)

- **SS-FU-1 / SS-FU-5** — `customer` → `tenant_id` model rename + `rag_collections.customer` column drop. Out of Sprint U (separate refactor sprint).
- **SS-SKIP-2** / **ST-SKIP-1** — Profile B (Azure OpenAI) live MRR@5 measurement. Conditional skip behind Azure credit availability.
- Sprint Q **SQ-FU-3** unchanged (UC1 corpus extension to 25 fixtures).
- Sprint P SP-FU-1..3 unchanged.
- Sprint N/M/J residuals unchanged (Vault rotation E2E, AppRole IaC, Langfuse v3→v4 unchanged).
- Coverage uplift 70%→80% (SJ-FU-7) — dormant; will be re-evaluated post-Sprint-V audit per the audit doc's "Post-Sprint-V audit gate (DEFER)" section.

## Skipped items tracker (final)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SU-SKIP-1 | `.github/workflows/nightly-regression.yml` `uc3-4combo-matrix` | Weekly job skip-by-default on PR runs | `secrets.OPENAI_API_KEY` + scheduled trigger |
| SU-SKIP-2 (planned) | `tests/ui-live/prompt-workflows.md` (S155 rescope) | Live Playwright `/prompts/workflows` deferred | Sprint V/W admin UI work |
| SS-SKIP-2 | `tests/integration/services/rag_engine/test_retrieval_baseline.py::test_retrieval_baseline_profile_b_openai` | Profile B Azure live MRR@5 measurement | Azure credit |

## Sprint U headline metric

**+51 unit tests, 0 integration delta, 0 endpoint change, 0 UI page change, 0 Alembic migration**, 5 PRs merged in 2 calendar days, **zero customer-visible feature change**. The win is operability:

- 3 new CI gates (OpenAPI drift, weekly UC3 4-combo, BGE-M3 PR-time integration)
- 1 pre-commit hook (vite-build for `aiflow-admin/` changes)
- 1 settings consolidation (`CostSettings` umbrella + 1 cost-write path + per-step ceiling API + env-tunable tier fallbacks)
- 2 new persona PromptWorkflow descriptors (additive)
- 1 invoice prompt + schema fix (`issue_date` canonical name)
- 1 `make api` docling warmup gate
- 1 uniform `--output` flag helper (1 of 5 scripts migrated)
- 1 Sprint V kickoff plan published

Sprint V can begin with SV-1 doc-recognizer interface design without picking up a single operability follow-up that should have been Sprint U's responsibility.
