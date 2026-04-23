# AIFlow — Session 127 Prompt (Sprint O — AttachmentFeatureExtractor)

> **Datum:** 2026-05-01
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (continues — cut from `main` @ `13a2f08`).
> **HEAD (parent):** S126 kickoff commit (landed 2026-04-30, see `git log`).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S126 — UC3 attachment-aware intent **KICKOFF + BASELINE**.
> Landed: 25-email fixture corpus (`data/fixtures/emails_sprint_o/` — 6 invoice-PDF
> / 6 contract-DOCX / 6 body-only / 7 mixed) + `scripts/measure_uc3_baseline.py`
> + `docs/uc3_attachment_baseline.md`. **Sprint K body-only baseline: 56% misclass
> (14/25), manual-review-like 40%, p95 95 ms, wall-clock 0.8 s → GATE PASS
> (≥ 15% floor).** Sprint O value proven.
> **Terv:** `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` §3 S127 + `docs/sprint_o_plan.md`.
> **Session tipus:** Feature work — build the pure-function extractor +
> orchestrator wiring + unit coverage. No classifier change yet (that is S128).

---

## 1. MISSION

Build `AttachmentFeatureExtractor` — a **pure-function** module that, given a
list of `ProcessedAttachment` objects produced by the Sprint K
`AttachmentProcessor`, derives a compact `AttachmentFeatures` Pydantic model
that S128 will feed into the classifier. Wire it into `scan_and_classify`
behind the Sprint O feature flag so it is a true no-op when off.

---

## 2. KONTEXTUS

### Honnan jottunk (S126)
Baseline measurement shows the attachment-signal gap is real and sized:
- Invoice-attachment cohort: **3/6 correct** (50% miss — body is too thin).
- Contract-DOCX cohort: **2/6 correct** (67% miss — 'sign the attached' body wins feedback/keywords_no_match).
- 10/25 emails route to `unknown` / `keywords_no_match` → MANUAL_REVIEW in prod.
- SUPPORT cohort: 3/3 correct → Sprint O must NOT regress that.

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2196 unit PASS / 1 skip / 1 xpass
Branch: feature/v1.4.11-uc3-attachment-intent
Feature flag: AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=false (default)
Fixture: data/fixtures/emails_sprint_o/ (25 .eml, 389 KB)
Baseline: docs/uc3_attachment_baseline.md (56% misclass, Sprint K body-only)
```

### Hova tartunk
After S127:
- Extractor module under `src/aiflow/services/classifier/attachment_features.py`.
- `AttachmentFeatures` Pydantic model consumable by S128's classifier.
- `scan_and_classify` runs the extractor **only** when flag ON; cached as
  `workflow_runs.output_data.attachment_features` JSONB.
- ≥ 12 new unit tests (fixture-driven, no LLM/docling roundtrips — mock
  `ProcessedAttachment` payloads inline).
- Flag-ON end-to-end timing check: all 25 fixture emails process in
  < 120 s wall-clock including real docling attachment extraction.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/v1.4.11-uc3-attachment-intent
git log --oneline -4                           # S126 kickoff + baseline on top of 13a2f08
ls data/fixtures/emails_sprint_o/*.eml | wc -l # 25
ls docs/uc3_attachment_baseline.md             # present
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1
alembic current                                # head 045 — S127 adds 0 migrations
docker compose ps                              # postgres + redis healthy
```

---

## 4. FELADATOK

### LEPES 1 — Feature flag surface
- Add `UC3AttachmentIntentSettings` under `src/aiflow/config/` with
  `AIFLOW_UC3_ATTACHMENT_INTENT__` env prefix. Fields: `enabled: bool = False`,
  `max_attachment_mb: int = 10`, `total_budget_seconds: float = 5.0`.
- 2–3 unit tests on the settings (defaults, env override, validator).

### LEPES 2 — `AttachmentFeatures` model + extractor
- `src/aiflow/services/classifier/attachment_features.py` exposing
  `extract_attachment_features(attachments: list[ProcessedAttachment], *,
  settings: UC3AttachmentIntentSettings | None = None) -> AttachmentFeatures`.
- Pydantic `AttachmentFeatures` fields (per plan §3):
  - `invoice_number_detected: bool` — regex on concatenated attachment text:
    `\b(INV|INVOICE|SZAMLASZAM)[-/:\s]*\d{3,}\b` (HU + EN, case-insensitive).
  - `total_value_detected: bool` — currency + number near total/össz/amount
    keywords; simple regex is fine for first cut.
  - `table_count: int` — `sum(len(a.tables) for a in attachments)`.
  - `mime_profile: str` — dominant mime across attachments
    (`application/pdf`, `...wordprocessingml.document`, `image/*`, `other`).
  - `keyword_buckets: dict[str, int]` — counts of bucket hits
    (`invoice`, `contract`, `support`, `report`) using word-boundary
    case-insensitive regex.
  - `text_quality: float` — mean of `a.metadata["quality_score"]` when
    present, else 0.0.
