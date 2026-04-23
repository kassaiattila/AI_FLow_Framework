# AIFlow — Session 128 Prompt (Sprint O — Classifier consumption + LLM-context)

> **Datum:** 2026-05-02
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (continues — cut from `main` @ `13a2f08`).
> **HEAD (parent):** S127 commit `885d336` `feat(sprint-o): S127 — AttachmentFeatureExtractor + orchestrator wiring (flag off)` (landed 2026-05-01).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S127 — AttachmentFeatureExtractor + orchestrator wiring.
> Landed: pure-function `extract_attachment_features` + `AttachmentFeatures`
> model + flag-gated `scan_and_classify` hook. Flag-OFF asserted as true
> no-op (no AttachmentProcessor instantiation, no log events, no new
> output_data keys). Flag-ON timing: 65.7 s wall-clock on the 25-fixture
> corpus (p50 139 ms, p95 17.5 s docling cold start) → < 120 s budget gate
> PASS. 22 new unit tests (3 settings + 14 extractor + 5 orchestrator). See
> `docs/uc3_attachment_extract_timing.md` + commit `885d336`.
> **Terv:** `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` §3 S128 +
> `docs/sprint_o_plan.md`.
> **Session tipus:** Feature work — extend `ClassifierInput`, add rule
> boost, opt-in LLM-context path, drop fixture misclass rate by ≥ 50%.

---

## 1. MISSION

Make the classifier **read** `attachment_features` from `ClassifierInput.context`
and use them to fix the Sprint K body-only blind spots:

1. **Rule boost** (default, no LLM cost): when `invoice_number_detected` OR
   `total_value_detected` is True **and** the body-intent confidence is
   below 0.6, boost the closest `EXTRACT`-class label by +0.3 (capped at
   0.95).
2. **LLM-context path** (opt-in via `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=true`):
   append the attachment-extract summary (first 500 chars of concatenated
   attachment text + feature summary) to the classification prompt as an
   additional system message.

Backward-compat is mandatory — `ClassifierInput.context` is added as an
**optional** field. Sprint K callers see no behavioural change, and the
Sprint K UC3 golden-path E2E must stay green.

---

## 2. KONTEXTUS

### Honnan jottunk (S127)
Extractor + orchestrator wiring landed flag-off on `885d336`. Flag-ON timing
gate PASS (65.7 s wall, 25 fixtures). Per-fixture booleans look right on
the invoice cohort (6/6 `invoice_number_detected=True`) and contract cohort
(`total_value_detected` partially True from boilerplate `Total ... HUF`
references). **The orchestrator now persists `output_data.attachment_features`
when the flag is on — but the classifier does not yet read them.** S128
closes that loop.

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2218 unit PASS / 1 skip / 1 xpass (Sprint O S127 added 22)
Branch: feature/v1.4.11-uc3-attachment-intent @ 885d336
Fixture: data/fixtures/emails_sprint_o/ (25 .eml)
Baseline: docs/uc3_attachment_baseline.md (Sprint K body-only: 56% misclass)
S127 timing: docs/uc3_attachment_extract_timing.md (65.7 s wall, p50 139 ms)
```

### Hova tartunk
After S128:
- `ClassifierInput.context: dict[str, Any] | None = None` (optional, default
  None, additive).
- `ClassifierService.classify` consumes `context["attachment_features"]`
  when present and applies the rule boost.
- LLM-context path emits a second system message when
  `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT=true` (opt-in within the
  already-on attachment-intent flag).
- `scan_and_classify` threads `output_data["attachment_features"]` into the
  classifier call as `context={"attachment_features": ...}` only when the
  flag is on (preserves OFF = true no-op).
- Fixture misclassification rate drops by **≥ 50% relative to the Sprint K
  body-only baseline** (S126 = 56% misclass → target ≤ 28% with attachment
  features rule-boost only, no LLM-context flag flipped).

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/v1.4.11-uc3-attachment-intent
git log --oneline -3                           # 885d336 S127 on top
ls data/fixtures/emails_sprint_o/*.eml | wc -l # 25
ls docs/uc3_attachment_extract_timing.md       # present (S127 output)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2218 pass
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current   # 045 (head)
docker compose ps                              # postgres + redis healthy
```

---

## 4. FELADATOK

### LEPES 1 — `ClassifierInput.context` extension
- Open `src/aiflow/services/classifier/service.py` and locate the
  `ClassifierInput` (or equivalent input model used by `classify`).
- Add `context: dict[str, Any] | None = Field(default=None,
  description="Optional structured context — e.g. attachment_features.")`.
- **STOP if** the extension would require any non-optional change to the
  contract — plan §4 STOP #5.
- Update `classify(text=..., schema_labels=..., context=None)` signature
  with the new optional kwarg (default None). All Sprint K call-sites must
  keep working unchanged.

### LEPES 2 — `LLMContextSettings` toggle
- Add `llm_context: bool = False` to `UC3AttachmentIntentSettings` (env
  var `AIFLOW_UC3_ATTACHMENT_INTENT__LLM_CONTEXT`). Update the existing
  `TestUC3AttachmentIntentSettings` to cover the new field (defaults +
  env override).

### LEPES 3 — Rule boost implementation
- In `ClassifierService.classify`, when `context` carries
  `attachment_features` and the body-derived top label has
  `confidence < 0.6`:
  - If `invoice_number_detected` OR `total_value_detected` is True, find
    the closest `EXTRACT`-class label in `schema_labels` (Sprint K v1
    schema labels with `intent_class == "EXTRACT"`, e.g.
    `invoice_question`, `extract_request`).
  - Boost that label's confidence by +0.3, capped at 0.95.
  - Set `result.method = "sklearn+attachment_rule"` (or extend the existing
    method enum if there is one) and add a `reasoning` breadcrumb naming
    the booleans that fired.
