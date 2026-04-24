# Sprint R (v1.5.1) — PromptWorkflow foundation

> **Cut from:** `main` @ `20ce548` (Sprint R S141 squash-merge). No external rebase dependency.

## Summary

- **`PromptWorkflow` becomes a first-class artifact.** Multi-step prompt chains can now be authored as YAML descriptors (or stored in Langfuse as `workflow:<name>` JSON-typed prompts), validated as a DAG, listed + previewed in the admin UI, and resolved by skill consumers via the new `PromptWorkflowExecutor`. The whole surface is dormant by default (`AIFLOW_PROMPT_WORKFLOWS__ENABLED=false`).
- **3 ready-to-consume descriptors ship today**: `email_intent_chain` (3 steps), `invoice_extraction_chain` (4 steps with full DAG + cost ceilings), `aszf_rag_chain` (4 steps, baseline persona). All resolve cleanly against the existing skill prompt YAMLs.
- **Per-skill code migration explicitly deferred** to S141-FU-1/2/3 — bundling 3 skill migrations in one session would have risked regressing Sprint K UC3, Sprint Q UC1, and Sprint J UC2 golden paths simultaneously. The shim is designed so each skill can adopt incrementally with its golden-path test as the gate.
- **No migration, no UI change for any skill, no behaviour change for any caller.** One additive JSONB-style settings class, one additive router (3 endpoints), one additive admin page, zero Alembic.

## Cohort delta (capability-first roadmap)

```
                          Sprint Q                    Sprint R
PromptWorkflow contract:  –                           shipped     ← new
Workflow lookup:          –                           3-layer     ← new
Admin UI list+detail:     –                           shipped     ← new
Dry-run endpoint:         –                           shipped     ← new
Skill consumers:          –                           0 (scaffold ready)
                                                      → S141-FU-1/2/3
```

## Acceptance criteria (per `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 + Sprint R prompts)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `PromptWorkflow` Pydantic model with DAG validation | ✅ | `src/aiflow/prompts/workflow.py`; 8 model unit tests |
| 2 | `PromptWorkflowLoader` filesystem YAML loader | ✅ | `src/aiflow/prompts/workflow_loader.py`; 6 loader tests |
| 3 | `PromptManager.get_workflow()` 3-layer lookup | ✅ | `src/aiflow/prompts/manager.py`; 7 manager tests |
| 4 | Flag-off → `FeatureDisabled` (HTTP 503) | ✅ | `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` default |
| 5 | Admin UI `/prompts/workflows` list + detail + Test Run | ✅ | `aiflow-admin/src/pages-new/PromptWorkflows.tsx`; sidebar nav + EN/HU locale |
| 6 | Dry-run endpoint resolves nested prompts (no LLM call) | ✅ | `GET /api/v1/prompts/workflows/{name}/dry-run`; 3 dry-run unit tests |
| 7 | `PromptWorkflowExecutor` per-skill opt-in | ✅ | `src/aiflow/prompts/workflow_executor.py`; 15 executor tests |
| 8 | 3 skill workflow descriptors that resolve | ✅ | `prompts/workflows/{email_intent,invoice_extraction,aszf_rag}_chain.yaml` |
| 9 | Sprint K UC3 / Sprint Q UC1 / Sprint J UC2 golden paths unchanged | ✅ | Zero skill code touched in this sprint |
| 10 | ≥ 30 unit tests | ✅ | 51 (24 + 10 + 17) |
| 11 | OpenAPI snapshot refreshed | ✅ | `docs/api/openapi.{json,yaml}` includes 3 new paths |
| 12 | Workflow router mounted before catch-all | ✅ | Documented inline in `app.py` + `router.tsx` |

Sprint R closes green on all 12 criteria. Per-skill consumption (the actual proof that the workflow contract works end-to-end) is queued as S141-FU-1/2/3 — each a small, focused PR with its UC golden-path test as the gate.

## What changed

### Source code

| File | Change | Session |
|---|---|---|
| `src/aiflow/prompts/workflow.py` | NEW: `PromptWorkflow` + `PromptWorkflowStep` Pydantic models with Kahn DAG validation | S139 |
| `src/aiflow/prompts/workflow_loader.py` | NEW: `PromptWorkflowLoader` filesystem YAML loader (defensive register_dir) | S139 |
| `src/aiflow/prompts/manager.py` | Extended: `get_workflow()` 3-layer lookup + `WorkflowResolutionError` | S139 |
| `src/aiflow/prompts/workflow_executor.py` | NEW: `PromptWorkflowExecutor` skill-side shim (resolution-only, no LLM) | S141 |
| `src/aiflow/core/config.py` | NEW: `PromptWorkflowSettings` (enabled, workflows_dir, cache_ttl, skills_csv) | S139 + S141 |
| `src/aiflow/core/errors.py` | NEW: `FeatureDisabled` exception (HTTP 503) | S139 |
| `src/aiflow/api/v1/prompt_workflows.py` | NEW: 3 GET endpoints (list / detail / dry-run) | S140 |
| `src/aiflow/api/v1/prompts.py` | Extended: `get_prompt_manager()` wires workflow loader + auto-registers skill prompts when flag is on | S140 |
| `src/aiflow/api/app.py` | Workflow router mounted BEFORE prompts router (catch-all shadowing fix) | S140 |
| `aiflow-admin/src/pages-new/PromptWorkflows.tsx` | NEW: React 19 + Tailwind v4 page (table + detail + dry-run) | S140 |
| `aiflow-admin/src/types/promptWorkflow.ts` | NEW: TS contracts mirroring FastAPI response models | S140 |
| `aiflow-admin/src/locales/{en,hu}.json` | `aiflow.prompts.workflows.*` + `aiflow.menu.prompts/promptWorkflows` | S140 |
| `aiflow-admin/src/router.tsx` | `/prompts/workflows` route BEFORE `/prompts/*` catch-all | S140 |
| `aiflow-admin/src/layout/Sidebar.tsx` | Settings group gains Prompts + Prompt Workflows entries | S140 |
| `prompts/workflows/uc3_intent_and_extract.yaml` | Example descriptor (3 steps, Sprint Q chain) | S139 |
| `prompts/workflows/email_intent_chain.yaml` | Sprint K UC3 chain (3 steps) | S141 |
| `prompts/workflows/invoice_extraction_chain.yaml` | Sprint Q UC1 chain (4 steps + DAG + cost ceilings) | S141 |
| `prompts/workflows/aszf_rag_chain.yaml` | Sprint J UC2 baseline persona chain (4 steps) | S141 |
| `docs/api/openapi.{json,yaml}` | OpenAPI snapshot refresh (3 new paths) | S140 |

