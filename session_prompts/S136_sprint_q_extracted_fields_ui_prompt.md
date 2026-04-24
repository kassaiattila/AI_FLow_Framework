# AIFlow — Session 136 Prompt (Sprint Q S136 — ExtractedFieldsCard + Playwright E2E live stack)

> **Datum:** 2026-05-08
> **Branch:** `feature/q-s136-extracted-fields-ui` (cut from `main` after S135 merge).
> **HEAD (parent):** S135 commit `feat(sprint-q): S135 — invoice_processor wiring into UC3 EXTRACT path (flag off)`.
> **Port:** API 8102 | UI 5173
> **Elozo session:** S135 — orchestrator extraction wiring. `workflow_runs.output_data.extracted_fields` now carries per-filename `{vendor, buyer, header, line_items, totals, extraction_confidence, cost_usd}` when `AIFLOW_UC3_EXTRACTION__ENABLED=true` + intent_class=EXTRACT + PDF/DOCX attachment. 15 unit + 1 real-stack integration (001_invoice_march → INV-2026-0001 extracted).
> **Terv:** `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md` §2 S136.
> **Session tipus:** UI — valós live stack Playwright E2E (no route mock).

---

## 1. MISSION

Surface the new `output_data.extracted_fields` on the email detail page as a dedicated card. Backend already persists the payload (S135); now the admin UI shows it to the operator: vendor, buyer, header (invoice number, currency, dates), line items (top-3 collapsed), totals (net / vat / gross), extraction confidence, per-attachment cost. Real Playwright E2E against the running dev stack (no route mocks).

---

## 2. KONTEXTUS

### S135 output reminder
```
output_data.extracted_fields = {
  "<filename>": {
    "vendor": {"name": ..., "tax_id": ...},
    "buyer": {"name": ..., "tax_id": ...},
    "header": {"invoice_number": ..., "currency": ..., "issue_date": ..., "due_date": ...},
    "line_items": [{"description": ..., "quantity": ..., "unit_price": ..., "total": ...}],
    "totals": {"net_total": ..., "vat_total": ..., "gross_total": ...},
    "extraction_confidence": 0.92,
    "extraction_time_ms": 1500.0,
    "cost_usd": 0.00054,
  },
  ...
}
```

### Jelenlegi allapot
```
Branch: main @ HEAD (S135 squash-merged)
Units: 2296 passed / 1 skipped
Integration: +1 real-stack (S135 extraction on 001_invoice_march)
E2E: 428 collected
Dev stack required live for this session (make api + vite dev server)
```

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/q-s136-extracted-fields-ui
git log --oneline -3                           # S135 on top
docker compose ps                              # postgres + redis healthy
curl -s -o /dev/null -w "API:%{http_code} UI:" http://localhost:8102/health \
  && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/
# Expect API:200 UI:200
echo $OPENAI_API_KEY                           # for E2E that hits live extraction? or we seed DB?
```

---

## 4. FELADATOK

### LEPES 1 — Backend API surface
- Extend `EmailDetailResponse` in `src/aiflow/api/v1/emails.py` with
  `extracted_fields: dict[str, Any] | None = None`.
- GET `/api/v1/emails/{id}` handler propagates `data.get("extracted_fields")`.
- Refresh `docs/api/openapi.json` + `docs/api/openapi.yaml`.
- 2 unit tests (serialization + None default).

### LEPES 2 — TS types + ExtractedFieldsCard
- Add `ExtractedInvoice` interface to `aiflow-admin/src/components-new/ExtractedFieldsCard.tsx` mirroring the Python shape.
- Card layout (Tailwind v4, dark-mode aware):
  - Header row: invoice number + confidence badge + total cost.
  - Vendor/Buyer side-by-side (name + tax_id).
  - Header fields dl: currency, issue date, due date.
  - Line items: top-3 collapsed rows, "+N more" expand toggle.
  - Totals row with gross prominent.
- `data-testid` hooks for E2E: `extracted-fields-card`, `extracted-fields-invoice-number`, `extracted-fields-gross-total`.

### LEPES 3 — EmailDetail page wiring + locales
- `EmailDetail.tsx` extends the `EmailDetail` interface with `extracted_fields`.
- Mount `ExtractedFieldsCard` below `AttachmentSignalsCard`, render-guarded on `extracted_fields && Object.keys > 0`.
- EN/HU locales under `aiflow.emails.extractedFields.*`: title, invoice_number, vendor, buyer, currency, issue_date, due_date, line_items, net_total, vat_total, gross_total, confidence, cost, show_more.

### LEPES 4 — Playwright E2E on live stack (NO route-mock)
- `tests/e2e/v1_5_0_q_s136_extraction/test_extracted_fields_ui.py`
- Seed `workflow_runs` row with a Sprint O-shape `output_data.extracted_fields` (avoid re-running real docling+LLM in the test — just seed DB).
- Use `authenticated_page` fixture. Load `/#/emails/<run_id>`. Assert:
  - `extracted-fields-card` testid visible
  - invoice number text matches seeded value
  - gross total text matches seeded value
  - confidence badge shown
- Autouse skip if UI/API down.

### LEPES 5 — Regression + lint + tsc + commit + push + PR
- `/regression` — unit 2296+~2 green, integration unchanged.
- `/lint-check` clean (ruff + tsc).
- `scripts/export_openapi.py` refresh.
- Commit: `feat(sprint-q): S136 — ExtractedFieldsCard UI + live-stack E2E` + Co-Authored-By.
- Push → PR against `main`.

### LEPES 6 — NEXT.md for S137
- Overwrite with S137 (UC1 invoice_finder golden-path E2E on 10-fixture corpus).

---

## 5. STOP FELTETELEK

**HARD:**
1. Live UI or API down — halt + ask user to start stack.
2. tsc regression in any other admin page — halt.
3. `extracted_fields` not reachable via `/api/v1/emails/{id}` — handler bug, halt.

**SOFT:**
- Line-item expand UI could use shadcn collapse — if Untitled UI's native Disclosure isn't available, use a `<details>` / `<summary>` fallback.

---

## 6. SESSION VEGEN

```
/session-close S136
```

Utana: auto-sprint → S137 (UC1 golden-path).
