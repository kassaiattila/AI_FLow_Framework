# AIFlow — Session 135 Prompt (Sprint Q kickoff — invoice_processor wiring)

> **Datum:** 2026-05-07
> **Branch:** `feature/q-s135-extraction-wiring` (cut from `main` @ `390d4d5`, Sprint P close).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S134 — Sprint P close + tag `v1.4.12`. UC3 intent 4% misclass. UC3 attachment_features persisted in `output_data.attachment_features`. `invoice_processor` skill exists as self-contained, untouched by UC3.
> **Terv:** `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md` §2 S135 + master roadmap `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md`.
> **Session tipus:** Feature work — orchestrator extraction wiring + integration test.

---

## 1. MISSION

Wire `invoice_processor` into the UC3 `scan_and_classify` pipeline behind a new feature flag. When the classifier outputs `intent_class == "EXTRACT"` AND there is at least one PDF/DOCX attachment AND `AIFLOW_UC3_EXTRACTION__ENABLED=true`, the orchestrator runs extraction on each attachment, merges the resulting field dict into `workflow_runs.output_data.extracted_fields`, and emits a structlog event. Flag-off contract: **zero new behaviour** (no import of invoice_processor, no extra DB writes, no log events).

---

## 2. KONTEXTUS

### Honnan jottunk (Sprint P close)
Sprint P closed with UC3 intent at 4% misclass on the 25-fixture corpus. The classifier knows "this email is `invoice_received`", but the orchestrator does not call anything downstream to actually extract the invoice's structured fields. `invoice_processor` is a separate skill (`skills/invoice_processor/`) with its own extraction pipeline (docling → LLM + Azure DI → Pydantic validation). Sprint Q bridges these.

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2278 unit PASS / 1 skip / 0 xpass (resilience unquarantine landed Sprint O FU-5)
~101 integration PASS
428 E2E collected
Branch: main @ 390d4d5
Flags: AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false default
       AIFLOW_UC3_ATTACHMENT_INTENT__CLASSIFIER_STRATEGY=sklearn_first
Fixture: data/fixtures/emails_sprint_o/ (25 .eml, 6 invoice_attachment cohort)
```

### Hova tartunk (S135 output)
- New flag `AIFLOW_UC3_EXTRACTION__ENABLED=false` (default, ship-off).
- `UC3ExtractionSettings` nested on `AIFlowSettings`.
- `_maybe_extract_invoice_fields(files, *, settings, workflow_run_id)` helper in orchestrator — lazy-imports `invoice_processor` so flag-off never pays the cost.
- `scan_and_classify` calls it after classification when `result.intent_class == "EXTRACT"` and attachments exist.
- `workflow_runs.output_data.extracted_fields` new JSONB key (additive, no Alembic).
- 10+ unit tests covering flag gating, intent_class gating, error handling, per-attachment merge.
- 1 integration test (real PG + real docling + real OpenAI) on fixture `001_invoice_march`, asserting `invoice_number` kinyerve + non-empty `total_amount`.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/q-s135-extraction-wiring
git log --oneline -3                           # 390d4d5 S134 on top
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2278 pass
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current   # 045 (head)
docker compose ps                              # postgres + redis healthy
echo $OPENAI_API_KEY                           # set (from .env)
ls skills/invoice_processor/                   # skill self-contained
```

---

## 4. FELADATOK

### LEPES 1 — Settings
- `UC3ExtractionSettings` in `src/aiflow/core/config.py`:
  - env prefix `AIFLOW_UC3_EXTRACTION__`
  - `enabled: bool = False`
  - `max_attachments_per_email: int = 5`
  - `total_budget_seconds: float = 60.0`
  - `extraction_budget_usd: float = 0.05` (per-invoice hard ceiling)
- Mount on `AIFlowSettings`.
- 3 unit tests (defaults, env override, direct construction).

