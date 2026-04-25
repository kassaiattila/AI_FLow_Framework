# AIFlow [Sprint T] — Session 149 Prompt (S141-FU-2: invoice_processor → PromptWorkflow)

> **Datum:** 2026-04-25 (snapshot — adjust if session runs later)
> **Branch:** `feature/t-s149-invoice-processor-workflow` (cut from `main` after PR #40 squash-merges → new tip).
> **HEAD (expected):** Sprint T S148 squash on top of `9c76239` (S147 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S148 — `email_intent_processor` consumes `email_intent_chain` (PR #40 opened, **+10 unit / +1 integration**, full unit suite 2389 PASS / 1 skipped, Sprint K UC3 4/4 PASS). Lessons learned: (a) skill-local `PromptManager` must be built workflow-aware (`workflows_enabled` + `PromptWorkflowLoader`) when the flag is on — defensive `FeatureDisabled` catch in the executor masks misconfiguration as silent fall-through; (b) `from __future__ import annotations` does NOT save type-only imports from ruff's auto-fix when applied between edit waves — keep import + first usage in a single edit, or re-add after the formatter strips it.
> **Terv:** `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` §2 S149 + §3 gate matrix row 2 + §4 R2.
> **Session tipus:** IMPLEMENTATION (second per-skill PromptWorkflow consumer migration).

---

## 1. MISSION

Wire `prompts/workflows/invoice_extraction_chain.yaml` (4-step DAG: `classify` + `extract_header` + `extract_lines` + `validate`) into `skills/invoice_processor/workflows/process.py`. The skill's 4 direct `prompt_manager.get("invoice/...")` call sites become opt-in workflow consumers gated by `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` + `SKILLS_CSV` containing `invoice_processor`. Flag-off default = byte-stable Sprint Q UC1 path.

This is **S141-FU-2** from Sprint R retro. **R2 — schema parity** is the dominant risk: `EmailDetailResponse.extracted_fields` must remain byte-identical (Sprint Q `ExtractedFieldsCard.tsx` + the live-stack Playwright spec depend on the exact JSON shape).

S149 **does not** touch:
- The Sprint Q `_extract_invoice_fields()` Pydantic model or its constructor signature.
- `EmailDetailResponse.extracted_fields` schema (the UI is downstream of S149).
- `_intent_class_is_extract` gate from Sprint Q S135 (orchestrator decides whether to extract; the workflow only changes prompt-loading once extraction starts).
- Sprint N `CostPreflightGuardrail` — S149 *adds* per-step cost-ceiling reads (`metadata.cost_ceiling_usd 0.02 / 0.03`) but reuses the existing guardrail surface; no new env knobs.
- `parse_invoice` (step 1, docling) or `store_invoice` / `export_invoice` (steps 5 / 6).
- Any Alembic migration (head stays at 047).

Side delivery if bandwidth: **ST-FU-1** (JWT singleton CI failure in `tests/unit/api/test_rag_collections_router.py`, 3 tests). S148 deferred this; clearing it before S150 keeps Sprint S's red CI tail from following us into the close.

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint R closed with the `PromptWorkflow` foundation. Sprint T S148 (PR #40) shipped the first per-skill consumer migration: `email_intent_processor` opts into `email_intent_chain` via a module-level `PromptWorkflowExecutor` singleton + an optional `prompt_definition` kwarg plumbed through `LLMClassifier` and `HybridClassifier`. The pattern is now proven on a real skill — S149 replicates it on `invoice_processor`, where the LLM call surface is more direct (4 sequential `prompt_manager.get()` calls, no hybrid sklearn path to plumb around).

### Hova tartunk

**Sprint T migration sequence (post-S148):**
- **S149 (this) — `invoice_processor` consumes `invoice_extraction_chain`.** Gate: Sprint Q UC1 ≥ 75% / `invoice_number` ≥ 90% on the 3-fixture CI slice + ≥ 80% on the 10-fixture operator corpus (within ±5pp of Sprint Q's 85.7% baseline).
- **S150** — `aszf_rag_chat.workflows.query` baseline persona consumes `aszf_rag_chain`. Gate: Sprint J UC2 MRR@5 ≥ 0.55 Profile A.
- **S151** — Sprint T close, tag `v1.5.3`.

### Jelenlegi állapot (post-S148)

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2389 unit PASS / 1 skipped (Azure Profile B conditional)
~114 integration | 432 E2E collected (no UI surface change in S148)
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors ready, 1/3 skill consumers wired
   (email_intent_chain ✓ | invoice_extraction_chain — | aszf_rag_chain —)
```

### Key files for S149

| Role | Path |
|---|---|
| Workflow descriptor | `prompts/workflows/invoice_extraction_chain.yaml` (4 steps with `cost_ceiling_usd` metadata on `extract_header` 0.02 / `extract_lines` 0.03) |
| Skill workflow code | `skills/invoice_processor/workflows/process.py` — 4 direct `prompt_manager.get(...)` call sites: line ~219 `invoice/classifier`, ~300 `invoice/header_extractor`, ~323 `invoice/line_extractor`, plus `invoice/validator` |
| Skill `__init__` | `skills/invoice_processor/__init__.py` — needs the same flag-aware `PromptManager(workflows_enabled=…, workflow_loader=…)` build that S148 added to `email_intent_processor/__init__.py` |
| Executor | `src/aiflow/prompts/workflow_executor.py::PromptWorkflowExecutor` (resolution-only, returns `None` on flag-off) |
| Settings | `src/aiflow/core/config.py::PromptWorkflowSettings` (env prefix `AIFLOW_PROMPT_WORKFLOWS__`) |
| Cost guardrail (existing) | `src/aiflow/services/cost_guardrail/preflight.py::CostPreflightGuardrail` — Sprint N S122; consumed in S149 to read `metadata.cost_ceiling_usd` per step |
| Schema (frozen) | `EmailDetailResponse.extracted_fields` Pydantic model (Sprint Q S136) — DO NOT MODIFY |
| Golden path (CI slice) | `tests/integration/skills/test_uc1_golden_path.py` (3 fixtures) |
| Golden path (operator) | `scripts/measure_uc1_golden_path.py` + `data/fixtures/invoices_sprint_q/manifest.yaml` (10 fixtures) |
| Sprint Q UI E2E (frozen surface) | `tests/ui-live/extracted-fields-card.md` |
| S148 reference diff | `git show 8a84347` (the email_intent_processor migration — same shape, fewer call sites) |

---

## 3. ELOFELTETELEK

```bash
git switch main                                              # presumes PR #40 merged
git pull --ff-only origin main
git checkout -b feature/t-s149-invoice-processor-workflow
git log --oneline -5                                          # confirm S148 squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current        # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # 2389 collected (or +new)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc1_golden_path.py --collect-only -q 2>&1 | tail -3
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
```

Stop, ha:
- PR #40 not yet merged → wait or escalate; the S149 branch must start from a clean S148 tip on `main`.
- Alembic head ≠ 047 → drift; investigate before opening S149.
- `test_uc1_golden_path.py --collect-only` doesn't list the expected fixtures → Sprint Q regression upstream; halt.
- `git status` dirty → finish or stash first.

---

## 4. FELADATOK

### LEPES 1 — Read-the-room

```bash
# 1. The descriptor + cost-ceiling metadata
prompts/workflows/invoice_extraction_chain.yaml

# 2. The 4 direct prompt-loading call sites in process.py
skills/invoice_processor/workflows/process.py        # search for prompt_manager.get(

# 3. Skill __init__ — copy the workflow-aware-manager pattern from S148
skills/invoice_processor/__init__.py
skills/email_intent_processor/__init__.py            # reference: same shape

# 4. The executor scaffold (already learned in S148, re-confirm)
src/aiflow/prompts/workflow_executor.py

# 5. Sprint N cost-guardrail surface for the cost-ceiling check
src/aiflow/services/cost_guardrail/preflight.py
src/aiflow/core/config.py    # CostGuardrailSettings + PromptWorkflowSettings

# 6. The frozen extraction schema — to confirm zero-touch contract
src/aiflow/api/v1/emails.py  # search for ExtractedFieldsResponse / extracted_fields
src/aiflow/services/email_connector/models.py
```

### LEPES 2 — Wire the executor (mirror S148's shape)

```python
# skills/invoice_processor/__init__.py — same workflow-aware-PromptManager
# pattern as skills/email_intent_processor/__init__.py from S148 (just
# copy + adjust the comment).

# skills/invoice_processor/workflows/process.py — at the top, alongside
# the existing `from skills.invoice_processor import models_client,
# prompt_manager` line, add:

from aiflow.core.config import get_settings
from aiflow.prompts.schema import PromptDefinition
from aiflow.prompts.workflow_executor import PromptWorkflowExecutor

WORKFLOW_NAME = "invoice_extraction_chain"
SKILL_NAME = "invoice_processor"

# Module-level singleton — same lifetime as prompt_manager.
prompt_workflow_executor = PromptWorkflowExecutor(
    manager=prompt_manager,
    settings=get_settings().prompt_workflows,
)
```

Then introduce a small per-request resolver helper (call this once at the start of `extract_invoice_data` or wherever the LLM-call sequence begins):

```python
def _resolve_workflow_prompts() -> dict[str, PromptDefinition] | None:
    """Resolve invoice_extraction_chain step prompts, or None on fall-through."""
    resolved = prompt_workflow_executor.resolve_for_skill(SKILL_NAME, WORKFLOW_NAME)
    if resolved is None:
        return None
    workflow, prompt_map = resolved
    logger.info(
        "invoice_processor.workflow_resolved",
        workflow=workflow.name,
        steps=list(prompt_map.keys()),
    )
    return prompt_map
```

At each of the 4 `prompt_manager.get("invoice/...")` call sites, gate on the resolved map:

```python
prompt = (workflow_prompts.get("classify") if workflow_prompts else None) \
         or prompt_manager.get("invoice/classifier")
```

The `validate` step has `required: false` in the descriptor — keep the legacy "always validate" behaviour on flag-off; on flag-on respect the `required` flag (skip if the resolved descriptor omits it). Mirror Sprint R's design intent (`PromptWorkflowStep.required: bool = True` default → omit only if explicit).

### LEPES 3 — Cost-ceiling enforcement (R2 mitigation)

The descriptor declares `metadata.cost_ceiling_usd` on `extract_header` (0.02) and `extract_lines` (0.03). Wire these into `CostPreflightGuardrail` per step:

```python
# Pseudocode — adapt to actual CostPreflightGuardrail signature
ceiling = workflow_prompts["extract_header"].metadata.get("cost_ceiling_usd") if workflow_prompts else None
if ceiling is not None:
    decision = cost_guardrail.preflight(
        tenant_id=tenant_id,
        projected_usd=estimator.estimate(...),
        explicit_ceiling_usd=ceiling,  # NEW per-step override
    )
    if decision.refused:
        # Surface as a structured error per Sprint N pattern; do NOT
        # silently swallow — tenant-budget enforcement contract relies
        # on visibility.
        ...
```

Confirm the guardrail's existing surface accepts a per-call ceiling override; if it doesn't, do **not** add a new arg in S149 (out of scope) — instead clamp the projected-usd locally and surface a `CostGuardrailRefused` from the workflow. Document the choice in the retro.

**Important:** `metadata.cost_ceiling_usd` must remain advisory on flag-off — the legacy `prompt_manager.get(...)` path doesn't see metadata. Don't backport ceiling enforcement to flag-off code paths in S149.

### LEPES 4 — Tests

| Test | What it asserts | File |
|---|---|---|
| `test_workflow_prompts_resolved_when_flag_on` | Flag-on + `invoice_processor` in CSV → 4 step prompts resolved; classifier / header / lines / validator each receive the workflow PromptDefinition | `tests/unit/skills/invoice_processor/test_workflow_migration.py` (new) |
| `test_flag_off_uses_legacy_prompt_manager_get` | `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` → 4 manager.get(...) calls, 0 executor resolution | same |
| `test_skill_not_in_csv_falls_through` | Flag-on but CSV missing skill → fall-through to legacy | same |
| `test_validate_step_required_false_can_be_omitted` | Descriptor without `validate` → skill skips that LLM call on flag-on; flag-off still validates | same |
| `test_descriptor_lookup_failure_falls_through` | `WorkflowResolutionError` → executor returns None; legacy 4-step path runs | same |
| `test_cost_ceiling_enforced_on_extract_header` | Projected cost > 0.02 USD → `CostGuardrailRefused` surfaced; flag-off path unaffected | same |
| `test_cost_ceiling_enforced_on_extract_lines` | Projected cost > 0.03 USD → refused | same |
| `test_extracted_fields_schema_byte_identical` | Flag-off vs flag-on on a fixed mock LLM output → identical `extracted_fields` JSON (R2 contract) | same |
| **integration** `test_invoice_processor_workflow_real` | Real PG + real docling + real OpenAI on `001_invoice_march.eml`; flag-on `invoice_number` matches Sprint Q baseline byte-identical | `tests/integration/skills/test_invoice_processor_workflow.py` (new) |

Add `@test_registry` headers per `tests/CLAUDE.md`. Skip the integration test by default unless `OPENAI_API_KEY` is set (mirror S148's pattern in `tests/integration/skills/test_email_intent_workflow.py`).

### LEPES 5 — Golden-path gate (BLOKKOLO)

```bash
# Sprint Q UC1 3-fixture CI slice — must remain ≥ 75% / invoice_number ≥ 90%
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc1_golden_path.py -v

# Operator measurement on full 10-fixture corpus (flag-OFF — baseline)
.venv/Scripts/python.exe scripts/measure_uc1_golden_path.py --output docs/uc1_s149_flag_off.md

# Operator measurement on full 10-fixture corpus (flag-ON — parity)
AIFLOW_PROMPT_WORKFLOWS__ENABLED=true \
AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=invoice_processor \
.venv/Scripts/python.exe scripts/measure_uc1_golden_path.py --output docs/uc1_s149_flag_on.md
```

**Threshold:**
- CI slice: overall ≥ 75% / `invoice_number` ≥ 90%.
- Full corpus flag-off: ≥ 80% accuracy (Sprint Q baseline 85.7%, allow ±5pp).
- Full corpus flag-on: byte-identical `extracted_fields` JSON on ≥ 9/10 fixtures (R2 contract; LLM nondeterminism allows ±1 fixture variance).

If any gate fails → halt, write follow-up note, **do not** push. Diagnostic checks first:
1. Diff the flag-off vs flag-on JSON per-fixture; identify which field drifted.
2. Confirm `_extract_invoice_fields()` Pydantic constructor receives the same args in both paths.
3. Verify the `validate` step's `required: false` skip path isn't dropping a field the legacy path computes.

### LEPES 6 — Lint + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/invoice_processor/  # 0 error
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/skills/invoice_processor/ -q
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc1_golden_path.py -q

git add skills/invoice_processor/__init__.py \
        skills/invoice_processor/workflows/process.py \
        tests/unit/skills/invoice_processor/ \
        tests/integration/skills/test_invoice_processor_workflow.py
git commit -m "feat(sprint-t): S149 — invoice_processor consumes invoice_extraction_chain (S141-FU-2)"
git push -u origin feature/t-s149-invoice-processor-workflow
gh pr create --base main --head feature/t-s149-invoice-processor-workflow \
  --title "Sprint T S149 — invoice_processor → PromptWorkflow (S141-FU-2)"
```

Then `/session-close S149` — which queues S150 (`aszf_rag_chat` baseline persona).

---

## 5. STOP FELTETELEK

**HARD:**
1. PR #40 (Sprint T S148) not yet merged — wait until `main` has the email_intent_processor migration squash.
2. Sprint Q UC1 CI slice fails on flag-off (`test_uc1_golden_path.py` < 75% overall or < 90% `invoice_number`) → halt; the executor wrapper has leaked into legacy path. Revert the diff entirely.
3. Flag-on parity > ±1 fixture JSON variance on 10-fixture corpus → halt; R2 schema-parity contract violated.
4. `_extract_invoice_fields()` Pydantic constructor signature changes — that's a refactor scope-bomb; back out.
5. `EmailDetailResponse.extracted_fields` schema diff (any new/removed/renamed field) → halt; the live-stack Playwright spec breaks.
6. `CostGuardrailRefused` thrown on a flag-off run → halt; cost-ceiling enforcement leaked to legacy path.
7. Operator wants to refactor docling parse step or the storage step — out of scope for S149.

**SOFT:**
- `OPENAI_API_KEY` not set → integration test skips; document, proceed.
- `CostPreflightGuardrail` doesn't accept a per-call ceiling override → skip cost enforcement in S149 with a follow-up note; the migration still ships the workflow consumption.
- ST-FU-1 JWT singleton fix grew beyond a side delivery → carry to S150 / S151 instead.

---

## 6. SESSION VEGEN

```
/session-close S149
```

The `/session-close` will:
- Validate lint + unit + e2e collect.
- Re-run Sprint Q UC1 CI slice + 10-fixture flag-on parity as the final gate.
- Stage + commit the migration diff.
- Push the branch.
- Generate `session_prompts/NEXT.md` for S150 — `aszf_rag_chat.workflows.query` baseline persona.

---

## 7. SKIPPED-ITEMS TRACKER (carry from S148)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-1 | Sprint T plan §5 | JWT singleton CI failure (3 tests in `test_rag_collections_router.py`) | **Side delivery in S149 if bandwidth** — pin per-test fresh `AuthProvider` + clear secret cache fixture |
| ST-FU-2 | Sprint T plan §5 | Expert/mentor persona descriptors (`aszf_rag_chain_expert/_mentor`) | Post-Sprint-T |
| SR-FU-4/5/6 | Sprint R retro | Live-stack Playwright + vite-build hook + Langfuse listing | Sprint T side delivery if bandwidth |

S149 closes `S141-FU-2` (kicks `S141-FU-3` to S150).
