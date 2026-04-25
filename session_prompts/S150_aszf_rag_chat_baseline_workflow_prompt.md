# AIFlow [Sprint T] — Session 150 Prompt (S141-FU-3: aszf_rag_chat baseline → PromptWorkflow)

> **Datum:** 2026-04-25 (snapshot — adjust if session runs later)
> **Branch:** `feature/t-s150-aszf-rag-baseline-workflow` (cut from `main` after PR #41 squash-merges → new tip).
> **HEAD (expected):** Sprint T S149 squash on top of `aa74e02` (S148 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S149 — `invoice_processor` consumes `invoice_extraction_chain` (PR #41 opened, **+15 unit / +1 integration**, full unit suite 2404 PASS / 1 skipped, Sprint Q UC1 CI slice PASS, real-LLM flag-on parity PASS on 001_hu_simple.pdf). Lessons learned: (a) the descriptor's `validate` step `required: false` keyword can map to a *pure-Python* legacy step — no LLM gate needed when the legacy code path doesn't invoke `prompt_manager.get(...)` at all; (b) when `CostPreflightGuardrail` doesn't accept a per-call ceiling override, local `CostEstimator` + explicit `CostGuardrailRefused` raise (escaping the bare `except Exception`) is the cleanest pattern for descriptor-declared per-step ceilings.
> **Terv:** `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` §2 S150 + §3 gate matrix row 3 + §4 R3.
> **Session tipus:** IMPLEMENTATION (third per-skill PromptWorkflow consumer migration; Sprint T sequence closes).

---

## 1. MISSION

Wire `prompts/workflows/aszf_rag_chain.yaml` (4-step DAG: `rewrite_query` + `system_baseline` + `answer` + `extract_citations`) into `skills/aszf_rag_chat/workflows/query.py` for the **baseline persona only**. The expert / mentor variants pick a different `system_prompt_<role>.yaml` at runtime; those would need separate workflows (deferred — see plan §11 Out of scope).

The migration adds a `_resolve_workflow_for_persona(role)` helper that returns the resolved `aszf_rag_chain` `(workflow, prompt_map)` tuple for `role == "baseline"` and `None` (legacy fallback) for `role in ("expert", "mentor")`. Flag-off default = byte-stable Sprint J UC2 path on every persona.

This is **S141-FU-3** from Sprint R retro. **R3 — persona variant carve-out** is the dominant risk: the legacy code branches on `role` to pick `system_prompt_baseline.yaml` / `system_prompt_expert.yaml` / `system_prompt_mentor.yaml`; only baseline gets the workflow path.

S150 **does not** touch:
- The expert / mentor persona prompts (`system_prompt_expert.yaml`, `system_prompt_mentor.yaml`) — they stay on the legacy `prompt_manager.get(...)` path on every flag state.
- `RAGEngineService.query()` retrieval surface (Sprint S S143 ProviderRegistry refactor) — S150 only changes the prompt-loading layer of the *answer-generation* leg.
- `tests/integration/skills/test_uc2_rag.py` schema or the 20-item HU UC2 corpus (`data/fixtures/rag_metrics/uc2_aszf_query_set.json`).
- The nightly `RagMetricsHarness` (Sprint S S145) — it already runs flag-off; the parity check uses it as the baseline.
- The reranker fallback path (Sprint J S103 OSError shim) — out of scope.
- Any Alembic migration (head stays at 047).

Side delivery if bandwidth: **ST-FU-1** (JWT singleton CI failure in `tests/unit/api/test_rag_collections_router.py`, 3 tests). S148 + S149 both deferred this; S150 is the last chance before Sprint T close — clearing it keeps Sprint S's red CI tail from following us into the close.

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint R closed with the `PromptWorkflow` foundation. Sprint T S148 + S149 (PRs #40 + #41) shipped the first two per-skill consumer migrations: `email_intent_processor` (1 LLM call site, hybrid ML+LLM short-circuit preserved) and `invoice_processor` (3 LLM call sites, per-step cost ceilings). The pattern is now proven on two skills with very different LLM-call surfaces — S150 closes the loop on the third, where the additional twist is **persona-variant dispatch**: only the baseline persona migrates.

### Hova tartunk

**Sprint T sequence end-state (post-S150):**
- S148 ✓ — `email_intent_processor` consumes `email_intent_chain`.
- S149 ✓ — `invoice_processor` consumes `invoice_extraction_chain`.
- **S150 (this) — `aszf_rag_chat` baseline persona consumes `aszf_rag_chain`.** Gate: Sprint J UC2 MRR@5 ≥ 0.55 Profile A; flag-on parity within ±0.02 absolute MRR@5 on the 20-item HU UC2 corpus.
- S151 — Sprint T close, tag `v1.5.3`.

### Jelenlegi állapot (post-S149)

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2404 unit PASS / 1 skipped (Azure Profile B conditional)
~115 integration | 432 E2E collected (no UI surface change in S148/S149)
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors ready, 2/3 skill consumers wired
   (email_intent_chain ✓ | invoice_extraction_chain ✓ | aszf_rag_chain —)
```

### Key files for S150

| Role | Path |
|---|---|
| Workflow descriptor | `prompts/workflows/aszf_rag_chain.yaml` (4 steps; check whether any step has `required: false` or `metadata.cost_ceiling_usd`) |
| Skill workflow code | `skills/aszf_rag_chat/workflows/query.py` — search for `prompt_manager.get(...)` + role dispatch (`system_prompt_baseline` / `_expert` / `_mentor`) |
| Skill `__init__` | `skills/aszf_rag_chat/__init__.py` — needs the same flag-aware `PromptManager(workflows_enabled=…, workflow_loader=…)` build that S148 / S149 added (mirror S149's `__init__.py` shape) |
| Executor | `src/aiflow/prompts/workflow_executor.py::PromptWorkflowExecutor` (resolution-only; battle-tested on 2 skills now) |
| Settings | `src/aiflow/core/config.py::PromptWorkflowSettings` (env prefix `AIFLOW_PROMPT_WORKFLOWS__`) |
| Sprint J UC2 integration | `tests/integration/skills/test_uc2_rag.py` (existing; do NOT modify schema) |
| Sprint S S145 nightly harness | `src/aiflow/services/rag_metrics/` + `scripts/run_nightly_rag_metrics.py` + `data/fixtures/rag_metrics/uc2_aszf_query_set.json` |
| S148 reference diff | `git show 8a84347` (`email_intent_processor` migration) |
| S149 reference diff | `git show 62eacd4` (`invoice_processor` migration — closer match for "multi-step + opt-in skill init") |

---

## 3. ELOFELTETELEK

```bash
git switch main                                              # presumes PR #41 merged
git pull --ff-only origin main
git checkout -b feature/t-s150-aszf-rag-baseline-workflow
git log --oneline -5                                          # confirm S149 squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current        # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # 2404 collected (or +new)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc2_rag.py --collect-only -q 2>&1 | tail -3
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
```

Stop, ha:
- PR #41 not yet merged → wait or escalate; the S150 branch must start from a clean S149 tip on `main`.
- Alembic head ≠ 047 → drift; investigate before opening S150.
- `test_uc2_rag.py --collect-only` doesn't list the expected fixtures → Sprint J/S regression upstream; halt.
- `git status` dirty → finish or stash first.

---

## 4. FELADATOK

### LEPES 1 — Read-the-room

```bash
# 1. The descriptor
prompts/workflows/aszf_rag_chain.yaml

# 2. The query workflow with role dispatch
skills/aszf_rag_chat/workflows/query.py        # search for prompt_manager.get( + role / persona

# 3. Skill __init__ — copy the workflow-aware-manager pattern from S149
skills/aszf_rag_chat/__init__.py
skills/invoice_processor/__init__.py            # reference: same shape

# 4. The 3 role-specific system prompts (only baseline migrates)
skills/aszf_rag_chat/prompts/system_prompt_baseline.yaml
skills/aszf_rag_chat/prompts/system_prompt_expert.yaml
skills/aszf_rag_chat/prompts/system_prompt_mentor.yaml

# 5. Sprint J / S retrieval-quality artefacts (gate inputs)
tests/integration/skills/test_uc2_rag.py
data/fixtures/rag_metrics/uc2_aszf_query_set.json
src/aiflow/services/rag_metrics/__init__.py
```

### LEPES 2 — Wire the executor (mirror S149's shape)

```python
# skills/aszf_rag_chat/__init__.py — same workflow-aware-PromptManager
# pattern as skills/invoice_processor/__init__.py from S149 (just copy + adjust comment).

# skills/aszf_rag_chat/workflows/query.py — at the top, alongside
# `from skills.aszf_rag_chat import models_client, prompt_manager`, add:

from aiflow.core.config import get_settings
from aiflow.prompts.schema import PromptDefinition
from aiflow.prompts.workflow import PromptWorkflow
from aiflow.prompts.workflow_executor import PromptWorkflowExecutor

WORKFLOW_NAME = "aszf_rag_chain"
SKILL_NAME = "aszf_rag_chat"
BASELINE_PERSONA = "baseline"

# Module-level singleton — same lifetime as prompt_manager.
prompt_workflow_executor = PromptWorkflowExecutor(
    manager=prompt_manager,
    settings=get_settings().prompt_workflows,
)


def _resolve_workflow_for_persona(role: str) -> tuple[PromptWorkflow, dict[str, PromptDefinition]] | None:
    """Resolve aszf_rag_chain for the baseline persona only.

    Expert / mentor personas keep the legacy single-prompt path on every
    flag state (out of scope per Sprint T plan §6 R3).
    """
    if role != BASELINE_PERSONA:
        return None
    return prompt_workflow_executor.resolve_for_skill(SKILL_NAME, WORKFLOW_NAME)
```

At each `prompt_manager.get("aszf-rag-chat/...")` call site that the workflow covers (rewrite_query / system_baseline / answer / extract_citations), gate on the resolved map for baseline persona only:

```python
resolved = _resolve_workflow_for_persona(role)
if resolved is not None:
    workflow, prompt_map = resolved
    rewrite_prompt = prompt_map.get("rewrite_query") or prompt_manager.get("aszf-rag-chat/rewrite_query")
    # ... same shape for system_baseline / answer / extract_citations
else:
    rewrite_prompt = prompt_manager.get("aszf-rag-chat/rewrite_query")
    # ... legacy fall-through
```

If the descriptor declares `extract_citations` (or any other step) with `required: false` and the existing legacy code already invokes that prompt unconditionally, **keep the legacy "always run" behaviour on flag-off**; on flag-on respect `required: false` and skip when the descriptor omits it. (Mirrors S149's handling of the `validate` step — the `required: false` keyword is honored only on flag-on.)

### LEPES 3 — Cost guardrail (only if descriptor declares ceilings)

Check `aszf_rag_chain.yaml` for `metadata.cost_ceiling_usd` on any step. If present, mirror S149's `_enforce_step_cost_ceiling` pattern (local `CostEstimator` + `CostGuardrailRefused` raise that escapes the bare except). If absent, do **not** add cost ceilings in S150 — that's a separate descriptor change, out of scope.

### LEPES 4 — Tests

| Test | What it asserts | File |
|---|---|---|
| `test_baseline_persona_resolves_workflow` | Flag-on + `aszf_rag_chat` in CSV + `role="baseline"` → 4 step prompts resolved; rewrite / system_baseline / answer / extract_citations each receive the workflow PromptDefinition | `tests/unit/skills/aszf_rag_chat/test_workflow_migration.py` (new) |
| `test_expert_persona_falls_through` | `role="expert"` returns None even when flag-on + skill in CSV | same |
| `test_mentor_persona_falls_through` | `role="mentor"` returns None even when flag-on + skill in CSV | same |
| `test_flag_off_uses_legacy_prompt_manager_get` | `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` on baseline persona → legacy 4-prompt resolution | same |
| `test_skill_not_in_csv_falls_through` | Flag-on, baseline role, but CSV missing skill → fall-through to legacy | same |
| `test_descriptor_lookup_failure_falls_through` | `WorkflowResolutionError` → resolver returns None; legacy path runs | same |
| `test_required_false_step_can_be_omitted_on_flag_on` | If descriptor declares any step `required: false` → flag-on can skip; flag-off always runs | same (skip if descriptor has no such step) |
| **integration** `test_aszf_rag_baseline_workflow_real` | Real PG + real BGE-M3 weights; 5 baseline-persona queries from `uc2_aszf_query_set.json`; flag-on MRR@5 within ±0.02 absolute of flag-off | `tests/integration/skills/test_aszf_rag_baseline_workflow.py` (new) |

Add `@test_registry` headers per `tests/CLAUDE.md`. Skip the integration test by default unless `OPENAI_API_KEY` + BGE-M3 weights are available (mirror S149's pattern in `tests/integration/skills/test_invoice_processor_workflow.py`).

### LEPES 5 — Golden-path gate (BLOKKOLO)

```bash
# Sprint J UC2 integration test — must PASS on flag-off
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc2_rag.py -v

# Nightly MRR@5 harness on the 20-item HU UC2 corpus (flag-OFF — baseline)
AIFLOW_RUN_NIGHTLY_RAG_METRICS=1 \
.venv/Scripts/python.exe scripts/run_nightly_rag_metrics.py --output docs/uc2_s150_flag_off.jsonl

# Same harness flag-ON — parity check
AIFLOW_PROMPT_WORKFLOWS__ENABLED=true \
AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=aszf_rag_chat \
AIFLOW_RUN_NIGHTLY_RAG_METRICS=1 \
.venv/Scripts/python.exe scripts/run_nightly_rag_metrics.py --output docs/uc2_s150_flag_on.jsonl
```

**Threshold:**
- `test_uc2_rag.py` flag-off: PASS (Sprint J / S baseline preserved).
- 20-item harness flag-off MRR@5 ≥ 0.55 (Sprint J Profile A baseline).
- 20-item harness flag-on MRR@5 within ±0.02 absolute of flag-off (R3 parity contract).

If any gate fails → halt, write follow-up note, **do not** push. Diagnostic checks first:
1. Diff the resolved `system_baseline` PromptDefinition vs the legacy `system_prompt_baseline.yaml` content — they must produce identical compiled messages.
2. Confirm role dispatch — `_resolve_workflow_for_persona("expert")` and `("mentor")` must return None on every flag state.
3. Verify the executor's workflow_cache TTL isn't masking a stale descriptor.

### LEPES 6 — ST-FU-1 side delivery (if bandwidth)

```bash
# JWT singleton CI failure in tests/unit/api/test_rag_collections_router.py (3 tests)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/api/test_rag_collections_router.py -v
```

If the 3 failures are still present, pin a per-test fresh `AuthProvider` + clear secret cache fixture. If the fix is large (>50 lines), defer to S151 and document.

### LEPES 7 — Lint + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/aszf_rag_chat/  # 0 error
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/skills/aszf_rag_chat/ -q
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc2_rag.py -q

git add skills/aszf_rag_chat/__init__.py \
        skills/aszf_rag_chat/workflows/query.py \
        tests/unit/skills/aszf_rag_chat/ \
        tests/integration/skills/test_aszf_rag_baseline_workflow.py
git commit -m "feat(sprint-t): S150 — aszf_rag_chat baseline → PromptWorkflow (S141-FU-3)"
git push -u origin feature/t-s150-aszf-rag-baseline-workflow
gh pr create --base main --head feature/t-s150-aszf-rag-baseline-workflow \
  --title "Sprint T S150 — aszf_rag_chat baseline → PromptWorkflow (S141-FU-3)"
```

Then `/session-close S150` — which queues S151 (Sprint T close).

---

## 5. STOP FELTETELEK

**HARD:**
1. PR #41 (Sprint T S149) not yet merged — wait until `main` has the invoice_processor migration squash.
2. `test_uc2_rag.py` fails on flag-off → halt; the executor wrapper has leaked into legacy path. Revert the diff entirely.
3. 20-item harness flag-on MRR@5 drift > ±0.02 absolute → halt; R3 parity contract violated.
4. `_resolve_workflow_for_persona("expert"|"mentor")` ever returns non-None → halt; persona carve-out leaked. Out of scope.
5. Any change to `system_prompt_expert.yaml` / `system_prompt_mentor.yaml` → halt; non-baseline personas are explicitly out of scope.
6. Reranker / pgvector / BGE-M3 retrieval surface modified → halt; only the prompt-loading leg of the answer-generation step migrates.
7. Operator wants to migrate expert/mentor personas in S150 → halt + escalate; this needs new descriptors (`aszf_rag_chain_expert`, `aszf_rag_chain_mentor`) which is plan §6 ST-FU-2 scope, not S150.

**SOFT:**
- `OPENAI_API_KEY` not set → integration test skips; document, proceed.
- BGE-M3 weights not cached → harness skip; document, proceed (Sprint S S145's `actions/cache@v4` covers CI).
- ST-FU-1 (JWT singleton) fix grew beyond a side delivery → carry to S151 close.

---

## 6. SESSION VEGEN

```
/session-close S150
```

The `/session-close` will:
- Validate lint + unit + e2e collect.
- Re-run Sprint J UC2 integration + 20-item flag-on parity as the final gate.
- Stage + commit the migration diff.
- Push the branch.
- Generate `session_prompts/NEXT.md` for S151 — Sprint T close.

---

## 7. SKIPPED-ITEMS TRACKER (carry from S147 / S148 / S149)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-1 | Sprint T plan §5 | JWT singleton CI failure (3 tests in `test_rag_collections_router.py`) | **Side delivery in S150 if bandwidth** — pin per-test fresh `AuthProvider` + clear secret cache fixture |
| ST-FU-2 | Sprint T plan §11 | Expert/mentor persona descriptors (`aszf_rag_chain_expert/_mentor`) | Post-Sprint-T |
| SR-FU-4/5/6 | Sprint R retro | Live-stack Playwright + vite-build hook + Langfuse listing | Sprint T side delivery if bandwidth |
| **NEW from S149** | session_prompts/S149 §3 step 5 | Operator full 10-fixture flag-on parity script needs `--output` flag | S151 close (small refactor) |

S150 closes `S141-FU-3`. S151 ships Sprint T close + tag `v1.5.3`.
