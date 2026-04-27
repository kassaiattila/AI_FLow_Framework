# AIFlow [Sprint X] — Session SX-2 Prompt (UC3 → DocRecognizer routing layer)

> **Template version:** 1.0 (mandatory Quality target header).
> **Source template:** `session_prompts/_TEMPLATE.md`.
> **Closes:** Sprint W pipeline gap §1 — UC3 EXTRACT path is hardcoded to `invoice_processor` (Sprint Q S135).

---

## Quality target (MANDATORY)

- **Use-case:** UC3 + DocRecognizer composite (no single UC quality metric — this is a **routing wiring** session that preserves UC3 + UC1 byte-stable while introducing a new DocRecognizer-mediated dispatch path)
- **Metric:** composite gate — (a) UC3 4/4 unchanged on flag-off; (b) UC1 ≥ 75% / `invoice_number` ≥ 90% on flag-on `hu_invoice` path; (c) new id_card extraction successful on flag-on (≥ 3 fields with confidence ≥ 0.7 on the SW-1 starter fixture)
- **Baseline (now):** UC3 4/4 (Sprint K, byte-stable since); UC1 ≥ 75% / `invoice_number` ≥ 90% (Sprint Q baseline); id_card extraction = **N/A** (no path exists today — UC3 EXTRACT silently misroutes ID-card attachments to `invoice_processor`)
- **Target (after this session):** all three gates green. Flag-off path byte-identical to pre-SX-2; flag-on path gains the id_card capability while keeping UC1 byte-stable on the `hu_invoice` route.
- **Measurement command:** `pytest tests/integration/skills/test_uc3_4_intents.py tests/integration/skills/test_uc1_golden_path.py tests/integration/skills/test_uc3_doc_recognizer_routing_real.py -v`

> Note (deviation from "one-UC quality push"): Sprint X is operator-directed
> as a multi-UC pipeline-unification sprint (see `docs/post_sprint_w_audit.md`).
> SX-2 uses a **composite gate** rather than a single quality number because
> the value of the session is wiring, not metric improvement on an existing
> golden path. Acceptance is binary: all three sub-gates pass.

---

## Goal

Replace Sprint Q S135's hardcoded `invoice_processor.workflows.process(...)` call with **DocRecognizer-mediated dispatch**. Every UC3 EXTRACT email runs DocRecognizer on its attachments first; the detected doctype picks the extraction handler.

**Default-off** (`AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED=false`) so the pre-SX-2 path stays byte-identical. **Flag-on path** keeps UC1 byte-stable: `hu_invoice` continues to route through the existing `invoice_processor`. Other doctypes (`hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`) route through the SW-1 DocRecognizer extraction wire-up.

This is the biggest behaviour-changing session of Sprint X. The default-off discipline + UC1 + UC3 golden-path gates protect every existing flow.

---

## Predecessor context