- Pure logic — no LLM call, no I/O.

### LEPES 4 — LLM-context path (opt-in)
- When `attachment_intent_settings.llm_context` is True **and** the
  classifier strategy hits the LLM path, append a second system message
  built from:
  - `attachment_features` summary (`invoice_number_detected`,
    `total_value_detected`, `mime_profile`, top-3 `keyword_buckets`).
  - First 500 chars of the concatenated attachment text. To get text the
    orchestrator will need to also forward
    `context["attachment_text_preview"]` — extend the orchestrator helper
    to slice the `extract_attachment_features` input concatenation and
    pass it through.
- When `llm_context` is False → no extra system message. Assert this in a
  unit test.

### LEPES 5 — Orchestrator wiring update
- In `_maybe_extract_attachment_features` (or a small follow-up), build a
  `context_payload = {"attachment_features": features.model_dump()}` and
  optionally `"attachment_text_preview"` when `llm_context` is on.
- Pass `context=context_payload` into `classifier.classify(...)` from
  `scan_and_classify` **only** when the flag is on. Flag-OFF path stays
  unchanged.

### LEPES 6 — Unit tests (≥ 15)
Under `tests/unit/services/classifier/`:
1–6: `ClassifierInput.context` round-trip + default None + serialization.
7–11: rule-boost matrix — body confidence above/below 0.6 × invoice_number
True/False × total_value True/False × no-feature baseline.
12–13: rule boost respects the 0.95 cap.
14: LLM-context flag OFF → no extra system message added (mock LLM client).
15: LLM-context flag ON → second system message emitted with the expected
preview + summary.
16 (bonus): orchestrator passes context only when flag-on (mirror the
S127 wiring assertion with rule-boost evidence).

### LEPES 7 — Integration test (1, real Docker PG)
- Under `tests/integration/services/email_connector/test_attachment_intent_classify.py`:
  - Use the S106 `_FakeImapBackend` pattern.
  - Pick fixture `001_invoice_march.eml` (or similar invoice-PDF cohort
    sample).
  - Run `scan_and_classify` with `attachment_intent_settings.enabled=True`
    against real Postgres.
  - Assert the persisted `output_data` has `attachment_features` AND the
    label is in the EXTRACT class (`invoice_question` or equivalent).
  - Single `@pytest.mark.asyncio` method (asyncpg pool/event-loop trap).

### LEPES 8 — Misclass-rate re-measurement
- Add a `--with-attachment-intent` flag to `scripts/measure_uc3_baseline.py`
  (or duplicate the script as `scripts/measure_uc3_attachment_intent.py`)
  that runs the same 25 fixtures with the flag ON and rule-boost active.
- Compare misclass rate to the S126 body-only baseline (56%). Target:
  **≤ 28%** misclass (≥ 50% relative drop). Write
  `docs/uc3_attachment_intent_results.md`.
- Plan §4 STOP #2: if attachment processing p95 > 10 s per email, halt.
- Plan §4 STOP #3: if Sprint K UC3 golden-path E2E regresses, halt.

### LEPES 9 — Regression + lint + commit + push
- `/regression` → 2218 + ≥15 unit pass; +1 integration; Sprint K E2E
  golden-path 4/4 unchanged.
- `/lint-check` clean on changed files (pre-existing `scripts/*` lint debt
  is out of scope).
- Commit: `feat(sprint-o): S128 — classifier reads attachment_features +
  rule boost + opt-in LLM-context (flag off)` + Co-Authored-By.
- Push.

### LEPES 10 — NEXT.md for S129
- Overwrite `session_prompts/NEXT.md` with the S129 prompt
  (UI surfacing + Playwright E2E + live-test).

---

## 5. STOP FELTETELEK

**HARD (hand back to user):**
1. `ClassifierInput.context` extension would require any non-optional
   field — plan §4 STOP #5; halt and redesign.
2. Sprint K UC3 golden-path E2E regresses — halt until root-caused (plan
   §4 STOP #2).
3. Misclass rate after rule-boost stays > 40% (relative drop < 30%) — the
   rule boost design is wrong; halt and rescope with user.
4. Attachment processing p95 latency > 10 s/email on the 25-fixture run
   (already 17.5 s p95 in S127 due to docling cold start). If S128's
   measurement still shows that, halt and consider warm-cache
   instrumentation (carry to S129) instead of failing.

**SOFT (proceed with note):**
- If LLM-context path produces a single-shot improvement that the rule
  boost cannot match on certain cohorts, document in retro and keep
  `llm_context=false` as ship-default. S129 may surface a UI toggle.
- If the EXTRACT-class label list changes between schema versions,
  hard-code the candidate set behind a tiny constant + add a TODO for
  the schema-aware lookup follow-up.

---

## 6. NYITOTT (carried)

Sprint N, M, J, resilience `Clock` seam — no change. Sprint O carries the
"docling p95 cold start" (17.5 s) into S128 as a known-soft. The
warm-cache fix is pre-empted as an S129 follow-up unless misclass-rate
gating forces it earlier.

Resilience `Clock` seam deadline was 2026-04-30 (now 2 days past). Decide
in the S128 retro: either unquarantine `test_circuit_opens_on_failures`
as a Lane C piggyback, or document a new deadline.

---

## 7. SESSION VEGEN

```
/session-close S128
```

Utana: `/clear` -> `/next` -> S129 (UI surfacing + Playwright E2E).
