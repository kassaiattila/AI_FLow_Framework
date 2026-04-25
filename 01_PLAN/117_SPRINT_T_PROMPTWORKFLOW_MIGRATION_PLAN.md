# AIFlow v1.5.3 Sprint T — PromptWorkflow consumer migration

> **Status:** KICKOFF on 2026-04-25 (S147).
> **Branch:** `feature/t-s{N}-*` (each session its own branch → PR → squash-merge).
> **Parent plan:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 (Sprint R foundation).
> **Predecessor:** v1.5.2 Sprint S (functional vector DB MERGED `20fb792`, tag `v1.5.2`).
> **Target tag (post-merge):** `v1.5.3`.

---

## 1. Goal

Close the **PromptWorkflow consumption loop** that Sprint R left scaffolded but unconsumed. Sprint R (S139–S142) shipped the `PromptWorkflow` contract + admin UI + executor scaffold, then explicitly deferred per-skill code migration to keep Sprint K UC3, Sprint Q UC1, Sprint J UC2 golden paths untouched. Three workflow descriptors landed on disk (`prompts/workflows/email_intent_chain.yaml`, `invoice_extraction_chain.yaml`, `aszf_rag_chain.yaml`) — **0 skill consumes them today**. Sprint T migrates each skill one session at a time, every session gated by the use-case golden-path test that protects it. Default-off rollout (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` + per-skill `SKILLS_CSV` opt-in) keeps zero-tenant-impact: any tenant that hasn't flipped a flag continues on the legacy direct-invocation path byte-for-byte unchanged.

### Capability cohort delta

| Cohort | Sprint R close | Sprint T close (target) |
|---|---|---|
| Workflow descriptors on disk | 3 | 3 (unchanged) |
| Skills consuming `PromptWorkflowExecutor` | **0** | **3** (`email_intent_processor`, `invoice_processor`, `aszf_rag_chat` baseline persona) |
| `AIFLOW_PROMPT_WORKFLOWS__ENABLED` default | `false` | `false` (unchanged — opt-in only) |
| `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` default | `""` | `""` (unchanged — operator opts each skill in explicitly) |
| Golden-path baselines | UC3 4/4, UC1 ≥ 80%, UC2 MRR@5 ≥ 0.55 | identical (gate per session) |
| Alembic head | 047 | 047 (no migration in Sprint T) |
| New endpoints / UI pages | — | 0 / 0 |

---

## 2. Sessions

### S147 — Kickoff (THIS SESSION)
**Scope.** Plan + carry-forward triage. Three deliverables: this plan doc, `docs/sprint_t_plan.md` operator-facing companion, and a reconcile of two stale carry-forwards (Sprint J `Clock` seam already resolved by Sprint O FU-5; the "1 skipped" unit test inventoried + classified). 0 skill code change, 0 new tests, 0 Alembic.

### S148 — `email_intent_processor` PromptWorkflow migration (S141-FU-1)
**Scope.** Wire `email_intent_chain` (3-step descriptor: classify + extract_entities + score_priority) into `skills/email_intent_processor/workflows/classify.py`. The LLM-aware leg of the hybrid classifier (steps 3 / 4 / 5 in the existing 7-step pipeline) gains a `PromptWorkflowExecutor.run_if_enabled()` gate before falling through to the legacy direct `PromptManager.get()` path. **The sklearn / `_keywords_first` early-return path is untouched** — Sprint P's strategy switch + attachment-signal early-return all stay on the legacy code surface. Only the LLM-context branch consults the workflow executor.

**Gate.** Sprint K UC3 4/4 golden-path E2E (`tests/e2e/uc3/test_email_intent_*.py`) — must remain 4/4 with flag-off. Plus a dedicated **flag-on** smoke run that asserts the chain returns identical labels on the 25-fixture corpus from Sprint P.

**Expected diff.** ~120 lines in `classify.py` (executor wrap + fallback) + ~5–8 unit tests (executor-path mocked, fallback path, flag-off identity, per-step error isolation) + 1 integration test (real OpenAI on `001_invoice_march.eml` — flag-on parity with flag-off baseline). 0 UI surface change.

**Risk.** R1 — strategy switch interaction (see §4 R1).

### S149 — `invoice_processor.workflows.process` PromptWorkflow migration (S141-FU-2)
**Scope.** Wire `invoice_extraction_chain` (4-step: classify + extract_header + extract_lines + validate, full DAG with cost ceilings) into `skills/invoice_processor/workflows/process.py`. The Sprint Q UC3 → UC1 chain is the freshest golden path; the migration touches **only** prompt-loading, never the extraction-result schema (`EmailDetailResponse.extracted_fields` from Sprint Q S136 must stay byte-identical). Cost ceilings (`metadata.cost_ceiling_usd 0.02 / 0.03`) become live via `PromptWorkflowExecutor` — extends Sprint N's `CostPreflightGuardrail` reach to per-step ceilings.

**Gate.** Sprint Q UC1 golden-path slice (`tests/integration/skills/test_uc1_golden_path.py`) — overall accuracy ≥ 75% / `invoice_number` ≥ 90% on the 3-fixture CI slice. Plus the operator measurement script (`scripts/measure_uc1_golden_path.py`) flag-on parity check on the full 10-fixture corpus (**target ≥ 80% accuracy**, mirrors Sprint Q's 85.7% baseline within ±5pp).

**Expected diff.** ~150 lines in `process.py` (executor wrap + per-step cost-ceiling check + fallback) + ~6–10 unit tests (4 step happy paths, validate-step `required: false` skip, cost-ceiling refusal, flag-off identity) + 1 integration test (real PG + real docling + real OpenAI on `001_invoice_march.eml`). `EmailDetailResponse.extracted_fields` Pydantic schema unchanged.

**Risk.** R2 — schema parity (see §4 R2).

### S150 — `aszf_rag_chat.workflows.query` baseline persona migration (S141-FU-3)
**Scope.** Wire `aszf_rag_chain` (4-step: rewrite_query + system_baseline + answer + extract_citations) into `skills/aszf_rag_chat/workflows/query.py` for the **baseline persona only**. The expert / mentor persona variants pick a different `system_prompt_<role>.yaml` at runtime; those would be separate workflows (deferred — see §6 Out of scope). The migration writes a `_resolve_workflow_for_persona(role)` helper that returns `aszf_rag_chain` for `role=="baseline"` and `None` (legacy fallback) for `role in ("expert","mentor")`.

**Gate.** Sprint J UC2 MRR@5 ≥ 0.55 on Profile A baseline (existing `tests/integration/skills/test_uc2_rag.py` + the nightly `RagMetricsHarness` from Sprint S S145). Flag-on parity check: same MRR@5 within ±0.02 absolute on the 20-item HU UC2 corpus (`data/fixtures/rag_metrics/uc2_aszf_query_set.json`).

**Expected diff.** ~100 lines in `query.py` (persona resolver + executor wrap + fallback) + ~5–8 unit tests (baseline-persona dispatch, expert/mentor fallback, citation-step `required: false` skip, flag-off identity) + 1 integration test (real PG + real BGE-M3 weights, MRR@5 on 5 baseline queries). 0 UI / endpoint change.

**Risk.** R3 — persona variant carve-out (see §4 R3).

### S151 — Sprint T close
**Scope.** `docs/sprint_t_retro.md`, `docs/sprint_t_pr_description.md`, CLAUDE.md banner flip + key-numbers update, PR opened against `main`, tag `v1.5.3` queued. Explicit skipped-items enumeration (per Sprint S retro pattern). Closes carry-forward IDs `S141-FU-1/2/3`. Carries forward expert/mentor persona migration + `SR-FU-4/5/6` if not addressed inline.

---

## 3. Plan, gate matrix

| Session | Skill | Workflow descriptor | Golden-path test | Threshold | Rollback path |
|---|---|---|---|---|---|
| S148 | `email_intent_processor` | `email_intent_chain` | `tests/e2e/uc3/test_email_intent_*.py` (4/4) + 25-fixture flag-on smoke | 4/4 PASS flag-off; 25/25 label parity flag-on within ±1 fixture | `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""` (drop skill from CSV) — instant disable, no code rollback needed |
| S149 | `invoice_processor` | `invoice_extraction_chain` | `tests/integration/skills/test_uc1_golden_path.py` (3-fixture CI) + 10-fixture operator measurement | overall ≥ 75% / invoice_number ≥ 90% (CI); operator full corpus ≥ 80% accuracy within ±5pp of Sprint Q 85.7% baseline | Drop `invoice_processor` from `SKILLS_CSV`; `EmailDetailResponse.extracted_fields` schema-stable so UI continues to render |
| S150 | `aszf_rag_chat` (baseline) | `aszf_rag_chain` | `tests/integration/skills/test_uc2_rag.py` + nightly `RagMetricsHarness` 20-item HU UC2 corpus | MRR@5 ≥ 0.55 Profile A; flag-on parity within ±0.02 absolute | Drop `aszf_rag_chat` from `SKILLS_CSV`; baseline persona auto-resolves back to legacy direct path |

**Threshold column is what blocks merge.** A failing golden-path or parity check in any session halts that session's PR; the operator either rolls forward (debugging the regression) or pulls the skill from `SKILLS_CSV` at runtime as a hot-rollback while the fix lands in a follow-up session.

---

## 4. Risk register

### R1 — Strategy switch interaction in `email_intent_processor`
The hybrid classifier has *both* an sklearn path *and* an LLM-fallback path; Sprint P S132 added strategy switching (`SKLEARN_ONLY` / `SKLEARN_FIRST` / `SKLEARN_THEN_LLM`) plus an attachment-signal early-return that bypasses the LLM entirely on strong-signal contracts/invoices. The PromptWorkflow only abstracts the **LLM** path. Migration must preserve every short-circuit on the sklearn / early-return paths byte-for-byte; the executor only kicks in when the legacy code would have invoked `PromptManager.get()` for an LLM call.

**Mitigation.** S148 wraps the executor inside the existing LLM-branch entrypoint (after strategy decision + early-return checks). Flag-off short-circuit fast — `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` returns `None` from `PromptWorkflowExecutor.run_if_enabled()` and the legacy code path runs unchanged. Sprint P's `_keywords_first` early-return remains pre-LLM, untouched.

**Detection.** A failing flag-off Sprint K 4/4 golden path + a failing flag-off 25-fixture Sprint P parity check together would expose any leak of executor logic into the sklearn path.

### R2 — Schema parity in `invoice_processor`
Sprint Q S136 added `EmailDetailResponse.extracted_fields` (vendor / buyer / header / items / totals) and the admin UI's `ExtractedFieldsCard.tsx` consumes it. The migration changes only the prompt-loading surface; the extraction-result schema must stay byte-identical, otherwise the Sprint Q live-stack Playwright E2E (`tests/ui-live/extracted-fields-card.md`) breaks.

**Mitigation.** S149 keeps the existing `_extract_invoice_fields()` Pydantic model untouched; the executor produces step outputs (header / line_items / validation) that flow into the same Pydantic constructor that the legacy code path uses. Flag-on/flag-off A/B on the 10-fixture corpus must produce **byte-identical** `extracted_fields` JSON on at least 9/10 fixtures (LLM nondeterminism allows ±1 fixture variance).

**Detection.** Sprint Q golden-path slice + a new flag-on/flag-off byte-diff assertion in the integration test.

### R3 — Persona variant carve-out in `aszf_rag_chat`
The skill has 3 role variants (baseline / expert / mentor). S150 migrates **only** baseline; expert / mentor remain on the legacy per-prompt path (their `system_prompt_<role>.yaml` files would each need their own workflow descriptor — out of scope for Sprint T). This mirrors the partial-migration pattern Sprint R used in the S141 scaffold.

**Mitigation.** A `_resolve_workflow_for_persona(role)` helper returns `aszf_rag_chain` when `role=="baseline"` and `None` for the other two. Flag-off and any non-baseline role fall through to legacy. Sprint J UC2 MRR@5 gate runs on baseline only — that's the persona that has the existing baseline.

**Detection.** Add a unit test that `role="expert"` and `role="mentor"` never trigger an executor call (assert `executor.run_if_enabled` not called for those roles).

### R4 — Default-off rollout (no per-tenant blast radius)
All three migrations land behind `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + per-skill `SKILLS_CSV` opt-in. **Default-off → zero rollback risk** for any tenant that hasn't explicitly flipped the flag. Operators choose when each tenant adopts the new path.

**Mitigation.** This is by design, not a risk to mitigate. Documenting the rollout sequence in `docs/sprint_t_plan.md` §"Operator activation" so each tenant can be toggled independently.

**Detection.** A flag-off CI run on every PR proves the legacy path is byte-stable. A flag-on smoke runs in the per-session integration test.

---

## 5. Follow-up table

Carry-forwards (Sprint S → Sprint T) + Sprint T's own ST-FU-X entries.

| ID | Description | Source | Target |
|---|---|---|---|
| S141-FU-1 | `email_intent_processor` PromptWorkflow migration | Sprint R retro | **Sprint T S148** |
| S141-FU-2 | `invoice_processor.workflows.process` migration | Sprint R retro | **Sprint T S149** |
| S141-FU-3 | `aszf_rag_chat.workflows.query` baseline migration | Sprint R retro | **Sprint T S150** |
| SR-FU-4 | Live-stack Playwright for `/prompts/workflows` admin page | Sprint R retro | Sprint T side delivery (S148+ if bandwidth) |
| SR-FU-5 | `vite build` pre-commit hook | Sprint R retro | Sprint T side delivery |
| SR-FU-6 | Langfuse workflow listing surface | Sprint R retro | Sprint T or later |
| SS-FU-1 | `create_collection` tenant-aware arg + `customer` deprecation | Sprint S retro | **Out of Sprint T** — separate refactor sprint |
| SS-FU-5 | `rag_collections.customer` column drop | Sprint S retro | **Out of Sprint T** (after SS-FU-1) |
| SS-SKIP-2 | Profile B (Azure OpenAI) live MRR@5 | Sprint S retro | Azure credit landing — **Out of Sprint T** |
| ST-FU-1 | JWT singleton CI failure in `tests/unit/api/test_rag_collections_router.py` (3 tests, Linux-only `secret_cache_hit negative=True` ephemeral key swap) | Sprint S close PR #38 CI red, S147 triage | Sprint T side delivery (recommended S148) — pin a per-test fresh `AuthProvider` + clear secret cache fixture |
| ST-FU-2 | Expert/mentor persona PromptWorkflow descriptors (`aszf_rag_chain_expert`, `aszf_rag_chain_mentor`) | S150 carve-out | Post-Sprint-T |

---

## 6. Test count expectations

Each skill migration adds ~5–10 unit tests + 1 integration test on real services. Total expected delta:

| Bucket | Sprint S close | Sprint T close (target) | Delta |
|---|---|---|---|
| Unit tests | 2379 | **2394–2409** | **+15 to +30** |
| Integration tests | ~113 | **~116** | **+3** (S148/S149/S150 each +1) |
| E2E tests | 430 | 430 (unchanged) | 0 |
| Alembic head | 047 | 047 (unchanged) | 0 |
| New endpoints | 196 | 196 | 0 |
| New UI pages | 26 | 26 | 0 |

The 432-vs-430 E2E count discrepancy noted in S147 NEXT.md §6 SOFT stop is presumed parametrize splits — Sprint T `S151` close will reconcile in the retro key-numbers block.

---

## 7. Definition of done — per session

1. **Green golden-path test** at the threshold listed in §3 gate matrix.
2. **Flag-on smoke** on the per-session corpus / fixture set (S148 25-fixture, S149 10-fixture, S150 20-item HU UC2).
3. **Flag-off smoke** confirms zero behaviour change on the same corpus (legacy path byte-stable).
4. **`ruff check src/ tests/`** + **`cd aiflow-admin && npx tsc --noEmit`** clean.
5. Session-close generates `docs/sprint_t_session_<N>_retro.md` (lightweight per-session note) + queues NEXT.md for the next session.
6. Skipped-items tracker (§8 below) updated with any new pytest.skip / deferred follow-up.

## 8. Skipped items tracker (S147 → S151)

Session-close per session must enumerate + explicit unskip-condition:

| ID | Session | Item | Unskip condition |
|---|---|---|---|
| ST-SKIP-1 | S147 | `tests/unit/providers/embedder/test_azure_openai.py::test_azure_openai_embed_real_api` (the "1 skipped" CLAUDE.md count). Intentional **conditional skip** — Azure OpenAI Profile B live round-trip. **Same as `SS-SKIP-2`** (Sprint S carry); inventoried in `docs/quarantine.md` "Conditional skips" §1. **Not a regression**, not a flake; expected steady state on every dev workstation + CI without Azure creds. | `AIFLOW_AZURE_OPENAI__ENDPOINT` + `AIFLOW_AZURE_OPENAI__API_KEY` env vars set (Azure billable credit lands) |
| *TBD* | S148+ | *(append during execution)* | — |

---

## 9. STOP conditions (HARD)

1. **Any per-session golden-path threshold failed** → halt + escalate. Either fix forward in the same session or revert and reschedule.
2. **Flag-off smoke regression** (legacy-path byte-instability) → halt; the executor scaffold has leaked into the legacy path. Roll back the session's diff entirely.
3. **`alembic upgrade head` ≠ 047** at any session start → drift outside Sprint T scope; investigate before opening the session.
4. **Schema drift in `EmailDetailResponse.extracted_fields`** during S149 → halt; the migration has crossed the schema-parity line (R2).
5. **Operator dispute on per-skill ordering** (e.g. start with `aszf_rag_chat` instead of `email_intent_processor`) → halt + revisit in this plan.

## 10. Rollback

- Per-skill: drop the skill name from `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` (instant runtime disable, no code rollback).
- Sprint-wide: flip `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` (kills executor calls everywhere).
- Per-session diff: each session is a single squash-merge — `git revert <squash>` reverts cleanly.
- Schema: 0 Alembic in Sprint T → no DB rollback required.

## 11. Out of scope (Sprint T)

- Expert / mentor persona PromptWorkflow descriptors (`ST-FU-2`, post-Sprint-T).
- `customer` → `tenant_id` model rename (`SS-FU-1` / `SS-FU-5`, separate refactor sprint).
- Profile B Azure live MRR@5 (`SS-SKIP-2`, Azure credit pending).
- Langfuse workflow listing surface (`SR-FU-6`, post-Sprint-T or per-skill side-delivery).
- New skills consuming `PromptWorkflowExecutor` beyond the existing 3 (additional descriptors land in their own sprints).
- Multi-step LLM cost aggregation rollups in `CostAttributionRepository` — current per-step ceilings reuse Sprint N's existing per-call recorder.
