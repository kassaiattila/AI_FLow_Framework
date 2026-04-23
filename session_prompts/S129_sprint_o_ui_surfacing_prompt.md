# AIFlow — Session 129 Prompt (Sprint O — UI surfacing + Playwright E2E)

> **Datum:** 2026-05-03
> **Branch:** `feature/v1.4.11-uc3-attachment-intent` (continues — cut from `main` @ `13a2f08`).
> **HEAD (parent):** S128 commit `5975296` `feat(sprint-o): S128 — classifier reads attachment_features + signal-aligned rule boost (flag off)` (landed 2026-05-02).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S128 — classifier consumption + signal-aligned rule
> boost. 23 new unit tests (rule-boost matrix, signal alignment, body-label
> protection, opt-in LLM-context path), 1 new integration test (real PG +
> 001_invoice_march fixture lands in EXTRACT_INTENT_IDS), full 25-fixture
> re-measurement: **misclass 56% → 32%** (24 pts absolute / 42.9% relative).
> Headline gains: invoice_attachment 3/6 → 6/6, contract_docx 2/6 → 5/6.
> See `docs/uc3_attachment_intent_results.md` + commit `5975296`.
> **Terv:** `01_PLAN/112_SPRINT_O_UC3_ATTACHMENT_INTENT_PLAN.md` §3 S129 +
> `docs/sprint_o_plan.md`.
> **Session tipus:** Frontend — UI card + locales + 1 Playwright E2E +
> `/live-test attachment_signals`.

---

## 1. MISSION

Surface the new `output_data.attachment_features` payload on the email
detail page so end users can see *why* the classifier picked the label.
Add the "Attachment signals" collapsible card below the existing
intent/priority cards on `EmailDetail.tsx`. Cover with one Playwright E2E
that exercises the full pipeline (scan → fixture → detail → assert card
visible). Land a `/live-test` report.

---

## 2. KONTEXTUS

### Honnan jottunk (S128)
Classifier now applies the signal-aligned rule boost end-to-end. The
orchestrator persists `output_data.attachment_features` (S127 wiring) AND
the `output_data.method` carries `+attachment_rule` when the boost fired.
Backend is feature-complete for Sprint O. UI work is the last code change
before retro + PR.

### Jelenlegi allapot
```
27 service | 190 endpoint (29 routers) | 50 DB table | 45 Alembic (head: 045)
2241 unit PASS / 1 skip / 1 xpass (Sprint O S127 +22, S128 +23)
+1 integration (real Postgres) — UC3 attachment-intent classify
Branch: feature/v1.4.11-uc3-attachment-intent @ 5975296
Misclass: 56% baseline → 32% with flag ON (docs/uc3_attachment_intent_results.md)
```

### Hova tartunk
After S129:
- `EmailDetail.tsx` shows an "Attachment signals" card (collapsible,
  rendered only when `attachment_features` is present on the run). Per
  attachment row: mime, page count (if available), invoice-number badge,
  total-value badge, table count, top-3 keyword buckets, quality score.
- EN + HU locale strings landed.
- 1 Playwright E2E green (`tests/e2e/v1_4_11_uc3_attachment/test_attachment_signals.py`):
  fixture invoice → flag-on scan → open detail → assert card visible +
  `invoice_number_detected` badge + label is in EXTRACT_INTENT_IDS.
- `/live-test attachment_signals` ran, report at
  `tests/ui-live/attachment_signals.md`.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/v1.4.11-uc3-attachment-intent
