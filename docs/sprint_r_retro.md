# Sprint R — Retrospective (v1.5.1 PromptWorkflow foundation)

> **Sprint window:** 2026-05-11 → 2026-05-14 (4 sessions: S139, S140, S141, S142)
> **Branch:** `feature/r-s142-sprint-close` (cut from `main` @ `20ce548`, S141 squash-merge)
> **Tag:** `v1.5.1` — queued for post-merge on `main`
> **PR:** opened at S142 against `main` — see `docs/sprint_r_pr_description.md`
> **Predecessor:** `v1.5.0` (Sprint Q — UC1 invoice extraction at 85.7% accuracy, MERGED `c4ded1d`)
> **Plan reference:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 Sprint R

## Headline

Sprint R built a reusable **`PromptWorkflow`** abstraction so multi-step prompt chains stop being copy-paste artifacts inside each skill. The contract, the lookup, the admin UI, and the per-skill executor scaffold all shipped. The actual per-skill code migration was **explicitly deferred** to follow-up sessions to keep Sprint K UC3, Sprint Q UC1, and Sprint J UC2 golden paths untouched — bundling 3 skill migrations in a single session would have risked regressing every UC.

```
S139:  PromptWorkflow model + YAML loader + Langfuse lookup       ← contract
S140:  Admin UI /prompts/workflows + dry-run endpoint              ← surface
S141:  PromptWorkflowExecutor + 3 ready-to-consume descriptors     ← scaffold
       (skill code untouched — per-skill migration → S141-FU-1/2/3)
```