> **Datum:** 2026-04-26 (snapshot date — adjust if session runs later)
> **Branch:** `feature/x-sx2-uc3-doc-recognizer-routing` (cut from `main`
> after the SX-1 audit + kickoff PR squash-merges).
> **HEAD (expected):** SX-1 close PR squash on top of `0c7cd28` (PR #61
> honest alignment audit + ROADMAP + CLAUDE slim) and `83af02f`-or-later
> (PR #62 intake pipeline plan + audit publish).
> **Predecessor session:** SX-1 — Sprint X kickoff (audit + plan publish).

---

## Pre-conditions

- [ ] SX-1 PR (#62) merged on `main` (intake pipeline plan + post-Sprint-W audit + NEXT → SX-2)
- [ ] Branch cut: `feature/x-sx2-uc3-doc-recognizer-routing`
- [ ] Stack runnable (`bash scripts/start_stack.sh --validate-only` GREEN)
- [ ] `bash scripts/run_quality_baseline.sh --uc UC3 --output json` produces UC3 4/4 baseline
- [ ] `bash scripts/run_quality_baseline.sh --uc UC1 --output json` produces UC1 ≥ 75% baseline
- [ ] `OPENAI_API_KEY` env var set (real-corpus integration test)
- [ ] PostgreSQL Docker container running (5433)
- [ ] DocRecognizer 5 doctype YAML descriptors present at `data/doctypes/`
- [ ] Sprint W SW-1 `DocumentRecognizerOrchestrator.run(...)` callable (extraction wire-up landed)

---

## Predecessor surfaces (existing, do not modify)

- UC3 orchestrator: `skills/email_intent_processor/orchestrator.py` — Sprint Q S135 `_maybe_extract_invoice_fields` (calls `invoice_processor.workflows.process` directly via lazy import; SX-2 wraps this).
- UC3 intent resolver: Sprint O FU-2 `_resolve_intent_class(...)` (gates EXTRACT detection).
- DocRecognizer orchestrator: `src/aiflow/services/document_recognizer/orchestrator.py` — `DocumentRecognizerOrchestrator.classify(attachment) → DocClassification` and `.run(attachment, doctype) → DocExtractionResult` (Sprint W SW-1).
- Cost preflight: `CostPreflightGuardrail.check_step(...)` (Sprint U S154).
- Existing settings: `UC3ExtractionSettings` (Sprint Q S135) — flag for the existing extraction wire-up.
- Existing schema: `EmailDetailResponse.extracted_fields` (Sprint Q S136) + `EmailDetailResponse.attachment_features` (Sprint O S129).
- Existing UC1 byte-stable test: `tests/integration/skills/test_uc1_golden_path.py`.
- Existing UC3 4/4 test: `tests/integration/skills/test_uc3_4_intents.py`.

---

## Tasks

1. **New settings module.** Add `UC3DocRecognizerRoutingSettings`:
   - `enabled: bool = False` (env `AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__ENABLED`)
   - `confidence_threshold: float = 0.6`
   - `total_budget_seconds: float = 30.0`
   - `unknown_doctype_action: Literal["fallback_invoice_processor", "rag_ingest", "skip"] = "fallback_invoice_processor"`
   - Pydantic v2 `BaseSettings` with `env_prefix="AIFLOW_UC3_DOC_RECOGNIZER_ROUTING__"`

2. **New routing helper.** `_route_extract_by_doctype(email, attachments) -> RoutingDecision`:
   - For each attachment, lazy-import `DocumentRecognizerOrchestrator`, call `classify(attachment)` with per-attachment `asyncio.wait_for(timeout=settings.total_budget_seconds / max(1, len(attachments)))`
   - Pick top-1 doctype if confidence ≥ `settings.confidence_threshold`
   - Dispatch:
     - `hu_invoice` → `invoice_processor.workflows.process(...)` (byte-stable pre-SX-2 path)
     - other known doctypes → `DocumentRecognizerOrchestrator.run(attachment, doctype)` → field-map to `EmailDetailResponse.extracted_fields` shape
     - confidence below threshold OR doctype unknown → `settings.unknown_doctype_action` policy
   - Returns a `RoutingDecision` Pydantic model (per-attachment list: `attachment_id`, `doctype_detected`, `doctype_confidence`, `extraction_path`, `extraction_outcome`, `cost_usd`, `latency_ms`)

3. **Per-extraction cost preflight.** Each routed extraction calls `CostPreflightGuardrail.check_step(step_name, model, input_tokens, max_output_tokens, ceiling_usd)`. On `allowed=False` → set `extraction_outcome="refused_cost"` and skip that attachment (do not raise; per-attachment isolation pattern).

4. **Per-extraction error isolation.** A single attachment's exception does not poison the rest. Wrap each per-attachment dispatch in try/except + log WARN with the attachment_id; mark that row's `extraction_outcome="failed"`.

5. **Wire into Sprint Q `_maybe_extract_invoice_fields`.** When `routing.enabled` is true, replace the direct `invoice_processor` call with `_route_extract_by_doctype`. When disabled, keep the existing direct call (byte-stable).

6. **Extend `EmailDetailResponse`.** Additive `routing_decision: Optional[RoutingDecisionView]` field. Backward-compat: absent when flag is off (`exclude_none=True`). Schema-stable on flag-off.

7. **OpenAPI snapshot refresh.** `python scripts/dump_openapi.py > tests/snapshots/openapi.json` (or equivalent). Schema delta limited to the new field.

---

## Tests (10 unit + 1 integration)

- `test_settings_defaults` — flag default off; threshold 0.6; budget 30 s; `unknown_doctype_action="fallback_invoice_processor"`
- `test_route_dispatches_hu_invoice_to_invoice_processor` — mock classify → `hu_invoice` confidence 0.9; assert `invoice_processor.workflows.process` called; `extraction_path="invoice_processor"`
- `test_route_dispatches_other_doctypes_to_doc_recognizer` (4 cases: hu_id_card, hu_address_card, eu_passport, pdf_contract) — assert `DocumentRecognizerOrchestrator.run` called; `extraction_path="doc_recognizer_workflow"`
- `test_below_threshold_falls_through` — confidence 0.4 < 0.6 → `extraction_path` per `unknown_doctype_action`
- `test_unknown_doctype_action_fallback_invoice_processor` — unrecognized doctype → invoice_processor called
- `test_unknown_doctype_action_rag_ingest` — unrecognized doctype → rag_ingest fallback called
- `test_unknown_doctype_action_skip` — unrecognized doctype → no extractor called; `extraction_path="skipped"`
- `test_per_attachment_error_isolation` — first attachment raises; second succeeds; second's row present
- `test_cost_ceiling_refusal_marks_outcome` — `CostPreflightGuardrail.check_step` returns `allowed=False`; `extraction_outcome="refused_cost"`; no LLM call
- `test_total_budget_timeout_returns_partial` — synthetic slow-mock attachment + 0.1 s budget → some attachments routed, others timeout-skipped
- **Integration** (skip-by-default, `OPENAI_API_KEY`): real PG + real OpenAI; 2-fixture test (1 hu_invoice + 1 hu_id_card EML); flag-on; assert hu_invoice routes to invoice_processor (UC1 byte-stable extraction) AND hu_id_card routes to DocRecognizer (≥ 3 fields with confidence ≥ 0.7)

---

## Acceptance criteria

- [ ] **Quality target met** — `pytest tests/integration/skills/test_uc3_4_intents.py tests/integration/skills/test_uc1_golden_path.py tests/integration/skills/test_uc3_doc_recognizer_routing_real.py -v` PASS (all three composite sub-gates)
- [ ] All unit tests PASS (`make test`)
- [ ] DocRecognizer 5-doctype top-1 accuracy unchanged on starter corpus (`scripts/measure_doc_recognizer_accuracy.py --strict` PASS)
- [ ] No regression on byte-stable golden paths (UC3 4/4 + UC1 ≥ 75% / `invoice_number` ≥ 90% unchanged on flag-off)
- [ ] `make lint` clean
- [ ] OpenAPI snapshot refreshed (only the new `routing_decision` field on `EmailDetailResponse`; **zero new paths**)
- [ ] PR opened against `main`, CI green
- [ ] `01_PLAN/ROADMAP.md` Sprint X table row SX-2 status → DONE

---

## Constraints

- **Default-off byte-stable.** Flag-off, the pre-SX-2 UC3 EXTRACT path is preserved bit-for-bit: `_maybe_extract_invoice_fields` calls `invoice_processor.workflows.process` directly. Test `test_uc3_4_intents.py` runs unchanged on flag-off.
- **UC1 byte-stable on flag-on `hu_invoice` path.** When DocRecognizer detects `hu_invoice`, the dispatch goes back through `invoice_processor.workflows.process` — same module, same call, same result. Test `test_uc1_golden_path.py` ≥ 75% / `invoice_number` ≥ 90% gates this.
- **No new endpoint.** SX-2 changes only the orchestrator. The `/api/v1/emails/{id}` response gains an additive optional field (`routing_decision`); router routing unchanged.
- **No DB schema change.** Alembic 050 (`routing_runs` table) is SX-3, not SX-2.
- **No UI change.** SX-2 is server-side; UI surfaces (`/routing-runs` page) are SX-3; `/aszf/chat` upgrade is SX-4.
- **Lazy imports.** `DocumentRecognizerOrchestrator` import-time chain pulls in OCR / parser stacks; lazy-import inside `_route_extract_by_doctype` to avoid boot-time penalty (mirror Sprint Q S135 lazy-import pattern).

---

## STOP conditions

**HARD:**
- UC3 4/4 regression on flag-off — by definition the byte-stable path. Halt.
- UC1 < 75% or `invoice_number` < 90% on flag-on `hu_invoice` path. Halt; the dispatch back to `invoice_processor` is broken.
- DocRecognizer accuracy regression on starter corpus. Halt; the classifier was perturbed.
- OpenAPI drift on routes (only `EmailDetailResponse` schema delta is allowed; any path delta is a HARD stop).

**SOFT:**
- Per-attachment latency on emails with > 5 attachments exceeds the 30 s budget. Adjust `total_budget_seconds` or per-attachment slicing.
- LLM cost per email exceeds $0.05 on the integration test. Tune `confidence_threshold` upward or per-step descriptor `cost_ceiling_usd`.
- Operator-driven dependency missing (no `OPENAI_API_KEY`) → integration test skips; unit gates still required.

---

## Output / handoff format

The session ends with:

1. PR opened against `main` titled `feat(sprint-x): SX-2 — UC3 → DocRecognizer routing layer (default-off)`
2. PR body summarizes the dispatch + flag-off byte-stable + UC1/UC3 gates green + composite Quality target outcome
3. `/session-close` invoked → generates `session_prompts/NEXT.md` for SX-3 (routing trace `routing_runs` Alembic 050 + 3-route API + admin UI)
4. `01_PLAN/ROADMAP.md` Sprint X table row SX-2 status → DONE
5. (No `docs/SPRINT_HISTORY.md` entry — that lands at SX-5 sprint-close only)

---

## References

- Sprint X plan: `01_PLAN/121_SPRINT_X_INTAKE_PIPELINE_RAG_CHAT_PLAN.md` §SX-2
- Forward queue: `01_PLAN/ROADMAP.md`
- Post-Sprint-W audit: `docs/post_sprint_w_audit.md` §"UC3 → DocRecognizer routing layer"
- Honest alignment audit: `docs/honest_alignment_audit.md`
- Sprint W retro (SW-1 extraction wire-up surfaces): `docs/sprint_w_retro.md`
- Sprint Q S135 pattern (the wrap target): `skills/email_intent_processor/orchestrator.py`
- DocRecognizer service: `src/aiflow/services/document_recognizer/`
- Cost preflight API: Sprint U S154 `CostPreflightGuardrail.check_step()`
- DocType descriptors: `data/doctypes/`
- Quality baseline script: `scripts/run_quality_baseline.sh`
- Reusable settings pattern: Sprint Q `UC3ExtractionSettings`, Sprint O `UC3AttachmentIntentSettings`
