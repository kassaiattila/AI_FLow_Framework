# AIFlow v1.4.7 Sprint K — Session 106 Prompt (UC3 RESCOPED: ClassificationResult unify + EmailSource scan-classify glue)

> **Datum:** 2026-04-26 (tervezett folytatas)
> **Branch:** `feature/v1.4.7-email-intent` (mar cut-olva mainbol `v1.4.5-sprint-j-uc2` tag-rol — S105-pre session zart le).
> **HEAD:** `f504aad` — `v1.4.5 Sprint J — UC2 RAG (retrieval baseline + multi-profile embedders + pgvector flex-dim) (#14)`
> **Alembic head:** `042` (Sprint J)
> **Port:** API 8102 | Frontend Vite 5175
> **Elozo session:** S105-pre — Sprint J PR #14 mypy ABC fix + squash merge, tag `v1.4.5-sprint-j-uc2` pushed, branch cut, **architect rescope discovery** S105-re. Az eredeti S105 scope (NEXT.md v1) stale-nek bizonyult — jelentos scope-csokkentes szukseges.
> **Terv:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K (UPDATED — rescope kesziteni a plan-validator-rel is).
> **Session tipus:** CONTRACT UNIFY + THIN GLUE — **NEM** uj alembic, **NEM** uj ClassificationStep, **NEM** uj contract file.
> **Elozo (stale) archive:** `session_prompts/S105_v1_4_7_sprint_k_kickoff_prompt.md` — superseded by architect verdict, ne kovesd.

---

## KONTEXTUS

### Honnan jottunk (S105-pre session output)

- **Sprint J MERGED** 2026-04-22: PR #14 squash-olva mainbe, `f504aad` merge commit, annotated tag `v1.4.5-sprint-j-uc2` push-olva.
- **Mypy blocker resolved:** `EmbedderProvider.PROVIDER_NAME: ClassVar[str]` declaralva az ABC-n (commit `71982ff` a PR-ben).
- **Branch cut:** `feature/v1.4.7-email-intent` tiszta, HEAD @ Sprint J merge commit.
- **Architect discovery** (S105-pre FAZIS 4): az eredeti S105 NEXT.md scope **3 kritikus stale feltevessel** rendelkezett — lasd lent.

### Architect verdikt — CONDITIONAL GO, 5 blocker-feltetel

**Kritikus findings-ok (verified):**

1. **Skill neve `email_intent_processor`, NEM `email_intent`.** `skills/email_intent_processor/` letezik ~20 helyrol importalva.
2. **`ClassificationResult` HAROM versenyzo definicio:**
   - `src/aiflow/models/protocols/classification.py:17` — 3-field protocol placeholder
   - `src/aiflow/services/classifier/service.py:48` — 11-field operational (**runtime actually consumed**)
   - `skills/email_intent_processor/models/__init__.py:52` — `IntentResult` skill-local variant
3. **`ClassificationStep` redundans** — `pipeline/adapters/classifier_adapter.py` + `services/classifier/service.py` mar biztositja a pipeline-szinten, `services/email_connector/service.py` a connector szinten.
4. **Alembic 043 redundans** — `workflow_runs.output_data` JSONB mar tarolja a classifikacios eredmenyeket (query evidence: `emails.py:264,1073`).
5. **EmailSource → IntakePackageSink mar wired** (Phase 1d complete, `sources/email_adapter.py` + `sources/sink.py:process_next()` helper).

**Rescope-olt S105 feladat = ~3h, nem ~8h.**

### Hova tartunk — Rescoped S105 (Sprint K UC3)

Kanonikus ClassificationResult unifikacio + vekony orchestrator (`scan_and_classify`) + uj thin API endpoint + integration test. **Semmi tobb.** IntentRoutingPolicy → S106 (volt S106), UI badges → S107 (volt S107).

### Jelenlegi allapot

```
27 service | 181 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1994 unit PASS | 413 E2E collected | 0 uj migration (rescope szerint)
Branch: feature/v1.4.7-email-intent @ f504aad
Sprint J MERGED | UC2 DONE | UC3 START (rescoped)
```

---

## ELOFELTELEK

```bash
git branch --show-current              # feature/v1.4.7-email-intent
git log --oneline -1                   # f504aad ... (#14)
git describe --tags HEAD               # v1.4.5-sprint-j-uc2
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet             # exit 0
.venv/Scripts/python.exe -m ruff format --check src/ tests/            # exit 0
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# Expected: 1994 passed, 1 skipped, 1 xpassed
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current             # 042
```

Dependencies: Docker PG (5433), Redis (6379) futnak. `.venv` Python 3.12.

---

## FELADATOK

### LEPES 1 — Read architect findings (readonly, 10 min)

Erositsd meg az alabbi file-ok aktualis tartalmat, nehogy vakon kovessed a fenti verdikt-idezetet:

