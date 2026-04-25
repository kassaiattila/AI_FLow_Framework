# Sprint T (v1.5.3) — PromptWorkflow per-skill consumer migration (close)

> **Cut from:** `main` @ `ee2b431` (Sprint T S150 squash-merge, PR #42). No external rebase dependency — Sprint T per-session PRs (#39/#40/#41/#42) already on `main`.

## Summary

- **All three Sprint R workflow descriptors now have skill consumers.** Sprint R shipped the contract + admin UI + executor scaffold and explicitly deferred per-skill code migration. Sprint T closed that loop: `email_intent_processor` (S148, PR #40), `invoice_processor` (S149, PR #41), and `aszf_rag_chat` baseline persona (S150, PR #42) all consume their respective workflow descriptors via `PromptWorkflowExecutor.resolve_for_skill(...)`.
- **Default-off rollout, zero behaviour change.** `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` + `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""` defaults preserved. Any tenant that hasn't flipped both flags continues on the legacy direct-invocation path byte-for-byte unchanged. Per-skill rollout is a single `SKILLS_CSV` env edit per tenant.
- **Every session gated by its UC golden-path test.** S148 by Sprint K UC3 4/4 + 25-fixture Sprint P parity; S149 by Sprint Q UC1 ≥ 75% / `invoice_number` ≥ 90% + 10-fixture operator measurement; S150 by Sprint J UC2 MRR@5 ≥ 0.55 Profile A baseline + 20-item HU UC2 corpus. **All gates green.**
- **ST-FU-1 fix lands here** (`tests/unit/api/test_rag_collections_router.py` JWT singleton CI failure — `_client_and_headers` now a contextmanager so the patch covers warmup + request, 3/3 PASS).
- **0 Alembic, 0 new endpoints, 0 new UI pages, 0 schema change** on `EmailDetailResponse.extracted_fields`. The migration touches only prompt-loading.

## Cohort delta (capability-first roadmap)

```
                          Sprint S (close)            Sprint T (close)
Workflow descriptors:     3 (Sprint R, unchanged)     3 (unchanged)
Skill consumers:          0                           3   ← email_intent_processor
                                                          ← invoice_processor
                                                          ← aszf_rag_chat (baseline)
Flag defaults:            ENABLED=false / CSV=""      ENABLED=false / CSV=""  (unchanged)
Per-skill golden paths:   UC3 4/4, UC1 ≥ 80%,         identical (each gated by its UC test)
                          UC2 MRR@5 ≥ 0.55
Alembic head:             047                         047 (unchanged)
New endpoints / UI pages: —                           0 / 0
```

## Acceptance criteria (per `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` §3 + Sprint T sessions)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `email_intent_processor` consumes `email_intent_chain` (LLM-context branch only, sklearn / `_keywords_first` early-return untouched) | ✅ | PR #40 `aa74e02`; +10 unit / +1 integration |
| 2 | `invoice_processor.workflows.process` consumes `invoice_extraction_chain` (per-step cost ceilings, schema-stable) | ✅ | PR #41 `e936eb3`; +15 unit / +1 integration |
| 3 | `aszf_rag_chat` baseline persona consumes `aszf_rag_chain`; expert/mentor on legacy | ✅ | PR #42 `ee2b431`; +19 unit / +1 integration |
| 4 | Sprint K UC3 4/4 golden-path E2E PASS flag-off | ✅ | S148 verification log |
| 5 | Sprint Q UC1 golden-path slice ≥ 75% / `invoice_number` ≥ 90% PASS flag-off | ✅ | S149 verification log |
| 6 | Sprint J UC2 MRR@5 ≥ 0.55 Profile A baseline PASS | ✅ | S150 verification log |
| 7 | Default-off flag → zero behaviour change | ✅ | Per-skill flag-off byte-stable on existing fixtures |
| 8 | `EmailDetailResponse.extracted_fields` schema-stable | ✅ | S149 byte-diff test on 10-fixture corpus |
| 9 | ST-FU-1 fix (JWT singleton CI failure) | ✅ | `tests/unit/api/test_rag_collections_router.py` 3/3 PASS |
| 10 | OpenAPI snapshot unchanged | ✅ | No API surface change in Sprint T |
| 11 | `ruff check src/ tests/` clean | ✅ | Local + CI |
| 12 | Alembic head 047 unchanged | ✅ | No migration in Sprint T |

Sprint T closes green on all 12 criteria.

## What changed

### Source code

| File | Change | Session |
|---|---|---|
| `skills/email_intent_processor/workflows/classify.py` | LLM-aware branch wrapped with `PromptWorkflowExecutor.run_if_enabled()` + legacy fallback. sklearn / `_keywords_first` early-return preserved byte-for-byte. | S148 |
| `skills/invoice_processor/workflows/process.py` | Per-step `PromptWorkflowExecutor.resolve_for_skill()` wraps for `classify` / `extract_header` / `extract_lines`. Per-step cost ceilings via local `CostEstimator` + `CostGuardrailRefused` raise. `validate` step `required: false` → pure-Python legacy path. | S149 |
| `skills/aszf_rag_chat/workflows/query.py` | `_resolve_workflow_for_persona(role)` helper. Baseline persona consumes `aszf_rag_chain` for `rewrite_query` / `system_baseline` / `extract_citations`. Expert/mentor fall through to legacy direct-prompt path. The descriptor's `answer` step has no matching legacy `prompt_manager.get(...)` call (legacy generates the answer directly from `system_prompt_<role>` in one LLM hop) — executor stays resolution-only. | S150 |
| `skills/aszf_rag_chat/__init__.py` | Persona-resolver helper export. | S150 |
| `tests/unit/api/test_rag_collections_router.py` | `_client_and_headers` converted to a `contextmanager` so the `patch.object(AuthProvider, "from_env", return_value=auth)` block covers `create_app()` AND warmup AND the request. **ST-FU-1 fix.** | S151 |
| `prompts/workflows/email_intent_chain.yaml` | Unchanged (Sprint R landed it; S148 consumes it). | — |
| `prompts/workflows/invoice_extraction_chain.yaml` | Unchanged (Sprint R landed it; S149 consumes it). | — |
| `prompts/workflows/aszf_rag_chain.yaml` | Unchanged (Sprint R landed it; S150 baseline persona consumes it). | — |

### Tests

| File | Added | Session |
|---|---|---|
| `tests/unit/skills/email_intent_processor/test_workflow_migration.py` | 10 (executor-path mocked, fallback path, flag-off identity, per-step error isolation, sklearn early-return preservation) | S148 |
| `tests/integration/skills/test_email_intent_workflow.py` | 1 (real OpenAI on `001_invoice_march.eml` — flag-on parity with flag-off baseline) | S148 |
| `tests/unit/skills/invoice_processor/test_workflow_migration.py` | 15 (4 step happy paths, validate-step `required: false` skip, cost-ceiling refusal, flag-off identity, per-step error isolation, byte-stable schema) | S149 |
| `tests/integration/skills/test_invoice_processor_workflow.py` | 1 (real PG + real docling + real OpenAI on `001_invoice_march.eml`) | S149 |
| `tests/unit/skills/aszf_rag_chat/test_workflow_migration.py` | 19 (baseline-persona dispatch, expert/mentor fallback, citation-step `required: false` skip, flag-off identity, persona-resolver matrix, no `answer` step call site) | S150 |
| `tests/integration/skills/test_aszf_rag_baseline_workflow.py` | 1 (real PG + real BGE-M3 weights, MRR@5 on baseline persona over HU UC2 query corpus) | S150 |

### Tests **unchanged** (gate set)

- `tests/e2e/uc3/test_email_intent_*.py` (Sprint K UC3 4/4 — flag-off baseline)
- `tests/integration/skills/test_uc1_golden_path.py` (Sprint Q UC1 3-fixture CI slice)
- `tests/integration/skills/test_uc2_rag.py` (Sprint J UC2 MRR@5)

## Test plan (post-merge)

- [ ] **S148 flag-on dry-run** (operator): set `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=email_intent_processor`, run the 25-fixture Sprint P parity smoke. Expect ≤ ±1 fixture variance vs. flag-off baseline.
- [ ] **S149 flag-on dry-run**: extend `SKILLS_CSV=email_intent_processor,invoice_processor`, run `scripts/measure_uc1_golden_path.py` on the 10-fixture corpus. Expect ≥ 80% accuracy within ±5pp of Sprint Q's 85.7% baseline.
- [ ] **S150 flag-on dry-run**: extend `SKILLS_CSV=email_intent_processor,invoice_processor,aszf_rag_chat`, run nightly `RagMetricsHarness` on the 20-item HU UC2 corpus. Expect MRR@5 within ±0.02 absolute of Profile A baseline.
- [ ] **Persona carve-out**: with `SKILLS_CSV=aszf_rag_chat`, hit the RAG endpoint with `role="expert"` and `role="mentor"` — verify the executor is **not** called (legacy direct-prompt path runs unchanged). Baseline persona consumes the workflow.
- [ ] **Flag-off regression**: with all flags default, every UC golden path stays byte-stable on the existing fixtures. No skill should observe any change.
- [ ] **ST-FU-1 fix**: `pytest tests/unit/api/test_rag_collections_router.py -v` — 3/3 PASS in any test ordering.

## Rollback

1. **Per-skill rollback (primary).**
   Remove the skill from `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV` (e.g., `SKILLS_CSV="email_intent_processor,invoice_processor"` to disable `aszf_rag_chat` only). Instant runtime disable, no code rollback. The executor's `is_skill_migrated()` returns False for the dropped skill → legacy direct-prompt path runs unchanged.
2. **Sprint-wide rollback.**
   `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` (the default) kills executor calls everywhere. All three skills fall through to legacy. Identical to Sprint S tip behaviour.
3. **Per-session diff revert.**
   Each session is a single squash-merge — `git revert ee2b431` (S150) / `git revert e936eb3` (S149) / `git revert aa74e02` (S148) reverts cleanly, in any order, without touching the others.
4. **Data rollback.**
   None. Sprint T ships zero migrations and zero stored state. Workflow descriptors live in `prompts/workflows/*.yaml` (file system) or Langfuse (external).

## Open follow-ups

- **ST-FU-2** Expert/mentor persona PromptWorkflow descriptors (`aszf_rag_chain_expert`, `aszf_rag_chain_mentor`). The S150 persona-resolver is forward-compatible.
- **ST-FU-3** Consolidate per-step cost ceilings into `CostPreflightGuardrail.check_step()` (S149's local `CostEstimator` is a candidate for upstream into the Sprint N guardrail).
- **ST-FU-4** Operator parity scripts uniform `--output` flag for CI integration (carry from S149 into S150).
- **ST-FU-5** ruff-strips-imports tooling fix or single-Edit-per-import-cluster convention (documented in S150 retro).
- **SR-FU-4** Live-stack Playwright E2E for `/prompts/workflows` page (carried from Sprint R).
- **SR-FU-5** `vite build --no-emit` pre-commit hook (carried from Sprint R).
- **SR-FU-6** Workflow listing endpoint enumerates Langfuse workflows (carried from Sprint R).

Plus carried Sprint S (SS-FU-1/SS-FU-5 / SS-SKIP-2), Sprint Q (SQ-FU-1..4), Sprint P (SP-FU-1..3), Sprint N/M/J residuals.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
