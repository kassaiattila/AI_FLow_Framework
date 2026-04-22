# AIFlow v1.4.7 Sprint K — Session 105 Prompt (UC3 kickoff: EmailSource → IntakePackageSink → Intent classifier glue)

> **Datum:** 2026-04-26 (tervezett folytatas)
> **Branch:** `feature/v1.4.7-email-intent` — **NEW** branch, kiindulas: `main` @ tag `v1.4.5-sprint-j-uc2` (Sprint J merge utan).
> **HEAD prereq:** PR #14 merged + `v1.4.5-sprint-j-uc2` tag pushed. Fallback: ha meg nem merge-olt, allj meg es jelezd.
> **Port:** API 8102 | Frontend Vite 5175 (Sprint K next port)
> **Plan:** `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` §4 Sprint K (S104 scope row: EmailSource → IntakePackageSink → Intent classifier skill glue).
> **Session tipus:** IMPLEMENTATION / WIRING — UC3 kickoff. Code risk: MEDIUM (uj router + skill integracio). Process risk: LOW.

---

## KONTEXTUS

### Honnan jottunk

- **Sprint J (UC2 RAG) DONE** 2026-04-25, tag `v1.4.5-sprint-j-uc2`, PR #14 merged.
  - S100: EmbedderProvider ABC + BGE-M3/Azure OpenAI + EmbeddingDecision + alembic 040 + PolicyEngine.pick_embedder.
  - S101: ChunkerProvider ABC + UnstructuredChunker + rag_engine opt-in provider-registry ingest + alembic 041.
  - S102: ChunkViewer UI + chunks API provenance.
  - S103: pgvector flex-dim alembic 042 + OpenAIEmbedder + retrieval baseline MRR@5 both profiles PASS.
  - S104: resilience flake quarantine + retro + PR cut + tag.
- Retro: `docs/sprint_j_retro.md`, PR desc: `docs/sprint_j_pr_description.md`, quarantine log: `docs/quarantine.md`.

### Hova tartunk — Sprint K UC3

- **Cel:** Email intent golden-path. Mailbox scan → EmailSource adapter → IntakePackageSink → email_intent skill classifier → intent label persisted on ClassificationResult → admin UI `Emails.tsx` shows list with intent badges.
- **Sprint K ujrarendezese (replan §4):**
  - **S105 (this session):** Glue — EmailSource adapter (Phase 1d DONE) → IntakePackageSink → email_intent skill → ClassificationResult with intent field. 1 integration test end-to-end with real PG.
  - **S106:** IntentRoutingPolicy (intent → action) per tenant.
  - **S107:** UI `Emails.tsx` — scan button, intent badges, routing chip, trace link.
  - **S108:** Prompts.tsx v2 — edit Langfuse-synced prompts from UI.
  - **S109:** Golden-path E2E + PR cut + tag `v1.4.7-sprint-k-uc3`.
- **Acceptance S105:** `POST /api/v1/emails/scan/{mailbox_id}` → EmailSource.fetch() → sink.handle() per email → ClassificationStep runs email_intent skill → ClassificationResult persisted with `intent` label. Integration test PASS with real Docker PG.

### Jelenlegi allapot (Sprint J merge utan — merge utan verify!)

```
27 service | 181 endpoint | 50 DB tabla | 42 Alembic migration (head: 042)
1994 unit PASS | 55+ integration PASS | 413 E2E collected
Branch: feature/v1.4.7-email-intent (uj, kiindulas main@v1.4.5-sprint-j-uc2)
Sprint J MERGED | UC2 DONE | UC3 START
```

---

## ELOFELTELEK

```bash
# 1. Verify Sprint J merge + tag
git fetch origin --tags
git log --oneline main -3           # keresd: merge commit v1.4.5-sprint-j-uc2
git tag -l "v1.4.5-sprint-j-uc2"    # legalabb 1 sor

# 2. Ha MERGED + TAG OK → cut uj branch
git checkout main && git pull origin main
git checkout -b feature/v1.4.7-email-intent

# 3. Baseline ellenorzes
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet            # exit 0
.venv/Scripts/python.exe -m ruff format --check src/ tests/           # exit 0  (S104 CI tanulsag!)
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
# 1994 PASS / 1 SKIP / 1 XPASSED (resilience quarantine, OK)
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current            # 042
```

**Ha PR #14 MEG NEM MERGED:** STOP. Jelezd a usernek, hogy PR review + merge szukseges mielott Sprint K indul.

---

## FELADATOK

### LEPES 1 — Discovery (readonly)

Terkepezd fel a meglevo email_intent skill-t es az EmailSource adapter-t:

