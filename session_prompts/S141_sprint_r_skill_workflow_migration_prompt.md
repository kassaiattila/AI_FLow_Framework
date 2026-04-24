# AIFlow — Session 141 Prompt (Sprint R S141 — skill migration to PromptWorkflow + backward-compat shim)

> **Datum:** 2026-05-13
> **Branch:** `feature/r-s141-skill-workflow-migration` (cut from `main` after S140 squash-merge).
> **HEAD (parent):** S140 squash-merge on `main` (PR #31).
> **Port:** API 8102 | UI 5173 | Langfuse dev: 3000
> **Elozo session:** S140 — admin UI `/prompts/workflows` + dry-run endpoint + 10 router unit tests. Total Sprint R footprint so far: 34 unit tests / 1 new router / 1 new admin page.
> **Terv:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 + S140 PR description ("Follow-ups" S141 line).
> **Session tipus:** Refactor — skill migration with backward-compat shim. Highest-risk session of Sprint R; conservative defaults.

---

## 1. MISSION

Make 3 skills consume `PromptWorkflow` via a thin shim instead of inlining `PromptManager.get(name)` per step. Goal: prove the contract without breaking any UC1/UC3/UC2 golden path.

**Strategy = additive + flag-gated.** Each skill keeps its existing per-prompt path 100% intact. A new `PromptWorkflowExecutor` helper resolves a workflow to ordered `PromptDefinition` instances; if the workflow lookup fails or the flag is off, the skill silently falls back to the legacy per-prompt code. Migration is **opt-in per skill via env**: `AIFLOW_PROMPT_WORKFLOWS__SKILLS=email_intent_processor,invoice_processor` (CSV).

**3 skills in scope:**
1. `email_intent_processor` — workflow `email_intent_chain` covering `intent_classifier` (+ optionally `entity_extractor` + `priority_scorer`).
2. `invoice_processor` — workflow `invoice_extraction_chain` covering `invoice_classifier`, `invoice_header_extractor`, `invoice_line_extractor`, `invoice_validator`.
3. `aszf_rag_chat` — workflow `aszf_rag_chain` covering 1 of the 3 system_prompt_* variants + `query_rewriter` + `answer_generator`.

**NO schema change. NO Alembic. NO new endpoint. NO LLM behaviour change.**

---

## 2. KONTEXTUS

### Honnan jöttünk (S140 close)
S139 shipped `PromptWorkflow` model + lookup. S140 shipped admin UI + dry-run. Now skills can finally **consume** the workflow contract — which is the whole point of Sprint R.

Today every skill has its own:
```python
self.prompt_manager.get("email-intent/classifier")
# ... same boilerplate, same caching, same Langfuse fallback ...
```

After S141 the migrated skills do:
```python
workflow, prompts = self.prompt_manager.get_workflow("email_intent_chain")
classifier_prompt = prompts["classify"]
# ... per-step metadata available via workflow.get_step("classify").metadata ...
```

### Jelenlegi állapot (S140 close)
```
27 service | 193 endpoint (30 routers) | 50 DB table | 45 Alembic (head: 045)
2330 unit PASS / 1 skip
~103 integration PASS
429 E2E collected
Branch: main @ <S140 squash sha>
Flags: AIFLOW_PROMPT_WORKFLOWS__ENABLED=false default
       AIFLOW_PROMPT_WORKFLOWS__SKILLS="" default (no skills migrated)
Workflow descriptors: prompts/workflows/uc3_intent_and_extract.yaml (S139 example)
```

### Hova tartunk (S141 output)
- 1 new helper `src/aiflow/prompts/workflow_executor.py` — `PromptWorkflowExecutor` resolves + sequences steps; **caller still owns LLM invocation**. This session does NOT introduce an executor that calls LLMs.
- 1 new `PromptWorkflowSettings.skills` CSV field.
- 3 new YAML descriptors under `prompts/workflows/`:
  - `email_intent_chain.yaml`
  - `invoice_extraction_chain.yaml`
  - `aszf_rag_chain.yaml`
- 3 lightweight migrations (one per skill) — each adds an `_uses_workflow()` gate + the workflow lookup; if it returns prompts, those win, else fallback to per-prompt path. **No code path is removed.**
- 12+ unit tests (4 per skill: shim off → legacy path; shim on → workflow path; workflow lookup fail → fallback to legacy; metadata propagated to executor).
- 1 integration test per skill (real PG + per-skill LLM if cheap; mock LLM otherwise) confirming a sample call still produces the legacy output.

### Milyen NEM cél
- NEM hajt végre LLM-hívást a `PromptWorkflowExecutor` (csak resolution + ordering).
- NEM töröl semmilyen meglévő prompt YAML-t.
- NEM mozgatja a `skills/<x>/prompts/*.yaml` fájlokat (a workflow csak hivatkozza őket név szerint).
- NEM változtatja meg a Sprint K/Q golden-path E2E eredményeit.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                       # feature/r-s141-skill-workflow-migration
git log --oneline -3                            # S140 squash on top
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/prompts/ tests/unit/api/test_prompt_workflows_router.py -q --no-cov 2>&1 | tail -1   # 34 pass
docker compose ps                               # postgres + redis healthy
ls skills/email_intent_processor skills/invoice_processor skills/aszf_rag_chat
```

---

## 4. FELADATOK

### LEPES 1 — Settings extension

`src/aiflow/core/config.py` `PromptWorkflowSettings`:
```python
skills: list[str] = []   # comma-separated env override → list
```
Custom validator parses CSV from `AIFLOW_PROMPT_WORKFLOWS__SKILLS`. 3 unit tests.

### LEPES 2 — Executor helper

`src/aiflow/prompts/workflow_executor.py`:
```python
class PromptWorkflowExecutor:
    def __init__(self, manager: PromptManager) -> None: ...

    def is_skill_migrated(self, skill_name: str) -> bool:
        """Read PromptWorkflowSettings.skills + AIFLOW_PROMPT_WORKFLOWS__ENABLED."""

    def resolve_for_skill(
        self, skill_name: str, workflow_name: str, *, label: str | None = None
    ) -> tuple[PromptWorkflow, dict[str, PromptDefinition]] | None:
        """Returns the workflow + resolved prompts, or None if shim is off / lookup fails."""
```
6 unit tests (gate matrix + lookup pass/fail + label override + caching).

### LEPES 3 — Workflow descriptors

3 YAML files under `prompts/workflows/`:
- `email_intent_chain.yaml` — 3 steps (`classify`, `extract_entities`, `score_priority`).
- `invoice_extraction_chain.yaml` — 4 steps (`classify`, `extract_header`, `extract_lines`, `validate`); the latter 3 with `depends_on` chain.
- `aszf_rag_chain.yaml` — 3 steps (`rewrite_query`, `system_baseline`, `answer`).

Each descriptor uses real prompt names (`email-intent/classifier`, `invoice/header_extractor`, `aszf-rag/answer_generator`, etc.).

### LEPES 4 — Skill migrations (one per skill)

For each of the 3 skills:
1. Find the workflow's entry point (look for `prompt_manager.get(...)` calls).
2. Add `if self._executor.is_skill_migrated("<skill>"):` gate at the top.
3. On True: call `resolve_for_skill(...)` and use the returned prompts.
4. On False or lookup fail: fallback to legacy per-prompt path.
5. **Add a structlog event** so we can verify in production which path executed.

Touch the **minimum** number of lines per skill. Pure additive.

### LEPES 5 — Tests (≥ 12 unit + ≥ 3 integration)

Per skill:
- Unit: shim-off legacy path / shim-on workflow path / workflow-fail fallback / metadata accessible.
- Integration: end-to-end pipeline call returns the same Pydantic output shape as before. Use existing fixtures (`tests/integration/skills/test_*.py` patterns).

### LEPES 6 — Regression + lint + commit + push

- `/regression` → 2330 + 12 unit + 3 integration green.
- `/lint-check` clean.
- Commit: `refactor(sprint-r): S141 — skill consumers of PromptWorkflow with backward-compat shim`.
- Push → `gh pr create`.

### LEPES 7 — NEXT.md for S142

Overwrite `session_prompts/NEXT.md` with the S142 prompt (Sprint R close — retro + PR description + tag `v1.5.1` + CLAUDE.md numbers).

---

## 5. STOP FELTETELEK

**HARD:**
1. Sprint K UC3 golden-path E2E regresses (4/4 → less) — halt + revert. The shim must be a true no-op when off.
2. Sprint Q UC1 golden-path accuracy drops below 80% — halt; the workflow descriptor's prompt names probably don't match the actual YAMLs.
3. Sprint J UC2 RAG MRR@5 drops below 0.55 on either profile — halt.
4. A skill's Pydantic output schema changes — halt; this PR must be schema-stable.
5. `aszf_rag_chat` has 3 system_prompt variants (baseline / expert / mentor) — pick **only baseline** for the workflow descriptor; the other two are operator-controlled, separate workflows. If the existing skill picks based on user role, keep that selection logic in the skill, not in the workflow.

**SOFT:**
- If a skill's prompt-call pattern is too entangled to migrate cleanly in one session, **migrate only 1-2 skills** and document the third as S141-FU-1 carryover. Better to ship 2 clean migrations than 3 messy ones.
- If `PromptWorkflowExecutor` ends up needing to know about LLM clients, halt and split — that's the executor session, not the shim session.

---

## 6. SESSION VEGEN

```
/session-close S141
```

Utána: auto-sprint loop indul S142-re (Sprint R close + `v1.5.1` tag).