git log --oneline -3                           # 5975296 S128 on top
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # 2241 pass
docker compose ps                              # postgres + redis healthy
cd aiflow-admin && npx tsc --noEmit && cd ..   # tsc clean baseline
```

---

## 4. FELADATOK

### LEPES 1 — UI types + API surface
- Confirm the GET endpoint that drives `EmailDetail.tsx` already returns
  `output_data.attachment_features` (Sprint O orchestrator persists it as
  JSONB — endpoint may already be passing it through via a `dict[str, Any]`
  field). If not, extend the response model to include it as an optional
  field. **STOP if** the change requires a migration.
- Add `AttachmentFeatures` TypeScript type under `aiflow-admin/src/types/`
  mirroring the Pydantic model (booleans + table_count + mime_profile +
  keyword_buckets + text_quality + considered/skipped counts).

### LEPES 2 — `AttachmentSignalsCard` component
- New component under
  `aiflow-admin/src/components/email-intent/AttachmentSignalsCard.tsx`
  (Untitled UI + Tailwind v4 + React Aria — see skill `aiflow-ui-pipeline`).
- Layout per skill rules:
  - Card header: `t("email.attachment_signals.title")` + collapsible chevron.
  - Body: per-attachment row (or single rollup row if only one attachment):
    - mime profile chip
    - badges: invoice-number-detected, total-value-detected (use
      Untitled UI Badge component, color tokens for true/false)
    - table count + text quality
    - keyword_buckets top-3 as small chips
  - Footer line: `attachments_considered` / `attachments_skipped`.
- Render only when `result.output_data.attachment_features` is truthy and
  `attachments_considered > 0`. Otherwise render nothing (no empty card
  flash).

### LEPES 3 — Page wiring
- `aiflow-admin/src/pages-new/EmailDetail.tsx` (or whichever current page
  renders email run detail): mount `AttachmentSignalsCard` below the
  existing intent/priority cards. Pass the run's `attachment_features` +
  `method` (so the card can mark "boosted by attachment rule" when
  `method` contains `attachment_rule`).

### LEPES 4 — Locales
- Add EN + HU strings under `aiflow-admin/src/locales/{en,hu}.json` (or
  the project's existing locale folder):
  - `email.attachment_signals.title`
  - `email.attachment_signals.invoice_number_badge`
  - `email.attachment_signals.total_value_badge`
  - `email.attachment_signals.table_count`
  - `email.attachment_signals.text_quality`
  - `email.attachment_signals.boosted_indicator`
  - `email.attachment_signals.considered_skipped`
- HU strings written natively (not translated), matching the project's
  HU/EN mixed style.

### LEPES 5 — Playwright E2E
- New folder `tests/e2e/v1_4_11_uc3_attachment/` with `__init__.py` +
  `test_attachment_signals.py`:
  - Use the existing E2E fixture-driven scan harness (similar to
    `tests/e2e/uc3/...` if present, or write a thin harness that POSTs to
    the scan endpoint with fixture 002_invoice_en_supplier — body-only
    Sprint K already classifies this correctly so the test focuses on
    the UI render path, not the boost itself).
  - Set `AIFLOW_UC3_ATTACHMENT_INTENT__ENABLED=true` in the test env.
  - Open `/emails/<run-id>` and assert:
    - `getByRole('heading', name='Attachment signals')` is visible.
    - `getByText('invoice_received')` (the EXTRACT label) is visible.
    - The invoice-number badge (truthy state) is rendered.
- Add the `e2e` mark to `pytest.ini`/`pyproject.toml` if it isn't already
  registered (PostToolUse will pick that up).

### LEPES 6 — Live-test
- `/live-test attachment_signals` against the dev API + UI.
- Capture screenshot/path summary into
  `tests/ui-live/attachment_signals.md` per project convention.

### LEPES 7 — Regression + lint + tsc + commit + push
- `/regression` → 2241 unit unchanged; 4 + 1 = 5 integration tests; new
  E2E green. Sprint K golden-path E2E green.
- `/lint-check` clean (Python + tsc).
- Commit: `feat(sprint-o): S129 — UI attachment signals card + Playwright
  E2E + live-test report` + Co-Authored-By.
- Push.

### LEPES 8 — NEXT.md for S130
- Overwrite `session_prompts/NEXT.md` with the S130 prompt
  (Sprint O retro + PR description + CLAUDE.md numbers + tag `v1.4.11`).

---

## 5. STOP FELTETELEK

**HARD (hand back to user):**
1. UI surface requires a non-additive API/DB change — halt and rescope.
2. Sprint K UC3 golden-path E2E regresses — halt until root-caused.
3. Playwright cannot start (missing browser binaries) — halt and ask
   user to run `npx playwright install`.
4. Live-test cannot reach the API/UI ports (8102 / 5173) — halt and ask
   user to start `make api` / `cd aiflow-admin && npm run dev`.

**SOFT (proceed with note):**
- If the existing email detail endpoint does not surface
  `attachment_features`, add a small response-model extension and note
  in the retro that S128 should have shipped that. Ship it here.
- If the project uses MUI / shadcn instead of Untitled UI in
  email-intent components (audit shows the codebase historically mixed
  libs), use the dominant local convention rather than re-tooling.

---

## 6. NYITOTT (carried)

Sprint N, M, J, resilience `Clock` seam (now 3 days past 2026-04-30
deadline) — document decision in S129 retro or piggyback an unquarantine
of `test_circuit_opens_on_failures` in this session. Sprint O carries
the SOFT "42.9% relative drop falls 7 pts short of 50% target" — already
documented in S128 commit body and `docs/uc3_attachment_intent_results.md`;
S130 retro will recap.

---

## 7. SESSION VEGEN

```
/session-close S129
```

Utana: `/clear` -> `/next` -> S130 (Sprint O retro + PR + tag).