The shim is dormant by default (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false`, `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""`). When operators flip both, `PromptWorkflowExecutor.resolve_for_skill(...)` returns the resolved chain, and the calling skill can adopt it incrementally. Today **no skill calls the executor** — that's S141-FU-1/2/3.

## Scope by session

| Session | Commit | Deliverable |
|---|---|---|
| **S139** | `5ad20d0` (PR #30) | `PromptWorkflow` + `PromptWorkflowStep` Pydantic models with full DAG validation (Kahn topological sort, dedup, cycle detection). `PromptWorkflowLoader` filesystem loader. `PromptManager.get_workflow()` 3-layer resolution (cache → Langfuse `workflow:<name>` JSON-typed prompt → local YAML). `PromptWorkflowSettings` (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` default). `FeatureDisabled` exception (HTTP 503). Example descriptor `prompts/workflows/uc3_intent_and_extract.yaml`. **24 unit tests** (8 model + 6 loader + 7 manager + 3 settings). |
| **S140** | `47c2634` (PR #31) | Admin UI `/prompts/workflows` page (React 19 + Tailwind v4: table list + detail panel with DAG indentation + metadata chips + Test Run button rendering dry-run JSON). New router `src/aiflow/api/v1/prompt_workflows.py` (3 GET endpoints: list / detail / dry-run). EN/HU locale bundle. Sidebar nav entry. `get_prompt_manager()` extended to wire workflow loader + auto-register skill prompt YAMLs when flag is on. **CRITICAL ordering fix**: workflow router mounted BEFORE prompts router on both backend (FastAPI) and frontend (React Router) — the existing `/prompts/{path}` catch-all otherwise shadows `/workflows`. **10 router unit tests** + OpenAPI snapshot refresh. **Mid-PR fix**: switched `useTranslation` (react-i18next, not in deps) → `useTranslate` from existing `lib/i18n` (CI-caught, fixed in same PR). |
| **S141** | `20ce548` (PR #32) | `PromptWorkflowExecutor` scaffold (`src/aiflow/prompts/workflow_executor.py`) — pure resolution helper with `is_skill_migrated()` + `resolve_for_skill()`. Returns `None` on flag-off / descriptor-missing / nested-prompt-unresolvable so callers fall back cleanly to legacy paths. **Never invokes an LLM.** `PromptWorkflowSettings.skills_csv: str` per-skill opt-in (raw string + parsed `.skills` property because pydantic_settings JSON-decodes `list[str]` env vars). 3 workflow descriptors under `prompts/workflows/`: `email_intent_chain.yaml` (3 steps), `invoice_extraction_chain.yaml` (4 steps with full DAG + cost ceilings), `aszf_rag_chain.yaml` (4 steps, baseline persona only). **17 unit tests** (15 executor + 2 settings). **Skill code untouched** — per-skill migration deferred to S141-FU-1/2/3. |
| **S142** | _(this commit)_ | Sprint close — `docs/sprint_r_retro.md`, `docs/sprint_r_pr_description.md`, CLAUDE.md numbers + Sprint R DONE banner, PR cut against `main`. Tag `v1.5.1` queued. |

## Test deltas

| Suite | Before (Sprint Q tip) | After (S141 tip) | Delta |
|---|---|---|---|
| Unit | 2296 | **2347** | **+51** (24 S139 + 10 S140 + 17 S141) |
| Integration | ~103 | ~103 | 0 (no skill migration → no integration test added; live-Langfuse test deferred to S140 follow-up) |
| E2E collected | 429 | 429 | 0 (live-stack Playwright deferred to S140 follow-up — needs interactive shell) |
| API endpoints | 190 | **193** | **+3** (`/api/v1/prompts/workflows` list / detail / dry-run) |
| API routers | 29 | **30** | **+1** (`prompt_workflows.py`) |
| UI pages | 24 | **25** | **+1** (PromptWorkflows.tsx) |
| Alembic head | 045 | **045** | 0 (no DB change) |
| Ruff / TSC | clean | clean | 0 new errors |

## Contracts + architecture delivered

- **`PromptWorkflow` + `PromptWorkflowStep` (S139)** — Pydantic models with Kahn topological sort for cycle detection. Steps reference prompts by name (not nested), so descriptors can be authored without inlining prompt content. `default_label` honors the existing dev/test/staging/prod label semantics from `PromptManager.get()`.
- **`PromptManager.get_workflow()` (S139)** — Mirrors the existing `get()` 3-layer pattern. Workflows live in Langfuse as `workflow:<name>` JSON-typed prompts (reuses v4 SDK `get_prompt`, no new client code). Falls back to local YAML registry. `WorkflowResolutionError` carries `workflow + step_id + cause` for actionable debugging.
- **`/api/v1/prompts/workflows` (S140)** — 3 read-only GET endpoints. Dry-run resolves the workflow + per-step `PromptDefinition` JSON without any LLM call. Maps `KeyError → 404`, `WorkflowResolutionError → 422` (with step_id), `FeatureDisabled → 503`. Mounted before the catch-all `prompts` router so `/workflows` doesn't get shadowed.
- **`PromptWorkflows.tsx` admin page (S140)** — Table list + detail panel with DAG-indented step ordering (`marginLeft: depends_on.length * 12px`), metadata chips, "Test Run" button. Locale-aware (EN/HU). Reuses the existing `useTranslate` hook + `PageLayout` + `EmptyState` + `ErrorState` components.
- **`PromptWorkflowExecutor` (S141)** — Skill-side shim with `is_skill_migrated(skill_name)` + `resolve_for_skill(skill_name, workflow_name, *, label)`. Returns `None` on every failure mode (flag off, descriptor missing, nested prompt unresolvable). Callers fall back to legacy per-prompt paths automatically. **Never calls an LLM** — skill keeps that responsibility.
- **`PromptWorkflowSettings.skills_csv` (S141)** — Per-skill opt-in via `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV="invoice_processor,email_intent_processor"`. Stored as raw string because pydantic_settings would JSON-decode a `list[str]` field from env.

## Key numbers (Sprint R tip)

```
27 service | 193 endpoint (30 routers) | 50 DB table | 45 Alembic (head: 045)
2347 unit PASS / 1 skipped
~103 integration PASS (Sprint R +0 — by design, no skill migration in scope)
429 E2E collected (Sprint R +0 — live-stack Playwright queued)
0 ruff error on changed files | 0 TSC error | OpenAPI snapshot refreshed
Branch: feature/r-s142-sprint-close (HEAD prepared, 3 commits on main ahead
        of Sprint Q tip c4ded1d)
Flag defaults on merge: AIFLOW_PROMPT_WORKFLOWS__ENABLED=false
                        AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""
                        AIFLOW_UC3_EXTRACTION__ENABLED=false (Sprint Q unchanged)
                        AIFLOW_UC3_ATTACHMENT_INTENT__* (Sprint O/P unchanged)
3 ready-to-consume workflow descriptors: email_intent_chain (3 steps),
                                          invoice_extraction_chain (4 steps),
                                          aszf_rag_chain (4 steps)
```

## Decisions log

- **SR-1 — 3-layer lookup mirroring `PromptManager.get()`.** Cache → Langfuse → local YAML. Kept the existing pattern instead of inventing a new one. Side benefit: the workflow cache + invalidation API just falls out of the design.
- **SR-2 — Workflows in Langfuse under `workflow:<name>`.** Reused the v4 SDK `get_prompt(name=..., type="text")` call. No new Langfuse client code. Trade-off: workflow listing can't enumerate Langfuse-only workflows (no cheap list-by-prefix call); local YAML registry is the source of truth for the listing endpoint. Filed as SR-FU-6.
- **SR-3 — Admin UI uses `useTranslate` from existing `lib/i18n`** (not `react-i18next`). The first PR caught this at CI (Vite build failed, `react-i18next` not in `package.json`). Fix landed in the same PR. Lesson: local TSC doesn't validate runtime resolution; consider adding a vite-build step to the local pre-commit (SR-FU-5).
- **SR-4 — Workflow router mounted BEFORE prompts router.** Both FastAPI and React Router would otherwise resolve `/prompts/workflows` against the `/{prompt_name:path}` catch-all in the legacy `prompts` router. Documented inline with explicit comments in both `app.py` and `router.tsx`.
- **SR-5 — `skills_csv: str`** instead of `list[str]` for the per-skill opt-in env. `pydantic_settings` JSON-decodes list fields from env vars, breaking simple CSV input. Computed `.skills` property keeps the API ergonomic while the stored field is env-friendly.
- **SR-6 — S141 ships scaffold-only, defers per-skill migration.** Bundling 3 skill migrations in a single session risked regressing Sprint K UC3 / Sprint Q UC1 / Sprint J UC2 golden paths simultaneously. Each skill has different entanglement (email_intent_processor: discovery + LLM classifier; invoice_processor: freshest Sprint Q golden path; aszf_rag_chat: role-based system_prompt selection). Splitting into 3 follow-ups (S141-FU-1/2/3), each with its golden-path test as the gate, is materially lower-risk.

## What worked

- **Incremental scaffolding** (model → router → executor) made each session's PR independently mergeable. None of the 4 PRs depended on the next; each could land on its own and still ship value.
- **Reuse of Sprint M's `PromptManager` pattern** — the workflow lookup is a strict mirror of the per-prompt lookup. No new abstractions, no surprise patterns.
- **Per-skill opt-in via `skills_csv`** — operators can roll out the workflow shim one skill at a time per tenant. Same per-tenant pattern Sprint N established for `tenant_budgets`.
- **The CI-caught `react-i18next` slip was a feature, not a bug.** It turned a latent runtime crash into a 3-minute fix in the same PR. The lesson (SR-FU-5) is to push that catch upstream to local pre-commit.

## What hurt

- **`react-i18next` slip** (caught at S140 CI Vite build, not local TSC). Local TypeScript check passes because `react-i18next` is a valid type lookup against `node_modules` (which has it transitively); only Vite's actual bundler resolution flagged the missing direct dep. SR-FU-5: add `npx vite build --no-emit` (or similar) to the local pre-commit.
- **3-skill migration deferred to follow-ups.** This was the right call on risk, but it does mean Sprint R doesn't yet "prove" the workflow consumption end-to-end. The S141-FU-1 (email_intent_processor) PR will deliver that proof — it should land before Sprint S can claim PromptWorkflow as production-ready capability D in the master roadmap.
- **Live-stack Playwright E2E for `/prompts/workflows`** deferred from S140. Needs interactive shell to bring up dev server with the flag on. Acceptable for an autonomous loop; should land as part of S141-FU-1 (which will need the live stack anyway for golden-path validation).

## Open follow-ups

- **S141-FU-1** Migrate `email_intent_processor` LLM classifier path to consume `email_intent_chain`. Gate: Sprint K UC3 golden-path E2E (4/4 green). Smallest-blast-radius migration, good first proof of consumption.
- **S141-FU-2** Migrate `invoice_processor.workflows.process` to consume `invoice_extraction_chain`. Gate: Sprint Q UC1 golden-path slice (≥ 75% accuracy / invoice_number ≥ 90%). Most valuable for the customer-visible UI surface (the extracted_fields card already renders today; S141-FU-2 just changes the prompt-loading machinery underneath).
- **S141-FU-3** Migrate `aszf_rag_chat.workflows.query` baseline persona to consume `aszf_rag_chain`. Expert/mentor variants remain separate workflows. Gate: Sprint J UC2 MRR@5 ≥ 0.55.
- **SR-FU-4** Live-stack Playwright E2E for `/prompts/workflows` page. Deferred from S140 because the autonomous loop can't bring up an interactive dev server.
- **SR-FU-5** Add `vite build --no-emit` (or equivalent) to local pre-commit so the `react-i18next` class of slip is caught before push.
- **SR-FU-6** Workflow listing endpoint enumerates Langfuse workflows too (today only local YAML). Needs a Langfuse v4 list-by-prefix call.

## Carried (Sprint Q / P / N / M / J — unchanged)

Sprint Q SQ-FU-1..4 unchanged (`issue_date` extraction fix, docling warmup at boot, corpus extension, `_parse_date` ISO roundtrip). Sprint P SP-FU-1..3 unchanged. Sprint N/M/J residuals unchanged. Most of these become Sprint S+ scope.
