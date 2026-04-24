# AIFlow — Session 140 Prompt (Sprint R S140 — Admin UI /prompts/workflows + dry-run E2E)

> **Datum:** 2026-05-12
> **Branch:** `feature/r-s140-workflow-admin-ui` (cut from `main` after S139 squash-merge).
> **HEAD (parent):** S139 squash-merge on `main` (PR #30).
> **Port:** API 8102 | UI 5173 | Langfuse dev: 3000
> **Elozo session:** S139 — `PromptWorkflow` Pydantic model + YAML loader + `PromptManager.get_workflow()` 3-layer lookup + `PromptWorkflowSettings` flag (default off) + 24 unit tests.
> **Terv:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 + S139 PR description ("Follow-ups" S140 line).
> **Session tipus:** Feature work — admin UI + additive read-only API endpoint + 1 Playwright E2E live stack.

---

## 1. MISSION

Build the admin-side surface for `PromptWorkflow`. Three deliverables:

1. **GET `/api/v1/prompts/workflows` + `/{name}` + `/{name}/dry-run`** — additive, read-only endpoints. Dry-run returns the resolved workflow + per-step `PromptDefinition` JSON (no LLM call, no side effect). Flag-gated by the same `AIFLOW_PROMPT_WORKFLOWS__ENABLED` from S139 → 503 `FeatureDisabled` when off.
2. **Admin UI `/prompts/workflows` page** (React 19 + Tailwind v4) — listing (name / version / step count / tags) → detail panel (DAG visualization minimal: ordered list with `depends_on` indentation, resolved prompt previews, metadata chips) → "Test run" button calling the dry-run endpoint and showing the JSON result.
3. **1 Playwright E2E on the live dev stack** — seed the example workflow into Langfuse OR rely on the local YAML (whichever is simpler), navigate UI → list → detail → click Test Run → assert JSON payload visible. NO route mock.

Flag stays off in production defaults.

---

## 2. KONTEXTUS

### Honnan jöttünk (S139 close)
S139 shipped the descriptor + 3-layer lookup. There's no consumer yet. The example workflow `uc3_intent_and_extract` is registered if `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` — but nothing surfaces it.

### Jelenlegi állapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2320 unit PASS / 1 skip
~103 integration PASS
429 E2E collected
Branch: main @ <S139 squash sha>
Flags: AIFLOW_PROMPT_WORKFLOWS__ENABLED=false default
       AIFLOW_UC3_EXTRACTION__ENABLED=false default (Sprint Q)
Existing prompts UI: aiflow-admin/src/pages-new/Prompts*.tsx (per-prompt view)
```

### Hova tartunk (S140 output)
- 1 new router `src/aiflow/api/v1/prompt_workflows.py` (3 routes: list / detail / dry-run).
- 1 new admin UI page `aiflow-admin/src/pages-new/PromptWorkflows.tsx` + sidebar nav entry under "Prompts".
- EN/HU locale bundle `aiflow.prompts.workflows.*`.
- 1 Playwright E2E `tests/e2e/v1_5_1_r_s140_workflow_admin/test_workflow_admin_dry_run.py` — live dev stack, signed JWT, real list → detail → dry-run.
- 8+ unit tests for the router (flag off → 503, list shape, detail not-found, dry-run resolution failure → 422).
- OpenAPI snapshot refresh (`scripts/export_openapi.py`).

### Milyen NEM cél
- NEM hajt végre LLM-hívást (executor S141).
- NEM ír DB-be (read-only).
- NEM migrál skill-t.
- NEM nyúl a Sprint Q UC3 / UC1 path-hoz.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                       # feature/r-s140-workflow-admin-ui
git log --oneline -3                            # S139 squash on top
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/prompts/ -q --no-cov 2>&1 | tail -1   # 24+ pass
docker compose ps                               # postgres + redis healthy
ls aiflow-admin/src/pages-new/Prompts*.tsx 2>&1 # existing prompt pages for layout reference
```

---

## 4. FELADATOK

### LEPES 1 — API router

`src/aiflow/api/v1/prompt_workflows.py`:
- `GET /api/v1/prompts/workflows` → list of `{name, version, step_count, tags}` from `PromptWorkflowLoader.list_local()` + Langfuse-known names if reachable.
- `GET /api/v1/prompts/workflows/{name}` → full `PromptWorkflow` JSON (no nested prompt resolution yet).
- `GET /api/v1/prompts/workflows/{name}/dry-run?label=prod` → `{workflow, steps: {step_id: PromptDefinition}}`. Use `PromptManager.get_workflow(name, label=...)`. Map `KeyError` → 404, `WorkflowResolutionError` → 422 (with step_id + cause), `FeatureDisabled` → 503.
- Mount under `aiflow_router` in `api/v1/__init__.py`.

### LEPES 2 — Router unit tests (≥ 8)

`tests/unit/api/v1/test_prompt_workflows_router.py`:
1. flag off → 503 with `error_code=FEATURE_DISABLED`
2. list shape correct (smoke)
3. detail unknown → 404
4. detail known → full payload
5. dry-run unknown → 404
6. dry-run nested-prompt missing → 422 with step_id
7. dry-run label override propagates
8. response models stable (Pydantic snapshot)

### LEPES 3 — Admin UI page

`aiflow-admin/src/pages-new/PromptWorkflows.tsx`:
- Table layout matching `Prompts.tsx` style. Columns: name, version, step count, tags.
- Detail drawer (Tailwind v4): ordered step list with `depends_on` chips, expandable prompt preview (system + user), metadata chips (cost ceiling, gate condition).
- "Test Run" button → `POST` (or GET) the dry-run endpoint, show resulting JSON in a `<pre>` block with copy button.
- `data-testid` hooks: `prompt-workflows-table`, `prompt-workflow-row-{name}`, `prompt-workflow-detail`, `prompt-workflow-dry-run-button`, `prompt-workflow-dry-run-output`.
- EN + HU locale bundle `aiflow.prompts.workflows.*` (title, columns, dryRun, noWorkflows).
- Sidebar nav entry under existing "Prompts" group.

### LEPES 4 — TypeScript types

`aiflow-admin/src/types/promptWorkflow.ts` mirroring the FastAPI response models. No `any` — use the OpenAPI snapshot as source of truth.

### LEPES 5 — Playwright E2E (live dev stack)

`tests/e2e/v1_5_1_r_s140_workflow_admin/test_workflow_admin_dry_run.py`:
- Boot dev stack (`make api` + UI dev server).
- Set `AIFLOW_PROMPT_WORKFLOWS__ENABLED=true` for the run.
- Sign JWT, authenticate, navigate to `/prompts/workflows`.
- Assert listing shows `uc3_intent_and_extract` row with version `0.1.0`, step count 3.
- Click row → detail visible with 3 steps, `depends_on` indentation correct.
- Click "Test Run" → JSON output contains all 3 step ids.
- NO route mocking. Uses the same `authenticated_page` fixture pattern as Sprint Q S136.

### LEPES 6 — Regression + lint + commit + push

- `/regression` → 2320 + 8 unit + 1 E2E green.
- `/lint-check` (ruff + tsc) clean.
- `scripts/export_openapi.py` refresh.
- Commit: `feat(sprint-r): S140 — admin UI /prompts/workflows + dry-run endpoint + live-stack E2E`.
- Push → `gh pr create --title "Sprint R S140: admin UI /prompts/workflows + dry-run E2E"`.

### LEPES 7 — NEXT.md for S141

Overwrite `session_prompts/NEXT.md` with the S141 prompt (skill migration: `email_intent_processor` + `invoice_processor` + `aszf_rag_chat` consume `PromptWorkflow` via backward-compat shim).

---

## 5. STOP FELTETELEK

**HARD:**
1. Sprint Q UC3 golden-path E2E regresses on the new endpoint mounting — halt.
2. Live dev stack Langfuse misbehaves on workflow seeding → fall back to local YAML for the E2E (acceptable), but document.
3. Admin UI auth integration breaks (the `authenticated_page` fixture stops returning 200) — halt; this affects every session, not just S140.

**SOFT:**
- React 19 / Tailwind v4 layout drift vs existing `Prompts.tsx` — accept and align in a follow-up.
- Dry-run JSON gets large on >5-step workflows — render via virtualized list if needed; otherwise plain `<pre>` is fine.

---

## 6. SESSION VEGEN

```
/session-close S140
```

Utána: auto-sprint loop indul S141-re (skill migration + backward-compat shim).
