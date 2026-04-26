# AIFlow [Sprint W] — Session SW-1 Prompt (Real PromptWorkflow extraction wire-up)

> **Datum:** 2026-04-26 (snapshot date — adjust if session runs later)
> **Branch:** `feature/w-sw1-prompt-workflow-extraction` (cut from `main` after the post-Sprint-V audit PR squash-merges).
> **HEAD (expected):** post-Sprint-V audit close PR squash on top of `ee3f5ff` (Sprint V SV-5 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** post-Sprint-V audit. `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` + `docs/post_sprint_v_audit.md`.
> **Terv:** `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` §2 / SW-1 row.
> **Session tipus:** IMPLEMENTATION (extraction stage wire-up — real LLM, real PromptWorkflow descriptors).

---

## 1. MISSION

The unblocker. SV-2 shipped the `DocumentRecognizerOrchestrator.run()` that returns an EMPTY `DocExtractionResult` after classification + intent routing. SW-1 wires the real LLM-driven extraction step so the recognize endpoint produces fields, not just a doc-type match. After SW-1, operators can run the doc_recognizer end-to-end on real documents.

### Five deliverables

1. **Extend `DocumentRecognizerOrchestrator.run()` extraction stage** — after the classifier match, resolve the descriptor's `extraction.workflow` via `PromptWorkflowExecutor.resolve_for_skill("document_recognizer", descriptor.extraction.workflow)`.
2. **Per-step LLM invocation** — for each resolved `(step_id, prompt_def)`, build the input dict (parsed text + per-field schema), invoke the LLM (`models_client.generate(...)`), capture cost.
3. **Per-step cost preflight** — wire `CostPreflightGuardrail.check_step(step_name, model, input_tokens, max_output_tokens, ceiling_usd)` (Sprint U S154 API). On `allowed=False` → raise `CostGuardrailRefused` (Sprint T S149 pattern).
4. **Field mapping + validators** — parse the LLM JSON response, build `dict[str, DocFieldValue]` per the descriptor's `extraction.fields` schema. Implement 7 validator functions: `non_empty`, `regex:<pattern>`, `iso_date`, `before_today`, `after_today`, `min:N`, `max:N`. Failures → `validation_warnings`, not crashes.
5. **Backward-compat for hu_invoice** — when descriptor is `hu_invoice`, the executor delegates to `invoice_extraction_chain` (Sprint T S149 reuse). UC1 byte-stable; doc_recognizer is an alternative entry point with the same shape.

### Out of scope for SW-1

- New doctype descriptors (Sprint V already shipped 5).
- Admin UI changes (SV-4 surface unchanged).
- Per-doctype real-document fixtures (SV-FU-1 = SW-2 scope).
- Multi-tenant rename (SS-FU-1/5 = SW-3 scope).
- `AIFLOW_ENV=prod` boot guard (SM-FU-2 = SW-4 scope).

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint V closed 2026-04-26 with 5 PRs (#50–#54). The doc_recognizer skill scaffolds production-usable: 5 doctypes + 1 PromptWorkflow descriptor (`id_card_extraction_chain`) + admin UI + API router + Alembic 048. **But extraction returns empty** — the SV-2 placeholder.

### Hova tartunk

SW-1 (this session) fills the placeholder. SW-2 adds live Playwright. SW-3 finishes `customer`→`tenant_id`. SW-4 production guards + Langfuse listing + script `--output`. SW-5 close + tag `v1.7.0`.

### Jelenlegi állapot

```
27 service | 201 endpoint (32 routers) | 51 DB tabla | 48 Alembic (head: 048)
2606 unit collected / 1 skipped (ST-SKIP-1 conditional Azure Profile B)
~116 integration | 432 e2e collected
27 UI oldal | 8 skill | 22 pipeline adapter
6 PromptWorkflow descriptors | 5 doctype descriptors
5 ci.yml jobs | 6 nightly-regression.yml jobs | 1 pre-commit hook
DocRecognizer rule engine: 100% top-1 on 8-fixture starter corpus.
Default-off rollout preserved.
```

### Key files for SW-1

| Role | Path |
|---|---|
| Sprint W plan | `01_PLAN/120_SPRINT_W_KICKOFF_PLAN.md` (§2 / SW-1 row, §3 gate matrix, §4 R1+R2) |
| Audit | `docs/post_sprint_v_audit.md` |
| Orchestrator skeleton (SW-1 modifies `run()`) | `src/aiflow/services/document_recognizer/orchestrator.py` |
| Validators target file (NEW) | `src/aiflow/services/document_recognizer/validators.py` |
| LLM invocation pattern reuse | Sprint T S149 `skills/invoice_processor/workflows/process.py` (`_resolve_workflow_step` + `_enforce_step_cost_ceiling`) |
| PromptWorkflowExecutor | `src/aiflow/prompts/workflow_executor.py` |
| CostPreflightGuardrail | `src/aiflow/guardrails/cost_preflight.py` (Sprint U S154 `check_step` API) |
| Doctype descriptors | `data/doctypes/hu_invoice.yaml`, `hu_id_card.yaml` (SW-1 priority targets) |

---

## 3. ELOFELTETELEK

```bash
git switch main
git pull --ff-only origin main
git checkout -b feature/w-sw1-prompt-workflow-extraction
git log --oneline -5                                              # confirm post-Sprint-V audit squash on tip
PYTHONPATH=src .venv/Scripts/python.exe -m alembic current        # head: 048
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1  # 2606 collected
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --quiet
PYTHONPATH=src .venv/Scripts/python.exe scripts/measure_doc_recognizer_accuracy.py 2>&1 | tail -10  # 5 doctypes 100% PASS
```

Stop, ha:
- Post-Sprint-V audit PR not yet merged → wait or escalate.
- Alembic head ≠ 048 → drift; investigate.
- DocRecognizer accuracy script reports any below-SLO on the starter corpus → halt; SW-1 cannot proceed without a stable rule-engine baseline.

---

## 4. FELADATOK

### LEPES 1 — `services/document_recognizer/validators.py`

7 validator functions, all pure-Python:

```python
def non_empty(value: Any) -> tuple[bool, str | None]: ...
def regex(value: Any, pattern: str) -> tuple[bool, str | None]: ...
def iso_date(value: Any) -> tuple[bool, str | None]: ...
def before_today(value: Any) -> tuple[bool, str | None]: ...
def after_today(value: Any) -> tuple[bool, str | None]: ...
def min_value(value: Any, n: float) -> tuple[bool, str | None]: ...
def max_value(value: Any, n: float) -> tuple[bool, str | None]: ...

def apply_validators(field_value: Any, validator_specs: list[str]) -> list[str]:
    """Return a list of warning strings (empty list = all pass)."""
```

Validator strings come from doctype YAML's `field.validators: ["regex:^\\d{8}-\\d-\\d{2}$", "iso_date"]`. Parse the prefix (`regex:` / `min:` / `max:`) and dispatch.

Tests: per-validator happy + sad path (14 tests minimum).

### LEPES 2 — Extend `DocumentRecognizerOrchestrator.run()`

Replace the SV-2 placeholder (empty `DocExtractionResult`) with:

```python
async def run(self, ctx, *, tenant_id, doc_type_hint=None, pii_detected=False):
    match, descriptor = await self.classify(...)
    if match is None or descriptor is None:
        return None

    # NEW: real extraction stage
    extraction = await self._extract(ctx, descriptor, tenant_id=tenant_id)

    intent = self.route_intent(descriptor, extraction, match, pii_detected=pii_detected)
    return match, extraction, intent

async def _extract(self, ctx, descriptor, *, tenant_id) -> DocExtractionResult:
    # 1. Resolve the PromptWorkflow descriptor
    resolved = self._workflow_executor.resolve_for_skill(
        SKILL_NAME, descriptor.extraction.workflow
    )
    if resolved is None:
        # Flag-off: empty fields + warning
        return DocExtractionResult(
            doc_type=descriptor.name,
            extracted_fields={},
            validation_warnings=[f"workflow {descriptor.extraction.workflow!r} not resolved"],
        )
    workflow, prompt_map = resolved

    # 2. Per-step LLM invocation with cost preflight
    extracted: dict[str, DocFieldValue] = {}
    total_cost_usd = 0.0
    start = time.monotonic()
    for step in workflow.steps:
        if not step.required:
            continue  # validate-style steps skip in SW-1
        prompt_def = prompt_map.get(step.id)
        if prompt_def is None:
            continue
        ceiling = step.metadata.get("cost_ceiling_usd") if step.metadata else None
        decision = self._cost_guardrail.check_step(
            step_name=step.id,
            model=prompt_def.config.model,
            input_tokens=len(ctx.text) // 4 + 256,
            max_output_tokens=prompt_def.config.max_tokens,
            ceiling_usd=ceiling,
        )
        if not decision.allowed:
            raise CostGuardrailRefused(...)

        # Compile prompt + invoke LLM
        messages = prompt_def.compile(variables={"text": ctx.text})
        response = await self._models_client.generate(
            messages=messages, model=prompt_def.config.model,
            temperature=prompt_def.config.temperature,
            max_tokens=prompt_def.config.max_tokens,
        )
        total_cost_usd += response.cost_usd

        # Parse JSON; map to DocFieldValue with confidence
        # ... (per-step output_key handling)

    # 3. Apply field validators
    warnings: list[str] = []
    for field_spec in descriptor.extraction.fields:
        if field_spec.name not in extracted:
            if field_spec.required:
                warnings.append(f"{field_spec.name} required but not extracted")
            continue
        field_warnings = apply_validators(
            extracted[field_spec.name].value, field_spec.validators
        )
        warnings.extend(f"{field_spec.name}: {w}" for w in field_warnings)

    elapsed_ms = (time.monotonic() - start) * 1000
    return DocExtractionResult(
        doc_type=descriptor.name,
        extracted_fields=extracted,
        validation_warnings=warnings,
        cost_usd=total_cost_usd,
        extraction_time_ms=elapsed_ms,
    )
```

Wire `_workflow_executor`, `_cost_guardrail`, `_models_client` via constructor injection.

### LEPES 3 — Backward-compat for `hu_invoice`

When `descriptor.name == "hu_invoice"`, the executor naturally resolves `invoice_extraction_chain` (Sprint T S149's existing descriptor). UC1 byte-stable because `invoice_processor.workflows.process` keeps using the same descriptor; the doc_recognizer is just an alternate entry point that hits the same chain.

**Verify** that the doc_recognizer extraction round-trip produces the same shape that `invoice_processor.workflows.process` produces (same field names + ranges); if not, document the difference + decide whether to backfill or hand-map.

### LEPES 4 — Tests

- **+12 unit** (validators × 7 happy/sad + extraction stage shape × 5):
  - `tests/unit/services/document_recognizer/test_validators.py` — per-validator
  - `tests/unit/services/document_recognizer/test_orchestrator_extraction.py` — workflow resolution + per-step cost preflight + JSON parse + field mapping
- **+2 integration** (skip-by-default behind `OPENAI_API_KEY`):
  - `tests/integration/services/document_recognizer/test_extraction_real.py` — real OpenAI gpt-4o-mini call on `hu_invoice` + `hu_id_card` starter fixtures

### LEPES 5 — Validate + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ skills/ --quiet
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/ -q --tb=line | tail -3   # 2620+ collected (+14)
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/unit/services/document_recognizer/ -v
# Real-LLM integration (only when OPENAI_API_KEY available):
PYTHONPATH=src .venv/Scripts/python.exe -m pytest tests/integration/services/document_recognizer/ -v --timeout=120

# UC1 regression check
AIFLOW_LANGFUSE__ENABLED=false PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/integration/skills/test_uc1_golden_path.py --timeout=300

git add src/aiflow/services/document_recognizer/ \
        tests/unit/services/document_recognizer/ \
        tests/integration/services/document_recognizer/
git commit -m "feat(sprint-w): SW-1 — DocRecognizer PromptWorkflow extraction wire-up (SV-FU-4)"
git push -u origin feature/w-sw1-prompt-workflow-extraction
gh pr create --base main --head feature/w-sw1-prompt-workflow-extraction \
  --title "Sprint W SW-1 — DocRecognizer PromptWorkflow extraction wire-up"
```

Then `/session-close SW-1` — which queues SW-2 (live Playwright + corpus extension).

---

## 5. STOP FELTETELEK

**HARD:**
1. UC1 invoice_processor golden-path regression — UC1 < 75% accuracy or `invoice_number` < 90% → halt; SW-1 must NOT touch UC1 behavior.
2. LLM cost per recognize call exceeds $0.05 on the starter corpus → investigate per-step ceilings + descriptor configuration.
3. `OPENAI_API_KEY` available but real-LLM integration test fails on both starter fixtures → halt; debug LLM JSON parsing or prompt template.

**SOFT:**
- LLM returns inconsistent JSON shape across runs → tighten prompt + add `response_format: json_object`.
- Per-step cost ceiling on `id_card_extraction_chain.fields` (0.02 USD) trips on long fixtures → bump ceiling per-tenant via override or relax ceiling to 0.03.

---

## 6. SESSION VEGEN

```
/session-close SW-1
```

Generates `session_prompts/NEXT.md` for SW-2 (live Playwright + corpus extension).

---

## 7. SKIPPED-ITEMS TRACKER

Carry from Sprint V SV-5 unchanged. Plus:

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SW-SKIP-1 (planned, this session) | `tests/integration/services/document_recognizer/test_extraction_real.py` | Real-OpenAI integration on hu_invoice + hu_id_card | `secrets.OPENAI_API_KEY` |

Sprint V carry-forwards inherit unchanged: ST-SKIP-1, SU-SKIP-1, SU-SKIP-2, SS-SKIP-2, SV-SKIP-1.
