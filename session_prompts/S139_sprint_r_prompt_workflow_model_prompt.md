# AIFlow — Session 139 Prompt (Sprint R kickoff — PromptWorkflow model + YAML loader + Langfuse lookup)

> **Datum:** 2026-05-11
> **Branch:** `feature/r-s139-prompt-workflow-model` (cut from `main` @ `c4ded1d`, Sprint Q close).
> **Port:** API 8102 | UI 5173 | Langfuse dev: 3000 | Langfuse PG: 5434
> **Elozo session:** S138 — Sprint Q close + tag `v1.5.0`. UC3 intent → UC1 invoice_processor chained end-to-end, 85.7% UC1 golden-path accuracy, admin UI ExtractedFieldsCard live.
> **Terv:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §3 Sprint R + részletesítés ebben a promptban (kickoff).
> **Session tipus:** Feature work — új contract (PromptWorkflow) + YAML loader + meglévő `PromptManager` kiterjesztés.

---

## 1. MISSION

Introduce a **`PromptWorkflow`** abstraction that composes multiple prompt steps into a single runnable unit, shared across skills. Scope:

1. `PromptWorkflow` + `PromptWorkflowStep` Pydantic models in `src/aiflow/prompts/workflow.py`.
2. YAML loader `PromptWorkflowLoader` (filesystem) mirroring the existing `PromptManager` pattern — resolution order: in-memory cache → Langfuse bundle → local `prompts/workflows/*.yaml` fallback.
3. Extend `PromptManager` with `get_workflow(name, *, label=...)` that returns a resolved `PromptWorkflow` with each step's `PromptDefinition` already fetched (single top-level call to `PromptManager.get()` per step).
4. One example workflow YAML as acceptance evidence: `prompts/workflows/uc3_intent_and_extract.yaml` — describes the Sprint Q chain (classify → optional EXTRACT → extract) **without calling anything yet**. It is a descriptor, not an executor — execution lands S140/S141.
5. Flag: `AIFLOW_PROMPT_WORKFLOWS__ENABLED=false` (default). When off, `get_workflow` raises `FeatureDisabled`.

**NO skill migration in S139** — skills still call `PromptManager.get(name)` directly. Backward-compat shim + skill migration is S141.

---

## 2. KONTEXTUS

### Honnan jöttünk (Sprint Q close, v1.5.0)
Sprint Q delivered the UC3 intent → UC1 extraction bridge end-to-end (85.7% accuracy), but each skill still copy-pastes YAML prompts into its own `skills/<skill>/prompts/` folder. Example: `invoice_processor/prompts/` has 4 prompts (classifier, header_extractor, line_extractor, validator), `email_intent_processor/prompts/` has 8, `aszf_rag_chat/prompts/` has 7. There is no composition, no per-tenant override, no A/B structure beyond the single-prompt level already in `src/aiflow/prompts/ab_testing.py`.

### Jelenlegi állapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2296 unit PASS / 1 skip
~103 integration PASS
429 E2E collected
Branch: main @ c4ded1d (Sprint Q close, tag v1.5.0)
Flags: AIFLOW_UC3_EXTRACTION__ENABLED=false default
       AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false default (Sprint P)