### Tests

| File | Added | Session |
|---|---|---|
| `tests/unit/prompts/test_workflow_model.py` | 8 (DAG validation matrix) | S139 |
| `tests/unit/prompts/test_workflow_loader.py` | 6 (YAML parse + register_dir) | S139 |
| `tests/unit/prompts/test_manager_get_workflow.py` | 7 (flag off + 3-layer lookup + Langfuse hit/miss + label override + nested fail) | S139 |
| `tests/unit/core/test_prompt_workflow_settings.py` | 3 + 2 (defaults, env override, mounted, CSV) | S139 + S141 |
| `tests/unit/api/test_prompt_workflows_router.py` | 10 (gating + listing + detail + dry-run + label override) | S140 |
| `tests/unit/prompts/test_workflow_executor.py` | 15 (gating matrix + 3 real-descriptor resolution + nested-fail + label override + CSV) | S141 |

## Test plan (post-merge)

- [ ] **S141-FU-1 dry-run** (operator): set `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=invoice_processor`, then call `PromptWorkflowExecutor.resolve_for_skill("invoice_processor", "invoice_extraction_chain")` from a Python REPL. Should return the 4-step workflow with all 4 prompts resolved.
- [ ] **Admin UI smoke**: navigate to `/prompts/workflows` with the flag on, confirm the 4 descriptors (`uc3_intent_and_extract` + 3 chain workflows) appear, click Test Run on `invoice_extraction_chain`, expect JSON output containing all 4 step IDs.
- [ ] **Flag-off smoke**: with the flag default-off, the admin page should show the localized "PromptWorkflows is disabled" message; the API should return 503 `FEATURE_DISABLED`. No skill should observe any change.
- [ ] **Regression**: Sprint Q UC1 golden-path slice unchanged (≥ 75% accuracy). Sprint K UC3 4/4 E2E unchanged. Sprint J UC2 MRR@5 unchanged.
- [ ] **OpenAPI drift CI gate** should pass with the refreshed snapshot.

## Rollback

1. **Flag-off rollback (primary).**
   `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` (default) means:
   - No skill consumes the executor (S141-FU-1/2/3 hasn't shipped yet anyway).
   - The admin page renders the disabled message.
   - The 3 GET endpoints return 503.
   - `get_workflow()` raises `FeatureDisabled` from the manager.
   Zero behaviour change relative to Sprint Q tip.
2. **Per-skill rollback** (after S141-FU-1/2/3 lands):
   `AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""` keeps the flag on (admin UI works) but no skill uses the workflow path. The executor's `is_skill_migrated()` returns False for everything.
3. **Revert rollback**. 4 squash commits (#30 S139, #31 S140, #32 S141, plus this close PR) are isolated; `git revert` on any subset restores prior state. The admin UI page is additive — reverting only it leaves the backend harmless.
4. **Data rollback**. None — Sprint R ships zero migrations and zero stored state. Workflow descriptors live in `prompts/workflows/*.yaml` (file system) or Langfuse (external).

## Open follow-ups

- **S141-FU-1** Migrate `email_intent_processor` LLM classifier to consume `email_intent_chain`. Gate: Sprint K UC3 4/4 E2E.
- **S141-FU-2** Migrate `invoice_processor.workflows.process` to consume `invoice_extraction_chain`. Gate: Sprint Q UC1 golden-path slice.
- **S141-FU-3** Migrate `aszf_rag_chat.workflows.query` baseline persona to consume `aszf_rag_chain`. Gate: Sprint J UC2 MRR@5 ≥ 0.55.
- **SR-FU-4** Live-stack Playwright E2E for `/prompts/workflows` page (deferred from S140 — needs interactive shell).
- **SR-FU-5** Add `npx vite build` to local pre-commit (catch the `react-i18next`-style slip earlier).
- **SR-FU-6** Workflow listing endpoint enumerates Langfuse workflows too (today only local YAML).

Plus carried Sprint Q (SQ-FU-1..4), Sprint P (SP-FU-1..3), Sprint N/M/J residuals.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
