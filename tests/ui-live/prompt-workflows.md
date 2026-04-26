# /live-test — prompt-workflows (Sprint W / SW-2, carry from Sprint U SR-FU-4)

> **Status:** SPEC PUBLISHED — operator runs against the live admin stack on demand.
>             Mirrors Sprint N S123 + Sprint S S144 patterns. Live runs append
>             a `## Utolso futtatas` section per execution.
> **Target:** `http://localhost:5173/#/prompts/workflows`
> **API:** `http://localhost:8102` (`GET /api/v1/prompt-workflows`,
>          `GET /api/v1/prompt-workflows/{name}`,
>          `POST /api/v1/prompt-workflows/{name}/dry-run`)
> **Services:** PostgreSQL (5433, Docker), Redis (6379, Docker)
> **Stack startup:** `bash scripts/start_stack.sh --full` then `cd aiflow-admin && npm run dev`

## Journey

### Test 1 — Browse: 6 workflow descriptors listed

1. **Login** — `/#/login` → admin credentials → Bejelentkezes.
2. **Navigate** — `/#/prompts/workflows`. Sidebar nav row "Prompt Workflows"
   visible + active. Page header rendered.
3. **List assertion** — workflow descriptors table shows **6 rows** post Sprint V:
   - `email_intent_chain` (Sprint R + Sprint T S148)
   - `invoice_extraction_chain` (Sprint R + Sprint T S149; 4-step DAG)
   - `aszf_rag_chain` (Sprint R + Sprint T S150 baseline)
   - `aszf_rag_chain_expert` (Sprint U S155)
   - `aszf_rag_chain_mentor` (Sprint U S155)
   - `id_card_extraction_chain` (Sprint V SV-2; 4-step DAG with `validate.required: false`)
   - `uc3_intent_and_extract` (Sprint R example descriptor — 7th if it ships in Sprint R)
4. **Tag chips** — each row's tag set rendered (e.g. `aszf_rag_chain_expert`
   shows `sprint-v`, `sv2`, `id_card`, `hu`, `pii_high` for the id_card chain;
   `aszf` + `persona-expert` for the expert chain).
5. **Cleanup** — none (read-only).

**Pass criteria:** ≥ 6 rows, no JS errors, all expected workflow names present.

### Test 2 — Detail + Test Run dry-run

1. **From Test 1 state**, click the `aszf_rag_chain_expert` row. Detail panel
   opens.
2. **DAG visualization assertion** — 4 steps rendered in declared order:
   `rewrite_query` → `system_expert` → `answer` → `extract_citations`. Each
   step shows its `prompt_name`, `output_key`, and `depends_on` array.
3. **Click `Test Run`** — the dry-run button triggers
   `POST /api/v1/prompt-workflows/aszf_rag_chain_expert/dry-run` with default
   variable values.
4. **Result panel** — JSON output panel populates with:
   - Resolved `PromptDefinition` shape per step
   - `system` + `user` template strings post-Jinja2-render with the default
     variables
   - Compiled `messages` array per step
5. **Switch to `aszf_rag_chain_mentor` row** — detail panel re-renders with
   the mentor descriptor; `system_mentor` step uses `aszf-rag/system_prompt_mentor`
   prompt definition.
6. **Cleanup** — none.

**Pass criteria:** Detail panel mounts, DAG renders 4 steps in correct order,
Test Run produces non-empty JSON output, descriptor swap re-renders correctly.

### Test 3 — Source toggle: local vs Langfuse (post Sprint W SW-4)

This test is **Sprint W SW-4** scope (SR-FU-6 Langfuse listing surface).
Until SW-4 lands, the source toggle is not present on the page; this test
section is a pre-publish placeholder.

After SW-4:

1. **Source toggle** — `[data-testid="source-toggle"]` (segmented control)
   has 3 options: `Local YAML` / `Langfuse` / `Both` (default).
2. **Click `Local YAML`** — list filters to descriptors loaded from
   `prompts/workflows/*.yaml` only.
3. **Click `Langfuse`** — list filters to descriptors typed `workflow:<name>`
   in Langfuse. (Empty when `AIFLOW_LANGFUSE__ENABLED=false` or no
   workflow-typed prompts exist.)
4. **Click `Both`** — merged list (deduplicated by `name`).

**Pass criteria (post-SW-4):** Toggle works, lists filter correctly, no
duplicate rows when both sources have the same `name`.

## Observations + diagnostics

When live runs append `## Utolso futtatas` sections, expected diagnostics:

- The dry-run output renders the resolved prompt + compiled messages; LLM
  is **NOT** invoked. Sprint R / Sprint T's `PromptWorkflowExecutor` is
  resolution-only.
- The `aszf_rag_chain_expert` + `aszf_rag_chain_mentor` descriptors mirror
  the baseline DAG byte-for-byte except the `system_<role>` step's
  `prompt_name`. Operators verifying the per-persona route should compare
  `system_expert.prompt_name == "aszf-rag/system_prompt_expert"`.
- The `id_card_extraction_chain.validate` step has `required: false` +
  a placeholder prompt_name. The dry-run output should clearly mark this
  step as "skip-resolved" or render the placeholder prompt without crashing.

## STOP conditions

- 0 workflow descriptors listed → `prompts/workflows/*.yaml` not registered
  via `PromptManager.register_yaml_dir`. Verify the API factory boot logs
  show `prompt_manager.workflow_yaml_fallback` events for each descriptor.
- Test Run returns 503 → `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` (Sprint R
  default). Operator can flip the env without restarting if running with
  `--reload` uvicorn.
- Source toggle missing → SW-4 not yet shipped. Skip Test 3.
