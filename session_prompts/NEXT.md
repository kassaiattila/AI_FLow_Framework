# AIFlow [Sprint X] — Session SX-2 Prompt (UC1 corpus extension + issue_date deep-fix)

> **Template version:** 1.0 (mandatory Quality target header).
> **Source template:** `session_prompts/_TEMPLATE.md`.

---

## Quality target (MANDATORY)

- **Use-case:** UC1 invoice extraction (`skills/invoice_processor`)
- **Metric:** invoice extraction accuracy on 25-fixture mixed corpus (10 synthetic + 10 anonimizalt magyar szamla + 5 OCR-noise)
- **Baseline (now):** 85.7% on 10-fixture synthetic (Sprint Q S137 measurement); `issue_date` field <100% real-corpus
- **Target (after this session):** ≥ 92% on 25-fixture mixed corpus; `issue_date` ≥ 95% on real-corpus subset
- **Measurement command:** `bash scripts/run_quality_baseline.sh --uc UC1 --output json`

---

## Goal

A Sprint X SX-1 audit megerositette: UC1 invoice extraction "85.7% / 10-fixture
synthetic" baseline-on van, "professzionalis" szinttol tavol. SX-2 zarja a
`SQ-FU-3` (corpus extension to 25) + Sprint Q nyitva maradt `issue_date`
deep-fix-et, amit Sprint U S156 csak normalizalt de nem ellenorzott
real-corpus-on.

A session **csak** akkor zarul, ha az UC1 25-fixture mixed corpus accuracy ≥ 92%
**es** az `issue_date` field accuracy ≥ 95% a real-corpus subseten. Ha
barmelyik nem, extension-session indul (SX-2b) a hianyzo dimenzioral.

A sprint NEM szallit:
- uj feature-t / scaffold-ot
- multi-tenant cleanup folytatas (SW-FU-3)
- DocRecognizer (SX-3 scope) / UC3 (SX-4 scope)

---

## Predecessor context

> **Datum:** 2026-04-26 (snapshot date — adjust if session runs later)
> **Branch:** `feature/x-sx2-uc1-corpus-issue-date` (cut from `main` after the
> SX-1 audit PR squash-merges).
> **HEAD (expected):** SX-1 close commit on top of `fed97af` (SW-5 squash).
> **Predecessor session:** SX-1 — honest alignment audit + ROADMAP rewrite + CLAUDE slim + run_quality_baseline.sh + 121_*_PLAN.md publish.

---

## Pre-conditions

- [ ] SX-1 PR merged on `main` (audit + Sprint X plan + ROADMAP + CLAUDE slim)
- [ ] `bash scripts/run_quality_baseline.sh --uc UC1 --output json` produces a number (baseline measurement)
- [ ] `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md` exists
- [ ] `docs/honest_alignment_audit.md` exists
- [ ] **Operator dependency:** anonimizalt magyar szamla PDF corpus (10 file) keszultseg ellenorizve. Ha NEM keszul el, ezt SOFT-STOP-pal jelezni kell, es SX-3 elobb mehet (DocRecognizer real-corpus is operator-feedolas, korrelalva).
- [ ] OPENAI_API_KEY env var beallitva (real-corpus integration teszthez)
- [ ] PostgreSQL Docker container fut (5433)

---

## Tasks

1. **Corpus extension to 25 fixture:**
   - 10 existing synthetic preserved at `data/fixtures/invoices_sprint_q/` (UNCHANGED)
   - 10 anonimizalt magyar szamla PDF: `data/fixtures/invoices_sprint_x/anonymized/{001..010}.pdf` + `manifest.yaml` (operator-supplied)
   - 5 OCR-noise fixture: `data/fixtures/invoices_sprint_x/ocr_noise/{001..005}.pdf` (deliberately blurry / rotated / scan-noisy synthetic generation, vagy real-PDF + `pdfimages` re-rasterize @72dpi)
   - 25-fixture aggregate manifest: `data/fixtures/invoices_sprint_x/manifest_aggregate.yaml`

2. **`scripts/measure_uc1_golden_path.py` 25-fixture mode:**
   - Add `--corpus {synthetic, anonymized, ocr_noise, all}` flag (default `all`)
   - When `all`: load all 25 fixtures from the aggregate manifest
   - Per-corpus + aggregated accuracy in JSON output
   - Update `argparse_output()` integration: JSON output includes `per_corpus`, `overall_accuracy`, `per_field_accuracy[issue_date]`

