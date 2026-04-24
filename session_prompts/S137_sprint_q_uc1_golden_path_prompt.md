# AIFlow — Session 137 Prompt (Sprint Q S137 — UC1 invoice_finder golden-path)

> **Datum:** 2026-05-09
> **Branch:** `feature/q-s137-uc1-golden-path` (cut from `main` after S136 merge).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S136 — ExtractedFieldsCard UI + live-stack Playwright E2E green. `EmailDetailResponse.extracted_fields` propagates end-to-end.
> **Terv:** `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md` §2 S137.
> **Session tipus:** Measurement — UC1 golden-path corpus + accuracy report.

---

## 1. MISSION

Curate a 10-fixture invoice corpus + run the full UC1 (invoice_finder) pipeline against it + produce `docs/uc1_golden_path_report.md` with per-field accuracy, latency p95, cost per invoice. Target: **≥ 80% overall accuracy, ≥ 90% invoice_number field accuracy**.

This is the first end-to-end UC1 validation since Phase 1d — the framework has had the pieces but never measured the full path.

---

## 2. KONTEXTUS

### Sprint Q closer view
S135 bridged UC3 intent with invoice_processor extraction (flag-gated).
S136 surfaced the result on the admin UI.
S137 now measures the standalone UC1 invoice pipeline (file / folder adapter → classifier → invoice_processor → HITL queue) on a curated corpus.

### Jelenlegi allapot
```
main @ S135+S136 merged
Fixtures baseline: data/fixtures/emails_sprint_o/ (25 UC3 .eml files, 6 contain invoice-PDFs)
invoice_processor: fully implemented skill, tested standalone (skills/invoice_processor/tests/)
UC1 pipeline: adapter orchestration landed Phase 1d; golden-path E2E never run on a curated corpus
```

### Hova tartunk (S137 output)
- `data/fixtures/invoices_sprint_q/` — 10 anonymized PDF invoices + `manifest.yaml` with ground-truth field values per fixture.
- `scripts/measure_uc1_golden_path.py` — runs the full UC1 pipeline via file adapter + invoice_processor, produces markdown report.
- `docs/uc1_golden_path_report.md` — per-fixture accuracy, per-field accuracy, p95 latency, cost per invoice, manual-review rate.
- 1 integration test (`tests/integration/skills/test_uc1_golden_path.py`) asserting the aggregate accuracy ≥ 80% on real OpenAI.

---

## 3. ELOFELTETELEK

```bash
git branch --show-current                      # feature/q-s137-uc1-golden-path
git log --oneline -3                           # S136 on top
ls skills/invoice_processor/                   # skill present
docker compose ps                              # postgres + redis healthy
echo $OPENAI_API_KEY                           # set (from .env)
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ -q --no-cov 2>&1 | tail -1   # baseline pass count
```

---

## 4. FELADATOK

### LEPES 1 — Fixture corpus
- `data/fixtures/invoices_sprint_q/generate_invoices.py` — reportlab-based generator: 10 PDF invoices, varied layouts (simple, tabular, multi-line, HU+EN).
- `data/fixtures/invoices_sprint_q/manifest.yaml`:
  ```yaml
  fixtures:
    - id: "001_hu_simple"
      pdf: "001_hu_simple.pdf"
      expected:
        invoice_number: "INV-2026-1001"
        vendor_name: "Acme Kft"
        buyer_name: "Partner Zrt"
        currency: "HUF"
        gross_total: 127000
        issue_date: "2026-03-15"
        due_date: "2026-04-15"
    # ... 9 more
  ```
- Cohort distribution: 4 HU, 4 EN, 2 mixed; 5 small (<1 MB), 3 medium, 2 large (multi-page); 7 standard layout, 3 tabular.

### LEPES 2 — Measurement script
- `scripts/measure_uc1_golden_path.py`:
  - Loads manifest
  - For each fixture: calls `parse_invoice` + `extract_invoice_data` via `skills.invoice_processor.workflows.process`
  - Compares each extracted field vs expected; records per-field hit/miss
  - Collects latency (wall-clock per fixture), cost (via token counts × $0.15/1M input, $0.60/1M output for gpt-4o-mini)
- Writes `docs/uc1_golden_path_report.md`:
  - Headline: overall accuracy, per-field accuracy table, p50/p95 latency, total cost, mean cost/invoice
  - Per-fixture detail table
  - HITL-eligible list (confidence < 0.6)

### LEPES 3 — Integration test
- `tests/integration/skills/test_uc1_golden_path.py`
- Runs the measurement script as a module, parses the report, asserts:
  - Overall accuracy ≥ 80%
  - Invoice number accuracy ≥ 90%
  - p95 latency < 20 s per invoice
  - Cost per invoice < $0.05
- Skips if `OPENAI_API_KEY` missing.

### LEPES 4 — Regression + lint + commit + push + PR
- `/regression` unit unchanged, integration +1 (the golden-path test).
- `/lint-check` clean.
- Commit: `feat(sprint-q): S137 — UC1 invoice_finder golden-path corpus + accuracy report` + Co-Authored-By.
- Push → PR.

### LEPES 5 — NEXT.md for S138
- Overwrite with S138 (Sprint Q close — retro + tag `v1.5.0`).

---

## 5. STOP FELTETELEK

**HARD:**
1. Overall accuracy < 60% → corpus needs curation, halt and escalate.
2. Cost per invoice > $0.10 → rescope the model tier (smaller/bigger), halt.
3. p95 latency > 30 s per invoice → fixture sizes too large, halt.
4. Fixture generation flaky (reportlab nondet) → halt and pin fixture outputs in git.

**SOFT:**
- 60-79% accuracy → ship the report, document gaps, file follow-ups for prompt tuning (Sprint R scope).

---

## 6. SESSION VEGEN

```
/session-close S137
```

Utana: auto-sprint → S138 (Sprint Q close + tag v1.5.0).