- **Pure function.** No async, no I/O, no DB, no LLM.
- Skip attachments where `mime_type` ∈ `AttachmentProcessor.OCR_TYPES`
  (image short-circuit per plan §5 out-of-scope).
- Skip attachments > `settings.max_attachment_mb * 1024 * 1024` bytes using
  `len(a.metadata.get("raw_bytes", b""))` if present; otherwise skip when
  `a.error` is non-empty.

### LEPES 3 — `scan_and_classify` orchestrator hook
- Thread `UC3AttachmentIntentSettings` through to `scan_and_classify`
  (default constructed — no breaking-change to existing call sites).
- When `settings.enabled` is True **and** the package has attachments:
  - Run `AttachmentProcessor` over the package's files
    (respecting `total_budget_seconds` via `asyncio.wait_for`).
  - Call `extract_attachment_features(processed)` and merge the result
    into `output_data["attachment_features"]` as JSONB.
  - Add structlog event
    `email_connector.scan_and_classify.attachment_features_extracted`
    with the top-level feature booleans + mime_profile.
- When flag is OFF: **zero** new log events, no `AttachmentProcessor`
  instantiation, no extra DB writes. Assert this in a unit test.

### LEPES 4 — Unit tests (≥ 12)
Under `tests/unit/services/classifier/test_attachment_features.py`:
1. Empty attachment list → zeroed features + mime_profile="none".
2. Single invoice PDF with `INV-2026-0042` in text → `invoice_number_detected=True`.
3. Invoice-like text without the regex → `invoice_number_detected=False`.
4. `Total: 48,500 HUF` in text → `total_value_detected=True`.
5. Contract DOCX text + `NDA` keyword → `keyword_buckets["contract"] ≥ 1`.
6. Support-log PDF → `keyword_buckets["support"] ≥ 1`, not invoice.
7. `table_count` sum across two attachments.
8. Image attachment (`image/png`) → skipped, not in mime_profile.
9. Oversize attachment (> 10 MB in `metadata`) → skipped.
10. Failed attachment (`.error != ""`) → skipped, does not crash.
11. Mixed mime → dominant returned in `mime_profile`.
12. `text_quality` mean across two attachments with quality scores.
13. (bonus) HU + EN invoice numbers both match the regex.

### LEPES 5 — Fixture-driven flag-ON integration
- Add a **manual** helper `scripts/measure_uc3_attachment_extract_cost.py`
  (reuses the S126 `_FakeImapBackend` pattern) that runs all 25 fixtures
  with flag ON, asserts wall-clock < 120 s, dumps a short
  `docs/uc3_attachment_extract_timing.md`.
- This is NOT in CI — it is a one-shot measurement for the S127 retro.

### LEPES 6 — Regression + lint + commit
- `/regression` → 2196+~15 unit tests green, Sprint K 4 UC3 E2E unchanged.
- `/lint-check` clean.
- Commit: `feat(sprint-o): S127 — AttachmentFeatureExtractor + orchestrator
  wiring (flag off)` + Co-Authored-By.
- Push.

### LEPES 7 — NEXT.md for S128
- Overwrite `session_prompts/NEXT.md` with the S128 prompt
  (classifier consumption + LLM-context path).

---

## 5. STOP FELTETELEK

**HARD (hand back to user):**
1. Any extractor call path that runs when the feature flag is OFF — violates
   the ship-off contract. Halt and redesign wiring.
2. Flag-ON timing on the 25-fixture run > 120 s — docling throughput is a
   gating concern; halt and rescope the per-email budget with user.
3. Sprint K UC3 golden-path E2E regresses — halt until root-caused.
4. Breaking `ClassifierInput` contract (non-optional field added) — plan
   §4 STOP condition #5; halt and redesign.

**SOFT (proceed with note):**
- If the `total_value_detected` regex has > 20% false positives on the 25
  fixtures, document in retro; S128 can rule-boost-only on
  `invoice_number_detected` instead.
- If attachments without `metadata["raw_bytes"]` are common (likely), the
  oversize-skip heuristic is weak; note in retro and defer to S128 with a
  proper byte-threading path.

---

## 6. NYITOTT (carried)

Sprint N, M, J, resilience `Clock` seam — no change. See
`docs/sprint_n_retro.md` §"Follow-up issues" and the Sprint M + J carry
lists. Sprint O carries none of these into S127 unless a STOP condition
forces it.

Resilience `Clock` seam deadline was 2026-04-30 (yesterday). Document the
decision in the Sprint O retro — either unquarantine
`test_circuit_opens_on_failures` as a Lane C piggyback this session, or
explicitly defer with a new deadline.

---

## 7. SESSION VEGEN

```
/session-close S127
```

Utana: `/clear` -> `/next` -> S128 (Classifier consumption + LLM-context).
