# Sprint T — Retrospective (v1.5.3 PromptWorkflow per-skill consumer migration)

> **Sprint window:** 2026-04-25 (5 sessions: S147 kickoff, S148, S149, S150, S151 close)
> **Branch:** `chore/sprint-t-close` (cut from `main` @ `ee2b431`, S150 squash-merge)
> **Tag:** `v1.5.3` — queued for post-merge on `main`
> **PR:** opened at S151 against `main` — see `docs/sprint_t_pr_description.md`
> **Predecessor:** `v1.5.2` (Sprint S — multi-tenant + multi-profile vector DB, MERGED `20fb792`)
> **Plan reference:** `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md`

## Headline

Sprint T closed the **PromptWorkflow consumption loop** that Sprint R left scaffolded but unconsumed. Sprint R (S139–S142) shipped the contract + admin UI + executor scaffold and explicitly deferred per-skill code migration to keep Sprint K UC3, Sprint Q UC1, Sprint J UC2 golden paths untouched. Sprint T migrated all three skills, **one session at a time, every session gated by the use-case golden-path test that protects it** — and the gates all stayed green.

```
S147:  Plan + carry-forward triage                                 ← kickoff
S148:  email_intent_processor consumes email_intent_chain          ← UC3
S149:  invoice_processor consumes invoice_extraction_chain         ← UC1
S150:  aszf_rag_chat baseline consumes aszf_rag_chain              ← UC2
S151:  retro + PR description + tag v1.5.3 prep + ST-FU-1 fix      ← close
```

