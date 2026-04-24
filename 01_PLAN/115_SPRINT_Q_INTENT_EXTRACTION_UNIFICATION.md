# AIFlow v1.5.0 Sprint Q — Intent + extraction unification

> **Status:** KICKOFF on 2026-05-07 (S135).
> **Branch:** `feature/q-s135-*` etc. (each session its own branch → PR → squash-merge).
> **Parent plan:** `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` §2.
> **Predecessor:** v1.4.12 Sprint P (UC3 intent 4% misclass MERGED `390d4d5`).
> **Target tag (post-merge):** `v1.5.0`.

---

## 1. Goal

Wire the existing `invoice_processor` skill into the UC3 email-intent pipeline so that when the classifier outputs `intent_class == "EXTRACT"` with a PDF/DOCX attachment, the orchestrator extracts structured fields (invoice_number, total_amount, due_date, supplier_name, iban, etc.) and persists them under `workflow_runs.output_data.extracted_fields`. Surface on EmailDetail UI. Separately validate the UC1 golden-path E2E on a curated 10-fixture invoice corpus.

## 2. Sessions

### S135 — Orchestrator wiring + integration test
**Scope.** `AIFLOW_UC3_EXTRACTION__ENABLED` flag (default false). When flag-on + `intent_class=="EXTRACT"` + attachment present, run `invoice_processor.extract()` on each PDF/DOCX attachment, merge the result into `output_data.extracted_fields`. Real-PG integration test on fixture `001_invoice_march`. 10+ unit tests (flag gating, failure modes, schema validation).

### S136 — UI card + Playwright E2E on live stack
**Scope.** `aiflow-admin/src/components-new/ExtractedFieldsCard.tsx` — Tailwind v4 card with key-value grid, `data-testid="extracted-fields-card"`. EN+HU locale. `EmailDetailResponse.extracted_fields` (optional). Playwright E2E seed → live API → visual assertion.

### S137 — UC1 golden-path E2E (invoice_finder real run)
**Scope.** `data/fixtures/invoices_sprint_q/` — 10 anonymized invoice fixtures (PDF+DOCX mix). `scripts/measure_uc1_golden_path.py` runs the full UC1 pipeline (file intake → classifier → invoice_processor → HITL queue threshold). Writes `docs/uc1_golden_path_report.md` with accuracy per field, latency, cost.

### S138 — Sprint Q close
**Scope.** `docs/sprint_q_retro.md`, `docs/sprint_q_pr_description.md`, CLAUDE.md bump, PR + tag `v1.5.0`.

## 3. Success metrics

| Metric | Target |
|---|---|
| Extracted-field accuracy on 10-fixture corpus | ≥ 80% overall, ≥ 90% for invoice_number |
| Cost per extraction (docling + LLM) | < $0.02 |
| p95 latency per extraction | < 15 s |
| UC3 Sprint P misclass not regressed | 4% unchanged |
| Live Playwright E2E | +3 (S135 int + S136 UI + S137 golden) |

## 4. STOP conditions (HARD)

1. UC3 classification regresses from 4% misclass → halt, restore prior behaviour.
2. Extraction cost > $0.05 per invoice live → rescope tenant-gated + document.
3. S137 accuracy < 60% on 10-fixture corpus → corpus curation session needed before proceeding.
4. OpenAI API outage > 30 min mid-sprint → halt and document, retry next day.

## 5. Rollback

Additive + flag-gated (same pattern as Sprint O):
- `AIFLOW_UC3_EXTRACTION__ENABLED=false` → Sprint P tip behaviour.
- No Alembic migration (JSONB key only).
- S137 fixtures isolated in `data/fixtures/invoices_sprint_q/` — no prod impact.
- `git revert` on the 4 squash-merge commits if flag-off insufficient.

## 6. Out of scope

- Per-tenant extraction prompt overrides (Sprint R).
- HITL queue UI improvements beyond a simple count badge (Sprint R/S).
- Non-invoice document types (receipt, contract, quote) — reuse pattern later.
- Cost-aware model tier for extraction (Sprint T).
