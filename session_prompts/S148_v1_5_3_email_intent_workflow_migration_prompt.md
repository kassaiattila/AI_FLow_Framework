# AIFlow [Sprint T] — Session 148 Prompt (S141-FU-1: email_intent_processor → PromptWorkflow)

> **Datum:** 2026-04-25 (snapshot date — adjust if session runs later)
> **Branch:** `feature/t-s148-email-intent-workflow` (cut from `main` after PR #39 squash-merges → new tip).
> **HEAD (expected):** Sprint T S147 squash on top of `20fb792` (Sprint S close).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S147 — Sprint T kickoff. `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` + `docs/sprint_t_plan.md` + carry-forward reconcile (Clock-seam stale carry dropped, "1 skipped" inventoried as conditional Azure Profile B). PR #39 opened against `main`.
> **Terv:** `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` §2 S148 + §3 gate matrix row 1 + §4 R1.
> **Session tipus:** IMPLEMENTATION (first per-skill PromptWorkflow consumer migration).

---

## 1. MISSION

Wire `prompts/workflows/email_intent_chain.yaml` (the 3-step descriptor: `classify` + `extract_entities` + `score_priority`) into `skills/email_intent_processor/workflows/classify.py` so the skill's **LLM-aware classifier path** opt-in consumes the workflow descriptor when the operator flips two flags. **Zero behaviour change** with flag-off: `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` (default) keeps every existing call site on the legacy direct-prompt path byte-for-byte.

This is **S141-FU-1** from Sprint R retro — the smallest-blast-radius migration first per Sprint R decision SR-6 (closes `S141-FU-1` follow-up; `S141-FU-2/3` follow in S149 / S150).

S148 **does not** touch:
- The sklearn classifier path (Sprint K body-only baseline).
- The Sprint P attachment-signal early-return / `_keywords_first` short-circuit.
- The Sprint P strategy switch (`SKLEARN_ONLY` / `SKLEARN_FIRST` / `SKLEARN_THEN_LLM`).
- `EmailDetailResponse.intent` schema or the 25-fixture corpus from Sprint P.
- Steps 1 / 2 / 6 / 7 of the 7-step pipeline (`parse_email`, `process_attachments`, `decide_routing`, `log_result`).
- Any Alembic migration (head stays at 047).
- Any UI surface.

S148 **may** also pick up `ST-FU-1` (JWT singleton CI-only failure in `tests/unit/api/test_rag_collections_router.py`) as a side delivery if bandwidth allows — clears Sprint S's red CI tail before S149.

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint R closed 2026-05-14 with the `PromptWorkflow` foundation: contract + admin UI + executor scaffold + 3 ready descriptors. **0 skill consumes the executor today.** Sprint S (S143 / S144 / S145) shipped functional vector DB; PR #38 admin-merged 2026-04-25. Sprint T S147 (PR #39) authored the migration plan + reconciled stale carries. Sprint T's job in S148–S150 is to wire each descriptor into its skill, gated by the use-case golden path.

### Hova tartunk

**Sprint T migration sequence:**
- **S148 (this) — `email_intent_processor` consumes `email_intent_chain`.** Gate: Sprint K UC3 4/4 golden-path E2E (`tests/e2e/test_uc3_emails_golden_path.py`) + 25-fixture flag-on label parity ±1 fixture.
- **S149** — `invoice_processor.workflows.process` consumes `invoice_extraction_chain`. Gate: Sprint Q UC1 ≥ 75% / invoice_number ≥ 90%.
- **S150** — `aszf_rag_chat.workflows.query` baseline persona consumes `aszf_rag_chain`. Gate: Sprint J UC2 MRR@5 ≥ 0.55 Profile A.
- **S151** — Sprint T close, tag `v1.5.3`.

### Jelenlegi állapot (post-S147)

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2379 unit PASS / 1 skipped (Azure Profile B conditional, see docs/quarantine.md)
~113 integration | 432 E2E collected (no UI surface change in S147)
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors ready (email_intent_chain, invoice_extraction_chain,
                                    aszf_rag_chain) — 0 skills consume them today
```

### Key files for S148

| Role | Path |
|---|---|
| Workflow descriptor | `prompts/workflows/email_intent_chain.yaml` (3 steps: classify / extract_entities / score_priority) |
| Skill workflow code | `skills/email_intent_processor/workflows/classify.py` (steps 3 / 4 / 5 are the LLM-aware legs to wire) |
| Hybrid classifier | `skills/email_intent_processor/classifiers/HybridClassifier` + `LLMClassifier` |
| Executor scaffold | `src/aiflow/prompts/workflow_executor.py::PromptWorkflowExecutor` (resolution-only, returns `None` on flag-off) |
| Settings | `src/aiflow/core/config.py::PromptWorkflowSettings` (`enabled` + `skills_csv` + `.skills` parsed property) |
| Per-prompt path (legacy) | `LLMClassifier(prompts: ["email-intent/classifier", "email-intent/entity_extractor", "email-intent/priority_scorer"])` |
| Golden path | `tests/e2e/test_uc3_emails_golden_path.py` (Sprint K — 4 emails) |
| Flag-on parity corpus | Sprint P 25-fixture set (drives `tests/integration/skills/test_uc3_attachment_intent_classify.py`) |

---

## 3. ELOFELTETELEK

```bash
git switch main                                              # presumes PR #39 merged
git pull --ff-only origin main
git checkout -b feature/t-s148-email-intent-workflow
git log --oneline -5                                          # confirm S147 squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current  # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # 2380 collected
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e/test_uc3_emails_golden_path.py --collect-only -q 2>&1 | tail -3
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
```

Stop, ha:
- PR #39 not yet merged → wait or escalate; the S148 branch must start from a clean Sprint T tip on `main`.
- Alembic head ≠ 047 → drift; investigate before opening S148.
- `test_uc3_emails_golden_path.py --collect-only` doesn't list 4 tests → Sprint K regression upstream; halt.
- `git status` dirty → finish or stash first.

---

## 4. FELADATOK

### LEPES 1 — Read-the-room

Open these in parallel before writing any code:

```bash
# 1. The descriptor itself
prompts/workflows/email_intent_chain.yaml

# 2. The current LLM call surface in classify.py (steps 3 / 4 / 5)
skills/email_intent_processor/workflows/classify.py    # classify_intent / extract_entities / score_priority

# 3. The hybrid + LLM classifier classes
skills/email_intent_processor/classifiers/__init__.py
skills/email_intent_processor/classifiers/llm_classifier.py
skills/email_intent_processor/classifiers/hybrid_classifier.py

# 4. Executor scaffold contract
src/aiflow/prompts/workflow_executor.py

# 5. Settings flag
src/aiflow/core/config.py    # PromptWorkflowSettings, .skills_csv, .skills
```

Note: `email_intent_chain.yaml` declares `score_priority` and `extract_entities` as `required: false` — the executor must surface that and the skill must respect it (legacy classifier currently runs all three unconditionally; the descriptor allows either to skip when classifier already disambiguates).

### LEPES 2 — Wire the executor (the smallest possible diff)

Inside `skills/email_intent_processor/workflows/classify.py`, instantiate a module-level `PromptWorkflowExecutor` next to the existing `LLMClassifier` singleton. Inject `prompt_manager` (already imported) + `PromptWorkflowSettings` from `aiflow.core.config`.

```python
from aiflow.core.config import get_settings
from aiflow.prompts.workflow_executor import PromptWorkflowExecutor

# Add next to existing singletons (line ~83)
prompt_workflow_executor = PromptWorkflowExecutor(
    manager=prompt_manager,
    settings=get_settings().prompt_workflows,
)
```

Then in the LLM-branch of `classify_intent` (step 3), call `prompt_workflow_executor.resolve("email_intent_chain")` *before* the existing `LLMClassifier.classify()` call. If the executor returns a `ResolvedWorkflow` (i.e. flag-on + skill in CSV), iterate the workflow's steps and use the resolved `PromptDefinition` for each LLM call. If `None` → fall through to the legacy `LLMClassifier.classify()` path unchanged.

**Critical:** the wrapper must short-circuit fast when `settings.enabled is False` — that's the contract that gives us the flag-off byte-stable property. The executor scaffold already does this; just confirm by reading `workflow_executor.py::resolve`.

**Step skipping:** for `extract_entities` and `score_priority` (`required: false` in the descriptor), the wrapper should treat a resolved descriptor that omits these as "skill decides" — i.e. the skill keeps its existing entity / priority logic on flag-off behaviour even when the executor is on. **Do not** make these steps mandatory; that would diverge from the legacy flag-off path.

### LEPES 3 — Tests

Add ~5–10 unit tests + 1 integration. Targets:

| Test | What it asserts | File |
|---|---|---|
| `test_executor_path_resolves_workflow` | Flag-on + skill in CSV → executor returns resolved descriptor; classifier uses workflow prompt | `tests/unit/skills/email_intent_processor/test_workflow_migration.py` (new) |
| `test_flag_off_falls_through_to_legacy` | `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` → executor returns `None`; legacy `LLMClassifier.classify()` runs unchanged | same |
| `test_skill_not_in_csv_falls_through` | Flag-on but `SKILLS_CSV` doesn't contain `email_intent_processor` → fall-through | same |
| `test_required_false_step_can_be_omitted` | Descriptor without `extract_entities` / `score_priority` → skill skips those steps | same |
| `test_descriptor_lookup_failure_falls_through` | Manager's `get_workflow` raises `WorkflowResolutionError` → executor returns `None`; legacy path runs | same |
| `test_strategy_switch_unaffected` | Sprint P `SKLEARN_FIRST` / `SKLEARN_ONLY` strategies — executor never called when sklearn shortcuts | same |
| `test_attachment_signal_early_return_unaffected` | `_keywords_first` + strong attachment signal returns before LLM branch — executor never called | same |
| **integration** `test_email_intent_workflow_real_openai` | Real OpenAI (gated by `OPENAI_API_KEY`), flag-on, `001_invoice_march.eml` fixture → label identical to flag-off baseline | `tests/integration/skills/test_email_intent_workflow.py` (new) |

Add `@test_registry` headers per `tests/CLAUDE.md` rule. Skip the integration test by default unless `OPENAI_API_KEY` is set (mirror the Profile B conditional-skip pattern).

### LEPES 4 — Golden-path gate (BLOKKOLO)

```bash
# Sprint K UC3 4/4 — must stay 4/4 with flag-off (default)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/e2e/test_uc3_emails_golden_path.py -v

# Flag-on parity smoke on the 25-fixture Sprint P corpus
AIFLOW_PROMPT_WORKFLOWS__ENABLED=true \
AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=email_intent_processor \
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/integration/skills/test_uc3_attachment_intent_classify.py -v
```

**Threshold (per `01_PLAN/117_*.md` §3 gate matrix row 1):**
- Flag-off: 4/4 PASS Sprint K UC3.
- Flag-on: 25 / 25 label parity vs flag-off baseline within ±1 fixture (LLM nondeterminism allowance).

If either gate fails → halt session, write a follow-up note in the retro, **do not** push. Two diagnostic checks first:
1. Verify the `_keywords_first` early-return still triggers — Sprint P regression possible.
2. Verify `LLMClassifier.classify()` still runs flag-off — your wrapper may have leaked into the legacy path.

### LEPES 5 — Lint + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/email_intent_processor/  # 0 error
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/skills/email_intent_processor/ -q

git add skills/email_intent_processor/workflows/classify.py \
        tests/unit/skills/email_intent_processor/test_workflow_migration.py \
        tests/integration/skills/test_email_intent_workflow.py
git commit -m "feat(sprint-t): S148 — email_intent_processor consumes email_intent_chain (S141-FU-1)"
git push -u origin feature/t-s148-email-intent-workflow
gh pr create --base main --head feature/t-s148-email-intent-workflow \
  --title "Sprint T S148 — email_intent_processor → PromptWorkflow (S141-FU-1)"
```

Then `/session-close S148` — which queues S149 (`invoice_processor` migration).

---

## 5. STOP FELTETELEK

**HARD:**
1. PR #39 (Sprint T S147 kickoff) not yet merged — wait until `main` has the plan doc + companion + carry-forward reconcile.
2. Sprint K UC3 4/4 fails on flag-off → halt; the executor wrapper has leaked. Revert the diff entirely.
3. 25-fixture flag-on parity > ±1 fixture variance → halt; either the descriptor is wrong, the legacy code-path lost a behaviour, or LLM nondeterminism is masquerading as drift (re-run with seed control once before declaring failure).
4. `WorkflowResolutionError` raised on a successful flag-on path (i.e. no fall-through) → executor scaffold contract violation; halt + escalate to operator (this is a Sprint R bug).
5. Strategy switch / attachment-signal early-return regressions detected on the 25-fixture corpus → halt; Sprint P R1 risk realized (see `01_PLAN/117_*.md` §4 R1).
6. Operator wants the full sklearn replacement instead of the LLM-branch-only migration → halt + revisit the scope (this is explicitly out of S148).

**SOFT:**
- `OPENAI_API_KEY` not set → integration test skips; document, proceed.
- The `extract_entities` / `score_priority` step on the LLM path runs when the descriptor marks them `required: false` — surface the skill-side decision in code review, proceed with current behaviour preserved.
- ST-FU-1 JWT singleton fix grew beyond a side delivery → carry to S149 instead of bundling into S148.

---

## 6. SESSION VEGEN

```
/session-close S148
```

The `/session-close` will:
- Validate lint + unit + e2e collect.
- Re-run Sprint K UC3 4/4 + 25-fixture flag-on parity as the final gate.
- Stage + commit the migration diff.
- Push the branch.
- Generate `session_prompts/NEXT.md` for S149 — `invoice_processor.workflows.process` PromptWorkflow migration.

---

## 7. SKIPPED-ITEMS TRACKER (carry from S147)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 / SS-SKIP-2 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-1 | Sprint T plan §5 + §"Carry-forward" | JWT singleton CI failure (3 tests in `test_rag_collections_router.py`) | **Side delivery in S148 if bandwidth** — pin per-test fresh `AuthProvider` + clear secret cache fixture |
| ST-FU-2 | Sprint T plan §5 | Expert/mentor persona descriptors (`aszf_rag_chain_expert/_mentor`) | Post-Sprint-T |
| SR-FU-4/5/6 | Sprint R retro | Live-stack Playwright + vite-build hook + Langfuse listing | Sprint T side delivery if bandwidth |

S148 closes `S141-FU-1` (kicks `S141-FU-2` to S149).