```bash
# Canonical ClassificationResult (operational, runtime-consumed)
sed -n '40,120p' src/aiflow/services/classifier/service.py

# Duplicate protocol-level definition (to become re-export)
cat src/aiflow/models/protocols/classification.py

# ABC placeholder (to become real import)
sed -n '25,35p' src/aiflow/providers/interfaces.py

# Skill-local variant (leave alone; skill-internal contract)
sed -n '40,80p' skills/email_intent_processor/models/__init__.py

# Existing orchestration stubs
grep -n "process_next\|sink.handle\|ClassifierAdapter\|ClassifierService" src/aiflow/sources/ src/aiflow/services/email_connector/ src/aiflow/services/classifier/

# Existing scan endpoints (ne dubli­kald)
grep -n "router.post\|@router" src/aiflow/api/v1/emails.py | head -30
```

**Ha a valosag elter az architect verdikttol** (pl. time elteltevel barki atirta a file-okat) → STOP, ismetelt architect review.

### LEPES 2 — Canonical ClassificationResult unify (C2 condition, ~30 min)

**Cel:** Egyetlen source-of-truth `ClassificationResult` — `src/aiflow/services/classifier/service.py` marad a canonical.

**Modositasok:**

1. `src/aiflow/models/protocols/classification.py`:
   - A 3-field `ClassificationResult`-t **re-export aliasra** cserelni:
     ```python
     from aiflow.services.classifier.service import ClassificationResult

     __all__ = ["ClassificationResult"]
     ```
   - Ha vannak consumer-ek akik a 3-field formatot varjak, listazd ki es adj hozzajuk TODO-t (de S105-ben NE modositsd oket, S106-ban).

2. `src/aiflow/providers/interfaces.py`:
   - A `ClassificationResult = Any` placeholder-t valodi importra cserelni (TYPE_CHECKING alatt hasznaltul).

3. `intent` field **NE** adj hozza — az architect kifejezetten ajanlotta: a `label`/`confidence` mezok mar szemantikusak (lasd `emails.py:517`-ben `result.label -> intent_id` mapping). Ez csokkenti a blast radius-t.

**Unit test update:**
- Ha letezik `tests/unit/models/protocols/test_classification.py` — add hozza a re-export check-et (assert `ClassificationResult is services.classifier.service.ClassificationResult`).
- Futtasd: `pytest tests/unit/models/protocols tests/unit/services/classifier -q --no-cov`

### LEPES 3 — Thin scan-classify orchestrator (C3, ~1h)

**File:** `src/aiflow/services/email_connector/orchestrator.py` (UJ, ~80 sor).

```python
"""Scan-classify orchestrator for EmailSource → IntakePackageSink → Classifier.

Thin composition layer. Does NOT define new pipeline steps.
"""
from __future__ import annotations

import structlog
from aiflow.sources.base import SourceAdapter
from aiflow.sources.sink import IntakePackageSink, process_next
from aiflow.services.classifier.service import ClassifierService, ClassificationResult

logger = structlog.get_logger(__name__)

async def scan_and_classify(
    adapter: SourceAdapter,
    sink: IntakePackageSink,
    classifier: ClassifierService,
    *,
    tenant_id: str,
    max_items: int = 10,
) -> list[tuple[str, ClassificationResult]]:
    """Fetch → sink → classify loop. Returns (package_id, result) tuples."""
    results: list[tuple[str, ClassificationResult]] = []
    for _ in range(max_items):
        package = await process_next(adapter, sink)
        if package is None:
            break
        text = package.descriptions[0].text if package.descriptions else ""
        if not text:
            continue
        result = await classifier.classify(text, tenant_id=tenant_id)
        # Persist via existing workflow_runs path (DO NOT create new table)
        await _persist_workflow_run(package, result, tenant_id)
        results.append((package.package_id, result))
        logger.info(
            "email_connector.scan_and_classify.item_done",
            tenant_id=tenant_id,
            package_id=package.package_id,
            label=result.label,
            confidence=result.confidence,
        )
    return results
```

**Persistence:** reuse `workflow_runs` insert logic — masold/extractold ki `emails.py`-bol (jelenleg kozel duplikalt helyeken van, pl. 948-950, 1253-1255 soron) egy kozos `_persist_workflow_run()` helper-be.

### LEPES 4 — Thin API endpoint (C4, ~30 min)

**File:** `src/aiflow/api/v1/emails.py` (meglevo router, csak bovites).

Uj endpoint: `POST /api/v1/emails/scan/{config_id}` — `config_id` az `email_connector` config (tenant + provider). Body: `{max_items: int = 10}`.

```python
@router.post("/scan/{config_id}", response_model=ScanResponse)
async def scan_and_classify_endpoint(
    config_id: str,
    req: ScanRequest,
    tenant: TenantContext = Depends(get_tenant),
) -> ScanResponse:
    """Scan inbox → sink → classify. Results persist via workflow_runs."""
    adapter = await build_email_adapter(config_id, tenant)
    sink = get_sink(tenant)
    classifier = get_classifier(tenant)
    tuples = await scan_and_classify(adapter, sink, classifier,
                                     tenant_id=tenant.tenant_id,
                                     max_items=req.max_items)
    return ScanResponse(processed=len(tuples), items=[...])
```