Existing: src/aiflow/prompts/{manager.py, schema.py, sync.py, ab_testing.py}
          skills/*/prompts/*.yaml (22 prompts across 3 skills today)
```

### Hova tartunk (S139 output)
- `src/aiflow/prompts/workflow.py` — new module with 2 Pydantic models (see LEPES 1).
- `src/aiflow/prompts/manager.py` — new method `get_workflow(name, *, label="prod", tenant_id=None)`.
- `src/aiflow/core/config.py` — new `PromptWorkflowSettings` (env prefix `AIFLOW_PROMPT_WORKFLOWS__`, `enabled=false` default).
- `prompts/workflows/uc3_intent_and_extract.yaml` — 1 example workflow, descriptive only.
- 12+ unit tests covering model validation, YAML parsing, Langfuse lookup mock, flag gating, step resolution failures.
- 1 integration test (real Langfuse dev instance) — create a bundle, fetch via `get_workflow`, assert steps resolved.

### Milyen nem cél S139-ben
- NEM migrálunk skill-t (S141 dolga — ott jön a backward-compat shim).
- NEM írunk workflow executor-t (S140/S141 dolga — itt csak a descriptor + lookup készül).
- NEM nyúlunk a UI-hoz (S140 hozza a `/prompts/workflows` oldalt).
- NEM változtatunk a `skills/*/prompts/*.yaml` fájlokon.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                       # feature/r-s139-prompt-workflow-model
git log --oneline -3                            # c4ded1d S138 on top of main
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/prompts/ -q --no-cov 2>&1 | tail -1
docker compose ps                               # postgres + redis healthy
curl -s http://localhost:3000/api/public/health 2>/dev/null | head -3  # Langfuse dev (opcionális integrációs teszt)
ls src/aiflow/prompts/                          # manager.py, schema.py, sync.py, ab_testing.py present
ls prompts/ 2>/dev/null || mkdir -p prompts/workflows   # new top-level dir OK
```

---

## 4. FELADATOK

### LEPES 1 — Pydantic models (`src/aiflow/prompts/workflow.py`)

```python
class PromptWorkflowStep(BaseModel):
    id: str                          # stable id within the workflow (e.g., "classify")
    prompt_name: str                 # PromptManager.get() name
    description: str | None = None
    required: bool = True            # if False, step can be skipped at runtime (e.g., EXTRACT gate)
    depends_on: list[str] = []       # ids of prior steps; cycle detection required
    output_key: str | None = None    # JSONB merge key hint — purely descriptive
    metadata: dict[str, Any] = {}    # free-form (e.g., cost_ceiling_usd, langfuse_variant)

class PromptWorkflow(BaseModel):
    name: str                        # globally unique
    version: str                     # semver string
    description: str | None = None
    steps: list[PromptWorkflowStep]  # ≥ 1, dedup-by-id validator
    tags: list[str] = []
    default_label: str = "prod"      # Langfuse label for resolving nested prompts

    # Validators:
    # - steps non-empty
    # - step ids unique
    # - depends_on references resolve to existing step ids
    # - DAG (no cycles) — kahn topological sort at validation time
```

Place this next to `PromptConfig` + `PromptDefinition` in `src/aiflow/prompts/schema.py` if they coupling naturally; else new file. Author's judgement, but keep the import surface narrow.

### LEPES 2 — Loader (`src/aiflow/prompts/workflow_loader.py`)

Class `PromptWorkflowLoader`:
- Constructor `(workflows_dir: Path, *, manager: PromptManager)`.
- Method `load_from_yaml(path: Path) -> PromptWorkflow`.
- Method `list_local() -> list[str]` (filenames without `.yaml`).
- Does NOT resolve prompts — that's the manager's job. Just returns the Pydantic object.

### LEPES 3 — `PromptManager.get_workflow`

New method on the existing `PromptManager`:
```python
async def get_workflow(
    self,
    name: str,
    *,
    label: str = "prod",
    tenant_id: str | None = None,
) -> tuple[PromptWorkflow, dict[str, PromptDefinition]]:
```

Returns the workflow + a dict of resolved `step.id -> PromptDefinition`. Uses the existing 3-layer lookup (cache → Langfuse → local YAML) **per step** but short-circuits if the workflow descriptor itself is in-cache.

Langfuse contract: the workflow lives as a JSON prompt in Langfuse under `workflow:<name>` key (leverages existing v4 SDK `get_prompt` infrastructure — no new Langfuse client code).

Feature flag check: if `settings.prompt_workflows.enabled is False` → raise `FeatureDisabled("prompt_workflows")`.

### LEPES 4 — Settings

`src/aiflow/core/config.py`:
```python
class PromptWorkflowSettings(BaseModel):
    enabled: bool = False
    workflows_dir: str = "prompts/workflows"
    cache_ttl_seconds: int = 300
```

Mount on `AIFlowSettings` as `prompt_workflows: PromptWorkflowSettings`.

### LEPES 5 — Example workflow (acceptance evidence)

`prompts/workflows/uc3_intent_and_extract.yaml`:
```yaml
name: uc3_intent_and_extract
version: "0.1.0"
description: |
  Sprint Q chain expressed as a descriptor — S139 lands the model,
  S141 migrates email_intent_processor + invoice_processor to consume
  this workflow via the PromptManager.
default_label: prod
tags: [uc3, sprint-q-bridge]
steps:
  - id: classify
    prompt_name: email_intent_processor/intent_classifier
    description: Sprint K base classifier prompt
    output_key: classification
  - id: extract_header
    prompt_name: invoice_processor/invoice_header_extractor
    required: false
    depends_on: [classify]
    output_key: extracted_fields.header
    metadata: { gate: "intent_class == EXTRACT", cost_ceiling_usd: 0.02 }
  - id: extract_lines
    prompt_name: invoice_processor/invoice_line_extractor
    required: false
    depends_on: [extract_header]
    output_key: extracted_fields.line_items
    metadata: { gate: "extract_header.succeeded", cost_ceiling_usd: 0.03 }
```

### LEPES 6 — Unit tests (≥ 12)

`tests/unit/prompts/test_workflow_model.py`:
1. Model accepts minimal valid payload (1 step).
2. Empty `steps` rejected.
3. Duplicate step id rejected.
4. `depends_on` referencing missing id rejected.
5. Cycle detected (a→b, b→a).
6. `default_label` default = `"prod"`.

`tests/unit/prompts/test_workflow_loader.py`:
7. Load example YAML round-trips without loss.
8. Malformed YAML → `WorkflowYamlError` with path hint.
9. Missing `name` field → validation error.

`tests/unit/prompts/test_manager_get_workflow.py`:
10. Flag off → `FeatureDisabled`.
11. Flag on + local YAML + Langfuse stubbed → returns workflow + resolved step prompts.
12. Langfuse bundle hit → local YAML NOT read (cache/Langfuse wins).
13. Missing nested prompt → `PromptResolutionError` names the failing step id.

### LEPES 7 — Integration test (1, Langfuse dev)

`tests/integration/prompts/test_workflow_langfuse_dev.py`:
- Skip if `docker compose ps` shows langfuse not healthy.
- Bootstrap: use `scripts/bootstrap_langfuse.py` pattern to create keypair + publish a workflow bundle.
- Assert: `PromptManager.get_workflow("uc3_intent_and_extract")` returns object with 3 steps, all `PromptDefinition` resolved.

### LEPES 8 — Regression + lint + commit + push

- `/regression` → 2296 + ≥ 12 unit green.
- `/lint-check` clean.
- Commit message:
  ```
  feat(sprint-r): S139 — PromptWorkflow model + loader + Langfuse lookup (flag off)

  - src/aiflow/prompts/workflow.py: PromptWorkflow + PromptWorkflowStep
  - src/aiflow/prompts/workflow_loader.py: filesystem YAML loader
  - src/aiflow/prompts/manager.py: get_workflow() method (3-layer cache → Langfuse → local)
  - src/aiflow/core/config.py: PromptWorkflowSettings (enabled=false default)
  - prompts/workflows/uc3_intent_and_extract.yaml: 3-step descriptor example
  - tests/unit/prompts/: 12 unit tests (model + loader + manager)
  - tests/integration/prompts/test_workflow_langfuse_dev.py: 1 live-stack test

  Session: S139 | Sprint: R | Phase: kickoff
  Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
  ```
- Push → `gh pr create --title "Sprint R S139: PromptWorkflow model + YAML loader + Langfuse lookup (flag off)"` against `main`.

### LEPES 9 — NEXT.md for S140

Overwrite `session_prompts/NEXT.md` with the S140 prompt (Admin UI `/prompts/workflows` listing + detail + test-run gomb + 1 Playwright E2E on live stack).

---

## 5. STOP FELTETELEK

**HARD:**
1. Langfuse v4 SDK does not expose a bundle-lookup path compatible with `get_prompt(name=...)` for JSON-typed prompts — halt, Langfuse v3→v4 migration becomes a prerequisite (Sprint O/M carry). Document scope and STOP decision-required.
2. Alembic migration becomes necessary (e.g., new `prompt_workflows` table) — halt. Sprint R scope is file + Langfuse only; a new table needs its own session.
3. Skill-level breakage observed during test run (e.g., `PromptManager.get` contract shifted) — halt + revert the manager edit.

**SOFT:**
- Langfuse dev instance not available during integration test → `pytest.skip` with clear reason; do NOT gate S139 on this.
- The 3 nested prompts referenced by the example workflow don't exist under those exact names yet — use the nearest existing prompt file and record the rename as an S141 prerequisite.

---

## 6. SESSION VEGEN

```
/session-close S139
```

Utána: auto-sprint loop indul S140-re (UI /prompts/workflows + Playwright E2E live stack).

---

## 7. POST-SESSION (S140 előnézet)

S140 scope: Admin UI `/prompts/workflows` oldal — listing (workflow name, version, step count, tags), detail panel (steps + resolved prompt previews + metadata), "Test run" gomb ami `/api/v1/prompts/workflows/{name}/dry-run` endpoint-ot hív (új, additív; csak a `PromptManager.get_workflow` output-ot adja vissza JSON-ben, NEM hajt végre LLM-hívást). 1 Playwright E2E live dev stack-en (seed a `uc3_intent_and_extract` workflow Langfuse bundle-be → UI megjeleníti → Test run zöld JSON).