3. **`issue_date` deep-fix:**
   - Identify failure modes on real-corpus (likely: alternative date formats, OCR-noise misreads, partial matches)
   - Possible fixes (pick what works):
     (a) Alternative regex pattern (e.g. `\d{4}\.\d{2}\.\d{2}` HU-style)
     (b) OCR-confidence-aware fallback (low-conf chars retried with structure inference)
     (c) Prompt-tuning the `extract_header` step in `invoice_extraction_chain.yaml` to explicitly mention "Magyar szamla kiallitasi datum" + alternative format examples
   - Byte-stable check: 10-fixture synthetic remains 100% on `invoice_number/vendor/buyer/currency/due_date/gross_total`

4. **Test updates:**
   - `tests/integration/skills/test_uc1_golden_path.py` — parametrize `corpus_mode` (synthetic/real/ocr_noise/all)
   - 1 new integration test: `test_uc1_25fixture_real_openai.py` — full 25-fixture run on real OpenAI gpt-4o-mini, skip-by-default behind `OPENAI_API_KEY`
   - `tests/unit/skills/invoice_processor/test_issue_date_extraction.py` — 10 new unit cases for the date-format edge cases the deep-fix addresses

5. **Documentation:**
   - `docs/uc1_25fixture_report.md` — measurement report (accuracy per corpus, per field; cost; wall-clock)
   - `01_PLAN/ROADMAP.md` — Sprint X table SX-2 row → DONE + measured value
   - PR description with baseline → measured comparison

---

## Acceptance criteria

- [ ] **Quality target met:** `bash scripts/run_quality_baseline.sh --uc UC1 --output json` reports `overall_accuracy >= 0.92`
- [ ] `issue_date` field accuracy ≥ 95% on real-corpus subset (≥ 9/10 anonymized fixtures)
- [ ] 10-fixture synthetic unchanged: `invoice_number / vendor / buyer / currency / due_date / gross_total` all 100% (regression check)
- [ ] All unit tests PASS (`make test`)
- [ ] `tests/integration/skills/test_uc1_golden_path.py` PASS in `--corpus all` mode
- [ ] `tests/integration/skills/test_uc1_25fixture_real_openai.py` PASS when `OPENAI_API_KEY` set (skipped otherwise)
- [ ] `docs/uc1_25fixture_report.md` published with per-corpus / per-field breakdown
- [ ] PR opened against `main`, CI green
- [ ] OpenAPI snapshot unchanged (no router changes expected)
- [ ] `bash scripts/run_quality_baseline.sh --uc UC1 --strict` exit 0

---

## STOP conditions

**HARD:**
- 25-fixture corpus accuracy < 92% after best-effort deep-fix → halt; investigate further or escalate to extension session SX-2b
- 10-fixture synthetic regression on any field that was previously 100% → halt, revert prompt-tuning
- `invoice_extraction_chain.yaml` PromptWorkflow descriptor change breaks Sprint T S149 byte-stable test → halt, redesign

**SOFT:**
- Anonimizalt corpus operator-feedolas keses → defer SX-2 to SX-7; queue SX-3 (DocRecognizer real-corpus) elobbre
- OCR-noise fixture-generation tooling problem → reduce OCR-noise corpus to 3 fixture; document as `SX-FU-1` follow-up

---

## Output / handoff format

The session ends with:

1. PR opened against `main` titled `feat(sprint-x): SX-2 — UC1 25-fixture corpus + issue_date deep-fix (SQ-FU-3)`
2. PR body summarizes: baseline (85.7% / 10-fixture synthetic) → measured (X% / 25-fixture mixed); `issue_date` baseline → measured
3. `/session-close` invoked → generates `session_prompts/NEXT.md` for SX-3 (DocRecognizer real-corpus)
4. `01_PLAN/ROADMAP.md` Sprint X table SX-2 row → DONE
5. `docs/sprint_x_retro.md` not yet (only at SX-6 close)

---

## References

- Sprint X plan: `01_PLAN/121_SPRINT_X_QUALITY_PUSH_PLAN.md` §2 SX-2
- Forward queue: `01_PLAN/ROADMAP.md`
- Honest alignment audit: `docs/honest_alignment_audit.md`
- Quality baseline script: `scripts/run_quality_baseline.sh`
- Sprint Q UC1 baseline report: `docs/uc1_golden_path_report.md`
- Sprint Q UC1 plan: `01_PLAN/115_SPRINT_Q_INTENT_EXTRACTION_UNIFICATION.md`
- UC1 measure script: `scripts/measure_uc1_golden_path.py`
- UC1 PromptWorkflow descriptor: `prompts/workflows/invoice_extraction_chain.yaml`
- UC1 skill: `skills/invoice_processor/`
- Use-case-first replan (policy): `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