**Request/Response schema** pydantic-modellekkel. OpenAPI drift utan: `scripts/export_openapi.py`.

### LEPES 5 — Integration test (~1h)

**File:** `tests/integration/services/email_connector/test_scan_and_classify.py`.

- Real Docker PG (conftest), sklearn-only classifier strategy (deterministic, no LLM).
- 2 fixture email (hu + en), `EmailSourceAdapter` stub vagy in-memory source.
- Trigger `scan_and_classify()` → assert:
  - `workflow_runs` table-ben 2 sor `skill_name='email_intent_processor'`, `status='completed'`, `output_data.intent` non-empty.
  - `IntakePackage` row-k letrejottek.
  - Structlog event `email_connector.scan_and_classify.item_done` tuzelt (caplog).

Futtatas: `PYTHONPATH=src pytest tests/integration/services/email_connector/ -q --no-cov`.

### LEPES 6 — Docs + skill count fixups (C5, ~15 min)

1. `CLAUDE.md`:
   - "7 skill" → "**8 skill**" (pontos lista ellenorizni: `ls skills/` — CLAUDE.md is szamol).
   - Key Numbers frissites: `8 skills`, `1 uj integration test`, etc.

2. `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K scope-row:
   - S105 scope: rescope-olt leiras (contract unify + thin glue, NEM uj step/tabla).
   - S106: IntentRoutingPolicy per tenant (nem valtozott).
   - S107: UI `Emails.tsx` badges + routing chip (nem valtozott).
   - S108: Prompts.tsx v2 (nem valtozott).
   - S109: Golden-path E2E + PR cut + tag `v1.4.7-sprint-k-uc3` (nem valtozott).

3. `session_prompts/S105_v1_4_7_sprint_k_kickoff_prompt.md` — a tetejere **ADD** egy admonition-t:
   ```
   > ⚠️ SUPERSEDED 2026-04-22 by architect rescope. Aktualis scope: S106_v1_4_7_contract_unify_and_glue_prompt.md
   ```

### LEPES 7 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/
cd aiflow-admin && npx tsc --noEmit && cd ..    # ha UI erintett (nem varhato)
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/email_connector/ -q --no-cov
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/e2e --collect-only -q
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current     # meg mindig 042 — NINCS 043
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py
git diff --stat docs/api/openapi.*

/session-close S106
```

---

## STOP FELTETELEK

**HARD:**
1. `services/classifier/service.py:ClassificationResult` mezoi elterek az architect findings-tol (pl. time-elteltevel valaki modositotta) → ismeteld meg az architect review-t.
2. `workflow_runs` tabla meglevo structuraja nem alkalmas az `intent` perzisztalasahoz JSON-mezoben (pl. hianyzik `output_data` JSONB column) → architect agent.
3. 3+ helyen tort kozbenso teszt a re-export miatt → STOP, scope-split S105/S106 kozott.

**SOFT:**
1. Ha `ClassifierService.classify()` signature uj parameter-t ker (pl. tenant-specific prompts) amit nem varunk → dokumentald S106 follow-up-kent.
2. Ha `email_connector` config schema nem tamogat `config_id`-alapu lookup-ot → fallback: `POST /api/v1/emails/scan` body-ban kuldott `provider_config`-ra (no URL param).

---

## ARCHITECT FINDINGS REFERENCIA (eredeti teljes verdikt a S105-pre session transcriptben)

| # | Severity | Finding | File |
|---|----------|---------|------|
| 1 | CRITICAL | 2 versenyzo ClassificationResult (+1 skill-local IntentResult) | `services/classifier/service.py:48`, `models/protocols/classification.py:17`, `skills/email_intent_processor/models/__init__.py:52` |
| 2 | HIGH | ClassifierAdapter + service mar letezik — uj ClassificationStep redundans | `pipeline/adapters/classifier_adapter.py` |
| 3 | HIGH | Alembic 043 `classification_results` tabla redundans — workflow_runs.output_data JSONB mar tarol | `emails.py:264,1073,334` |
| 4 | MEDIUM | Skill name drift: `email_intent` vs `email_intent_processor` | `skills/`, CLAUDE.md, NEXT.md (v1) |
| 5 | MEDIUM | EmailSource + IntakePackageSink mar wired (Phase 1d) | `sources/email_adapter.py`, `sources/sink.py` |
| 6 | LOW | `intent`/`intent_confidence` field-ek NE adjunk hozza — `label`/`confidence` szemantikusak | `services/classifier/service.py` |

---

## SESSION VEGEN

```
/session-close S106
```

Utana `/clear` es S107 (IntentRoutingPolicy per tenant, `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K).