### LEPES 2 — Orchestrator helper
- `_maybe_extract_invoice_fields(files, *, settings, workflow_run_id)` in `src/aiflow/services/email_connector/orchestrator.py`.
- Lazy imports `invoice_processor.workflows.extract` (or equivalent entry point — discover via `grep -n "def extract" skills/invoice_processor/`).
- For each file where mime is PDF/DOCX and flag-on: run extraction, time-budget via `asyncio.wait_for(settings.total_budget_seconds)`, cost-budget via the returned result's cost field.
- Return `{"extracted_fields": {per-filename dict}, "total_cost_usd": float}` or `None` on timeout/error.
- **Lazy import pattern** — no module-level `from skills...` to keep flag-off a true no-op.

### LEPES 3 — scan_and_classify wiring
- After classification, check `classifier_result.intent_class == "EXTRACT"`.
- Use `_resolve_intent_class` (Sprint O FU-2) to derive intent_class from `result.label` if not populated.
- Call `_maybe_extract_invoice_fields` only when flag-on + EXTRACT + files non-empty.
- Merge payload into `output_data["extracted_fields"]`.
- Emit structlog event `email_connector.scan_and_classify.extracted_fields_persisted` with field count + cost.

### LEPES 4 — Unit tests (≥ 10)
`tests/unit/services/email_connector/test_extraction_wiring.py`:
1. flag OFF → no invoice_processor import, no log event
2. flag OFF by default when settings omitted
3. flag ON + non-EXTRACT intent → skipped
4. flag ON + EXTRACT but no files → skipped
5. flag ON + EXTRACT + PDF → extractor monkeypatched, result merged
6. per-file failure → per-file error recorded, other files still extracted
7. timeout → `extracted_fields=None` + timeout log event
8. cost budget breach → early-return with reason
9. multi-attachment per-filename merge shape
10. `output_data["method"]` unchanged (no `+extraction` suffix)

Stub `invoice_processor.extract()` with a deterministic fake result to keep hermetic.

### LEPES 5 — Integration test (1, real stack)
`tests/integration/services/email_connector/test_extraction_real.py`:
- Use Sprint O fixture `001_invoice_march.eml`.
- Real Postgres + real docling + real OpenAI (load `.env`).
- Skip if `OPENAI_API_KEY` missing or docling can't extract from the fixture PDF (reuse `_docling_can_read_fixture` from `test_attachment_intent_classify.py` pattern).
- Assert: `output_data["extracted_fields"]` present, contains `invoice_number` matching `INV-2026-0001`, `total_amount` non-zero.

### LEPES 6 — Regression + lint + commit + push
- `/regression` → 2278+~10 unit green, existing integration tests unchanged.
- `/lint-check` clean.
- `scripts/export_openapi.py` refresh (no model change expected, but belt-and-braces).
- Commit: `feat(sprint-q): S135 — invoice_processor wiring into UC3 EXTRACT path (flag off)` + Co-Authored-By.
- Push → gh pr create → open PR against `main`.

### LEPES 7 — NEXT.md for S136
- Overwrite `session_prompts/NEXT.md` with the S136 prompt (UI ExtractedFieldsCard + Playwright E2E on live stack).

---

## 5. STOP FELTETELEK

**HARD:**
1. UC3 Sprint P golden-path test regresses (classifier misclass changes) — halt.
2. `invoice_processor.extract()` entry point signature doesn't match expectations — halt + design session.
3. Integration test cost > $0.05 for single invoice — budget ceiling breached, rescope.
4. Alembic migration becomes necessary — halt (scope creep; JSONB key was the design).

**SOFT:**
- If `invoice_processor` returns non-Pydantic dict — normalize at orchestrator layer + note in retro.
- If docling cold start pushes `total_budget_seconds` over 60s on first fixture — apply FU-4 warmup at startup + note.

---

## 6. SESSION VEGEN

```
/session-close S135
```

Utana: auto-sprint loop indul S136-ra (UI + Playwright E2E).