The shim remains dormant by default (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false`, `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""`). When operators flip both, **all three skills** now route their LLM-call surfaces through `PromptWorkflowExecutor.resolve_for_skill(...)`. Flag-off remains byte-for-byte identical to Sprint S tip on every skill.

## Scope by session

| Session | Commit on `main` | Deliverable |
|---|---|---|
| **S147** | `9c76239` (PR #39) | Sprint T kickoff plan (`01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md`) + carry-forward triage from Sprint S retro. Reconciled stale carry-forwards (Sprint J `Clock` seam already resolved by Sprint O FU-5; "1 skipped" unit test classified as `ST-SKIP-1`). 0 skill code change, 0 new tests. |
| **S148** | `aa84347`/`aa74e02` (PR #40) | `email_intent_processor` consumes `email_intent_chain` (3-step descriptor: classify + extract_entities + score_priority). Wrapped the LLM-aware leg of the hybrid classifier with `PromptWorkflowExecutor.run_if_enabled()`. **Sprint P sklearn / `_keywords_first` early-return path untouched** — only the LLM-context branch consults the workflow executor. Sprint K UC3 4/4 golden-path E2E PASS flag-off. **+10 unit / +1 integration**. |
| **S149** | `e936eb3` (PR #41) | `invoice_processor.workflows.process` consumes `invoice_extraction_chain` (4-step: classify + extract_header + extract_lines + validate, full DAG with cost ceilings). The Sprint Q UC3→UC1 chain is the freshest golden path; the migration touches only prompt-loading, never the extraction-result schema. Per-step cost ceilings (`extract_header` 0.02 USD, `extract_lines` 0.03 USD) enforced via local `CostEstimator` + `CostGuardrailRefused` raise. Sprint Q UC1 golden-path slice ≥ 75% / `invoice_number` ≥ 90% PASS flag-off. **+15 unit / +1 integration**. |
| **S150** | `ee2b431` (PR #42) | `aszf_rag_chat.workflows.query` baseline persona consumes `aszf_rag_chain` (4-step: rewrite_query + system_baseline + answer + extract_citations, baseline persona only). `_resolve_workflow_for_persona(role)` helper returns `aszf_rag_chain` for `role=="baseline"` and `None` for `role in ("expert","mentor")` — expert/mentor stay on legacy direct-prompt path. The descriptor's `answer` step has no matching legacy `prompt_manager.get(...)` call (legacy generates the answer directly from `system_prompt_<role>` in one LLM hop) — **executor stays resolution-only, no new call site introduced**. Sprint J UC2 MRR@5 ≥ 0.55 Profile A baseline PASS. **+19 unit / +1 integration**. |
| **S151** | _(this commit)_ | Sprint close — `docs/sprint_t_retro.md`, `docs/sprint_t_pr_description.md`, CLAUDE.md numbers + Sprint T DONE banner, ST-FU-1 fix (`tests/unit/api/test_rag_collections_router.py` JWT singleton — `_client_and_headers` converted to a contextmanager so the patch covers warmup + request, 3/3 PASS), PR cut against `main`. Tag `v1.5.3` queued. |

## Test deltas

| Suite | Before (Sprint S tip) | After (S151 tip) | Delta |
|---|---|---|---|
| Unit | 2379 | **2424** | **+45** (10 S148 + 15 S149 + 19 S150 + 1 ST-FU-1 fixture wrap counted via re-run) |
| Integration | ~113 | **~116** | **+3** (S148 real-OpenAI parity, S149 real-PG+real-docling+real-OpenAI, S150 real-PG+real-BGE-M3 MRR@5) |
| E2E collected | 430 | 430 | 0 (no UI surface change in S148/S149/S150) |
| API endpoints | 196 | 196 | 0 (no new endpoints) |
| API routers | 31 | 31 | 0 |
| UI pages | 26 | 26 | 0 |
| Alembic head | 047 | **047** | 0 (no DB change) |
| Workflow descriptors on disk | 3 | 3 | 0 (unchanged) |
| Skills consuming `PromptWorkflowExecutor` | **0** | **3** | **+3** (`email_intent_processor`, `invoice_processor`, `aszf_rag_chat` baseline) |

## Per-skill summary

### S148 — `email_intent_processor`
- **Call sites migrated:** 1 LLM call site (the LLM-context branch of the hybrid classifier).
- **Risk class:** R1 (Sprint P strategy switch + attachment-signal early-return interaction).
- **Lesson learned:** The pre-LLM `_keywords_first` early-return path is the highest-traffic short-circuit in production — the executor wrap **must** sit AFTER strategy decision + early-return checks, not at the top of the function. A failing flag-off Sprint K 4/4 + a failing flag-off 25-fixture Sprint P parity check together would expose any leak.
- **Gate:** Sprint K UC3 4/4 golden-path E2E + 25-fixture Sprint P parity check, both PASS flag-off and (with operator opt-in) flag-on.

### S149 — `invoice_processor.workflows.process`
- **Call sites migrated:** 3 LLM call sites (`classify`, `extract_header`, `extract_lines`).
- **Risk class:** R2 (schema parity in `EmailDetailResponse.extracted_fields`).
- **Lesson learned:** S149 introduced the **per-step cost ceiling pattern** that Sprint N's `CostPreflightGuardrail` didn't yet support natively — local `CostEstimator` + `CostGuardrailRefused` raise inside the executor wrap. The descriptor's `validate` step is `required: false` and maps to pure-Python validation (no LLM call), so the executor wrap skips it entirely; the legacy validate code path runs unchanged.
- **Gate:** Sprint Q UC1 golden-path slice (3-fixture CI, ≥ 75% accuracy / `invoice_number` ≥ 90%) PASS flag-off. Operator-script flag-on parity on full 10-fixture corpus — overall accuracy ≥ 80% within ±5pp of Sprint Q 85.7% baseline.
- **Schema parity:** `EmailDetailResponse.extracted_fields` Pydantic model byte-identical; `ExtractedFieldsCard.tsx` continues to render unchanged.

### S150 — `aszf_rag_chat` baseline persona
- **Call sites migrated:** 3 mappable call sites (`rewrite_query`, `system_baseline` baseline-only, `extract_citations`); the descriptor's 4th step (`answer`) is a documented gap because legacy generates the answer in one LLM hop directly from `system_prompt_<role>` — no separate prompt to resolve.
- **Risk class:** R3 (persona variant carve-out).
- **Lesson learned:** Per S149's lesson, the executor stayed **resolution-only** — no new call site introduced for the `answer` step. The descriptor remains forward-compatible: when expert/mentor variants get their own descriptors (ST-FU-2), the same persona-resolver helper carries over. **`_resolve_workflow_for_persona(role)`** returns `aszf_rag_chain` only for `baseline`; expert/mentor fall through to legacy direct-prompt path.
- **Gate:** Sprint J UC2 MRR@5 ≥ 0.55 on Profile A baseline (`tests/integration/skills/test_uc2_rag.py`) + real-OpenAI parity smoke on HU UC2 query #1 PASS in 82s.

## Decisions log

- **ST-1 — Persona carve-out via resolver-returns-None.** S150's `_resolve_workflow_for_persona(role)` returns `None` for non-baseline personas, which the executor treats as "no workflow available" → legacy fallback. Same pattern as Sprint R's `is_skill_migrated()` returning False — **callers always observe a clean fallback, never a partial migration.** This makes per-persona rollout a single env-flag flip per descriptor.
- **ST-2 — `validate` step `required: false` maps to pure-Python legacy code.** S149's descriptor declares `validate` as a step but marks it `required: false`; the executor skips it during resolution, and the legacy pure-Python validate code path runs unchanged. This is the precedent for any step that doesn't correspond to an LLM call — keeps the descriptor a complete topological view of the chain without forcing every step to be LLM-bound.
- **ST-3 — Per-step cost ceilings via local `CostEstimator` + `CostGuardrailRefused` raise.** S149 introduced the per-step ceiling pattern inside the executor wrap (`extract_header` 0.02 USD, `extract_lines` 0.03 USD). Sprint N's `CostPreflightGuardrail` covers per-call ceilings; per-step ceilings are a strictly tighter sub-constraint enforced inside the workflow consumer. Future descriptors can opt in by setting `metadata.cost_ceiling_usd` on individual steps. Carries forward as a candidate for `CostPreflightGuardrail.check_step()` consolidation.
- **ST-4 — Ruff-strips-imports mitigation.** S150 caught a real footgun: when `ruff format` auto-strips type-only imports between `Edit` waves, the next `Edit` that adds the corresponding usage fails because the import block is gone. **Mitigation pattern:** bundle the imports + first usage in a single `Edit`, OR keep a referencing helper around to anchor them — the import block survives the next pass. Documented in S150's session prompt; carry to skill team's onboarding.
- **ST-5 — Default-off rollout, per-skill opt-in.** All three skills land behind `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=<comma-list>`. Default-off → zero blast radius for any tenant that hasn't flipped a flag. Operators choose per-tenant adoption sequence. **No code rollback is ever required** — drop the skill from `SKILLS_CSV` for instant runtime disable.
- **ST-6 — ST-FU-1 fix path A (lifecycle pin in `_client_and_headers`).** S151 closed the JWT singleton CI failure by converting the test helper to a `contextmanager` so the `patch.object(AuthProvider, "from_env", return_value=auth)` block stays open across `create_app()` AND the warmup `client.get("/health/live")` AND the actual request. **Root cause:** `AuthMiddleware.__init__` runs lazily on first dispatch, not on `create_app()`; if the patch closes between `create_app()` and the warmup, the middleware re-initialises with an unpatched `from_env()` and the minted token fails signature verification. ~6 LOC change, no framework touch.

## What worked

- **One skill per session, golden-path test as the gate.** Splitting the 3 migrations into 3 focused PRs (S148/S149/S150) with the relevant UC golden-path test as the merge gate kept blast radius minimal. Any single regression would have surfaced as a single-skill failure, not a 3-skill simultaneous regression.
- **`PromptWorkflowExecutor` resolution-only contract held.** Sprint R's design call to keep the executor resolution-only (never invokes LLM) was validated end-to-end across three very different skills: a hybrid ML+LLM classifier, a multi-step extraction with per-step cost ceilings, and a persona-variant RAG chain. **Each skill kept its LLM-invocation responsibility** and only delegated prompt resolution to the workflow shim.
- **Default-off rollout meant zero risk to other tenants.** Sprint T didn't need a feature-flag-rollout playbook because the default is "no behaviour change." Each tenant adopts independently when the operator flips both flags.
- **Lessons compound across sessions.** S149's `validate`-step pattern (`required: false` + pure-Python legacy fallback) directly informed S150's `answer`-step decision (no executor call site for steps without a matching legacy prompt). Both paths flow through the same resolver-returns-None contract — keeps the framework consistent.

## What hurt

- **The `answer`-step gap in S150's descriptor was discovered late.** S150's session-prompt expected 4 mappable call sites; only 3 turned out to be mappable because legacy generates the answer in one LLM hop directly from `system_prompt_<role>`, with no separate `answer_generator` prompt to resolve. The descriptor stays valid (it's a forward-compatible topology) but **future S150-style migrations should audit the descriptor against the legacy call sites BEFORE writing the executor wrap**, not during.
- **Ruff-strips-imports footgun (ST-4)** cost ~10 minutes in S150. The mitigation is documented but the underlying tooling drift (formatter vs. mid-edit incomplete state) will keep biting until either ruff gains a "preserve unused imports under EXCEPT TYPE_CHECKING" mode or the project enforces a single-Edit-per-import-cluster rule.
- **ST-FU-1 was carried for 5 sessions before fixing.** The JWT singleton CI failure was visible in Sprint S close PR #38 and triaged in S147, but didn't block any per-skill PR — so it sat as a `must-clean before tag` rather than a hard blocker. Lesson: small CI-only test failures should land in the next session that touches the relevant test surface, not at sprint close. Adding ~6 LOC at session close is fine; carrying a known-red CI signal across 5 sessions adds noise.

## Open follow-ups

- **ST-FU-2** Expert/mentor persona descriptors (`aszf_rag_chain_expert`, `aszf_rag_chain_mentor`). Each picks a different `system_prompt_<role>.yaml`. The persona-resolver in S150 is forward-compatible — when these descriptors land, `_resolve_workflow_for_persona(role)` learns to dispatch them by role. Target: post-Sprint-T or Sprint U side delivery.
- **ST-FU-3** Consolidate per-step cost ceilings into `CostPreflightGuardrail.check_step()` so the executor wrap doesn't need a local `CostEstimator`. S149's local pattern is correct for Sprint T but is a candidate for upstream into the framework guardrail.
- **ST-FU-4** Operator parity scripts (S148 25-fixture, S149 10-fixture, S150 20-item HU UC2) need a uniform `--output` flag for CI integration. S150 inherited the gap from S149.
- **ST-FU-5** ruff-strips-imports tooling fix or convention. Either upstream-config the formatter or document a single-Edit-per-import-cluster rule.
- **SR-FU-4** Live-stack Playwright E2E for `/prompts/workflows` page (carried from Sprint R; still deferred — no Sprint T session needed it).
- **SR-FU-5** `vite build --no-emit` pre-commit hook (carried from Sprint R).
- **SR-FU-6** Workflow listing endpoint enumerates Langfuse workflows too (carried from Sprint R).

## Carried (Sprint S / Q / P / N / M / J — unchanged)

- **SS-FU-1 / SS-FU-5** — `customer` → `tenant_id` model rename + `rag_collections.customer` column drop. Out of Sprint T (separate refactor sprint).
- **SS-SKIP-2** / **ST-SKIP-1** — Profile B (Azure OpenAI) live MRR@5 measurement. Conditional skip behind Azure credit availability.
- Sprint Q SQ-FU-1..4 unchanged (`issue_date` extraction fix, docling warmup at boot, corpus extension, `_parse_date` ISO roundtrip).
- Sprint P SP-FU-1..3 unchanged.
- Sprint N/M/J residuals unchanged (BGE-M3 weight cache lives at S145; live rotation E2E, AppRole IaC, Langfuse v3→v4 unchanged).

## Skipped items tracker (final)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-2 | Sprint T plan §11 | Expert/mentor persona descriptors | Post-Sprint-T (Sprint U candidate) |
| SR-FU-4/5/6 | Sprint R retro | Live-stack Playwright + vite-build hook + Langfuse listing | Sprint U side delivery if bandwidth |

## Key numbers (Sprint T tip)

```
27 service | 196 endpoint (31 routers) | 50 DB table | 47 Alembic (head: 047)
2424 unit PASS / 1 skipped (ST-SKIP-1 conditional Azure Profile B)
~116 integration PASS (Sprint T +3 — 1 per per-skill migration on real services)
430 E2E collected (Sprint T +0 — by design, no UI surface change)
0 ruff error on changed files | 0 TSC error | OpenAPI snapshot unchanged
Branch: chore/sprint-t-close (HEAD prepared, S151 close commit on top of S150 squash)
Flag defaults on merge: AIFLOW_PROMPT_WORKFLOWS__ENABLED=false
                        AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""
                        (all per-skill flag-on opt-in, default-off → zero behaviour change)
3 skills now consume PromptWorkflowExecutor:
   email_intent_processor → email_intent_chain (3 steps)
   invoice_processor → invoice_extraction_chain (4 steps + per-step cost ceilings)
   aszf_rag_chat baseline → aszf_rag_chain (4 steps; expert/mentor on legacy)
```

Sprint T closes green on every gate. Sprint U opens with a clean `main`, no in-flight per-skill migrations, no carry-forward red CI signals.
