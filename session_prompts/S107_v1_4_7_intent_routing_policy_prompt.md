# AIFlow v1.4.7 Sprint K — Session 107 Prompt (UC3 — IntentRoutingPolicy + Langfuse prompt fetch)

> **Datum:** 2026-04-23 (tervezett folytatas)
> **Branch:** `feature/v1.4.7-email-intent`
> **HEAD:** `f615800` — `feat(sprint-k): S106 — ClassificationResult unify + scan_and_classify orchestrator`
> **Alembic head:** `042` (nincs uj migration szukseges S107-hez)
> **Port:** API 8102 | Frontend Vite 5175
> **Elozo session:** S106 — ClassificationResult unify + `scan_and_classify` thin orchestrator + `POST /api/v1/emails/scan/{config_id}` endpoint + 1 integration test (real PG) GREEN.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K — S107 row (IntentRoutingPolicy, volt S105 a rescope elott).
> **Session tipus:** IMPLEMENTATION — per-tenant routing policy + Langfuse prompt fetch az email_intent skill-hez.

---

## KONTEXTUS

### Honnan jottunk (S106 output)

- `ClassificationResult` unify: `services/classifier/service.py` a canonical forras. `models/protocols/classification.py` + `providers/interfaces.py` re-export-ol.
- `scan_and_classify(adapter, sink, classifier, repo, *, tenant_id, max_items, schema_labels)` thin orchestrator — `src/aiflow/services/email_connector/orchestrator.py`.
- `POST /api/v1/emails/scan/{config_id}` — dev-credentials (plaintext JSON) imap konfigokkal mukodik, `credentials_encrypted` decrypt deferred S107-re.
- 1 integration test (`tests/integration/services/email_connector/test_scan_and_classify.py`) GREEN real Docker PG-n: 2 email (HU+EN) → 2 `intake_packages` + 2 `workflow_runs` row + 2 structlog event.
- CLAUDE.md + `110_USE_CASE_FIRST_REPLAN` §4 frissitve: 8 skill, 56 integration tests, S104→S106 / S105→S107 rescope note.
- Tooling: post-Write/Edit tsc hook az `aiflow-admin/` TS fajlokra (`.claude/hooks/tsc_check.py`, incremental, ~4s warm), shared allowlist-bovites.

### Hova tartunk (S107 scope)

Per-tenant `IntentRoutingPolicy`: a `ClassificationResult.label` → downstream action mapping (pl. `invoice_question → EXTRACT`, `support_request → NOTIFY_DEPT`, `spam → ARCHIVE`, `unknown → MANUAL_REVIEW`). PolicyEngine integraciot hasznal (mar letezik a `core/policy/` alatt). Langfuse prompt fetch-et ekkor kotjuk be az `email_intent_processor` skill-hez.

### Jelenlegi allapot

```
27 service | 181 endpoint (27 router, +1 S106) | 50 DB tabla | 42 Alembic migration (head: 042)
1995 unit PASS | 413 E2E collected | 56 integration (incl. 1 UC3 scan_and_classify)
8 skills | Branch: feature/v1.4.7-email-intent @ f615800
Sprint J MERGED | UC2 DONE | UC3 S106 GREEN | UC3 S107 START
```

---

## ELOFELTELEK

```bash
git branch --show-current                              # feature/v1.4.7-email-intent
git log --oneline -1                                   # f615800
git describe --tags HEAD                               # v1.4.5-sprint-j-uc2-2-gf615800
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet   # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# Expected: 1995 passed, 1 skipped, 1 xpassed
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current   # 042
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/email_connector/ -q --no-cov
# Expected: 1 passed (S106 regression check)
```

**Docker dependencies:** PG (5433), Redis (6379). Langfuse: local or cloud — `AIFLOW_LANGFUSE__ENABLED=true` + project keys env-ben.

---

## FELADATOK

### LEPES 1 — Explore PolicyEngine + Langfuse prompt manager (readonly, ~20 min)

Parallel Read agent-et indits (Explore + Plan egyutt) az alabbi cel-file-okra:

```bash
# PolicyEngine surface
grep -rn "class PolicyEngine\|def pick_\|tenant_id" src/aiflow/core/policy/ | head -30

# IntentRoutingPolicy — letezik? vagy uj?
grep -rn "IntentRoutingPolicy\|RoutingPolicy\|intent.*route" src/ 2>&1 | grep -v __pycache__ | head -10

# Langfuse prompt fetch pattern
grep -rn "langfuse.*prompt\|prompt_manager\|fetch_prompt" src/aiflow/prompts/ src/aiflow/services/email_connector/ | head -15

# Email intent skill prompts
ls skills/email_intent_processor/prompts/
```

**Cel:** meghatarozni, hogy `IntentRoutingPolicy` legyen (a) uj `core/policy/` contract, (b) `services/email_connector/` helper, vagy (c) `skills/email_intent_processor/` skill-local policy. Javaslat: (a) core/policy, hogy `PolicyEngine` ABI-t kovesse es tobb skill is hasznalhassa.

### LEPES 2 — IntentRoutingPolicy contract (~30 min)