```bash
ls skills/email_intent/                               # prompts, tests, __init__.py
cat skills/email_intent/prompts/*.yaml | head -80
ls src/aiflow/sources/                                 # email_adapter.py, sink.py, association.py
grep -n "email_intent" src/aiflow/ -r                 # existing wiring points
grep -n "class ClassificationResult\|classifier_skill" src/aiflow/ -r
```

**Kerdesek amikre valaszt keresel:**
- Milyen input/output I/O modellt var az `email_intent` skill?
- Melyik router kezeli a `POST /api/v1/emails/scan/*` endpoint-ot? (`src/aiflow/api/v1/` keres)
- Van-e mar `ClassificationStep` vagy keszitendo?
- Hogyan kapcsolodjon a `PolicyEngine` (policy-driven skill choice)?

### LEPES 2 — Contract: `ClassificationResult` + `intent` field

Replan §2 processing flow: `ClassificationResult` (Phase 2a contract). Ha mar letezik, adj hozza `intent: str | None` + `intent_confidence: float | None` field-et (Pydantic v1 stub, extra=forbid). Ha meg nem letezik, hozd letre `src/aiflow/contracts/classification_result.py`-ban.

- Export `aiflow.contracts` __init__.py-bol.
- Unit test: `tests/unit/contracts/test_classification_result.py` — 5 teszt min (construct, to_dict, round-trip, missing intent OK, forbid extra).

### LEPES 3 — Glue wiring: EmailSource → IntakePackageSink → ClassificationStep → ClassificationResult

**File-ok amiket modositod / keszitel:**

- `src/aiflow/api/v1/emails.py` (ha letezik, egeszitsd ki; ha nem, hozd letre)
  - `POST /api/v1/emails/scan/{mailbox_id}` — fetches EmailSourceAdapter, sink handles, triggers classification.
- `src/aiflow/pipeline/steps/classification_step.py` (NEW or augmentation)
  - Input: `IntakePackage`. Hivja az `email_intent` skill-t a skill runner-en keresztul. Output: `ClassificationResult` (intent + confidence).
  - Emit structlog event `pipeline.classification_done`.
- `src/aiflow/services/classification/` service (ha nincs, Sprint K hozza letre) — persist ClassificationResult to DB.
- Alembic 043: `classification_results` table (schema-only init — tenant_id, intake_package_id FK, intent, intent_confidence, classified_at, raw_response jsonb).

**Alembic rule:** `nullable=True` minden uj oszlopnak, zero-downtime. Up/down/up verify Docker PG-n.

### LEPES 4 — Integration test (real PG + deterministic LLM)

`tests/integration/services/classification/test_email_intent_glue.py`:

- Fixture: 2 test email (hu + en), `_AIFLOW_LLM_MODE=deterministic` env (ha elerheto — kulonben skip-pel).
- Trigger `POST /api/v1/emails/scan/{mailbox_id}` → assert:
  - IntakePackage row created via sink.
  - ClassificationResult row created with intent label (non-empty).
  - Structlog event `pipeline.classification_done` emitted.
  - Langfuse trace_id set on response header (ha AIFLOW_LANGFUSE_ENABLED).

### LEPES 5 — OpenAPI drift snapshot

```bash
PYTHONPATH=src .venv/Scripts/python.exe scripts/export_openapi.py
git diff --stat docs/api/openapi.*
```

Ha drift → commit `docs(openapi): regen after S105 emails scan endpoint`.

### LEPES 6 — Regression + session-close

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
.venv/Scripts/python.exe -m ruff format --check src/ tests/        # S104 CI tanulsag: check + format-check KELL mindketto!
cd aiflow-admin && npx tsc --noEmit && cd ..                        # ha aiflow-admin erintett
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/classification/ -q --no-cov
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/e2e --collect-only -q
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current          # 043 (uj)

/session-close S105
```

---

## STOP FELTETELEK

- **HARD:** PR #14 meg nem merged → allj meg a LEPES 0-nal.
- **HARD:** `email_intent` skill I/O schema bizonytalan — architect review (`Agent architect`) szukseges a contract stabilizalashoz.
- **HARD:** Alembic 043 breaking change (FK nullable=False uj oszlopon existing adat nelkul) — kerj iranymutatast.
- **HARD:** Integration test FAIL 2 kiserlet utan — root-cause, jelezd.
- **SOFT:** `PolicyEngine.pick_classifier()` (analog pick_embedder) kellhet — ha igen, dokumentald mint follow-up, ne bomld be S105-ot vele.
- **SOFT:** Ha scope >2x a becsultnek (pl. a ClassificationResult contract masutt is modositasra szorul) → split: S105 = glue, S106 contract-uplift, S107 routing policy.

---

## SESSION VEGEN

```
/session-close S105
```

Utana `/clear` es S106 (IntentRoutingPolicy per tenant, replan §4 Sprint K).