**File:** `src/aiflow/core/policy/intent_routing.py` (UJ, ~60 sor).

```python
"""Intent → downstream action routing policy, per-tenant configurable."""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class IntentAction(str, Enum):
    EXTRACT = "extract"           # UC1-style document field extraction
    NOTIFY_DEPT = "notify_dept"   # Route to department queue
    ARCHIVE = "archive"            # No further processing
    MANUAL_REVIEW = "manual_review"
    REPLY_AUTO = "reply_auto"      # Auto-reply with template

class IntentRoutingRule(BaseModel):
    intent_label: str               # matches ClassificationResult.label
    action: IntentAction
    target: str = ""                # e.g., department_id, queue_id, template_id
    min_confidence: float = 0.6

class IntentRoutingPolicy(BaseModel):
    tenant_id: str
    default_action: IntentAction = IntentAction.MANUAL_REVIEW
    rules: list[IntentRoutingRule] = Field(default_factory=list)

    def decide(self, label: str, confidence: float) -> tuple[IntentAction, str]:
        """Return (action, target) for a (label, confidence) pair."""
        for rule in self.rules:
            if rule.intent_label == label and confidence >= rule.min_confidence:
                return rule.action, rule.target
        return self.default_action, ""
```

Per-tenant config: PolicyEngine beolvassa `AIFLOW_POLICY_DIR/intent_routing/{tenant_id}.yaml`-t (konvencio).

### LEPES 3 — Integracio `scan_and_classify`-ba (~30 min)

Bovitsd az orchestrator-t: `scan_and_classify(..., routing_policy: IntentRoutingPolicy | None = None)`. Ha van policy:
- Hivd `policy.decide(result.label, result.confidence)` -> `(action, target)`
- Mentsd el `output_data["routing_action"]` + `output_data["routing_target"]` a workflow_runs row-ban
- Emit additional structlog event: `email_connector.scan_and_classify.routed` `action=... target=...`

### LEPES 4 — Langfuse prompt fetch wiring (~30 min)

`services/email_connector/orchestrator.py`-ban opcionalisan hivd `PromptManager.fetch("email_intent_processor/classifier", version="head", langfuse_trace=True)`-t. Ha sikeres, passzold be a classifier.classify-nak mint `schema_labels` forrast (a prompt YAML-bol).

Ha `AIFLOW_LANGFUSE__ENABLED=false` → skip silent, hasznalj `schema_labels` param-ot ahogy eddig.

**Prompt YAML forma:** `skills/email_intent_processor/prompts/intents_schema.yaml` (ha letezik, kulonben uj, de S107 scope-ban ne hozzuk letre uj Langfuse prompt-ot — ez a cel, csak fetch legyen).

### LEPES 5 — Integration test bovites (~30 min)

**File:** `tests/integration/services/email_connector/test_intent_routing.py` (UJ).

- 4 fixture email → 4 intent label (invoice, support, spam, unknown).
- `IntentRoutingPolicy` fixturet 4 rule-lal: invoice→EXTRACT, support→NOTIFY_DEPT, spam→ARCHIVE, default→MANUAL_REVIEW.
- Futtasd `scan_and_classify(routing_policy=...)` → assert:
  - 4 workflow_runs row, mindegyik `output_data.routing_action` helyes
  - 4 `email_connector.scan_and_classify.routed` structlog event

Determinisztikussag: `AIFLOW_LLM_MODE=deterministic` env var; sklearn_only strategy maradjon a classifier config.

### LEPES 6 — Docs + `scan_and_classify_endpoint` bovites (~15 min)

- `CLAUDE.md` Key Numbers: 56→57 integration tests
- `110_USE_CASE_FIRST_REPLAN.md` §4 S107 row: **[DELIVERED]** marker
- `api/v1/emails.py` endpoint: opcionalis `routing_policy_id` body field → betolti `POLICY_DIR`-bol a yaml-t es tovabbitja

### LEPES 7 — Regresszio + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/email_connector/ -q --no-cov
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/e2e --collect-only -q
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current     # meg mindig 042
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py

/session-close S107
```

---

## STOP FELTETELEK

**HARD:**
1. `PolicyEngine` ABI nem alkalmas per-tenant YAML fetch-re (pl. async signature mismatch) → architect agent.
2. Langfuse cloud/local nem elerheto es nincs fallback path → defer Langfuse wiring S108-ra, S107 csak a routing policy contract-et szallitja.
3. `IntentRoutingPolicy` contract breaking change-et igenyel a `ClassificationResult`-ban → STOP, architect revisit.

**SOFT:**
1. Ha `AIFLOW_LLM_MODE=deterministic` nincs implementalva → sklearn_only strategy marad, LLM vonulat S108-ra deferred.
2. Ha 4-way routing test flaky > 3 futas alatt → jelezd, de ne blokkold a session-t — quarantine-oljuk.

---

## SESSION VEGEN

```
/session-close S107
```

Utana `/clear` es S108 (UI `Emails.tsx`: scan button + intent badge + routing chip + Langfuse trace link, Playwright E2E) — `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4.
