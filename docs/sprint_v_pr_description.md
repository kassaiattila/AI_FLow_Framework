# Sprint V — Generic Document Recognizer (v1.6.0)

> **Already-merged sub-PRs:** #50 (SV-1 foundation) · #51 (SV-2 classifier) · #52 (SV-3 API + Alembic 048) · #53 (SV-4 admin UI)
> **This PR:** SV-5 close — corpus + accuracy gate + tag `v1.6.0` queued
> **Cumulative diff vs Sprint U tip (`d949391`):** +5500 / −0 LOC plus the Alembic 048 schema delta
> **Tag (post-merge):** `v1.6.0`

## Summary

Sprint V ships the **generic document recognizer skill** (UC1-General) — a parametrizable, pluggable doc-type registry that replaces and generalizes the legacy `invoice_finder` scaffold. **5 initial doctypes** (`hu_invoice`, `hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`) ship in this PR with **100% top-1 accuracy on the 8-fixture synthetic starter corpus**.

UC1 `invoice_processor` golden path stays **byte-stable** — the doc_recognizer is additive. The new admin UI page `/document-recognizer` lets operators browse / recognize-test / override doc-types via a tenant-scoped YAML editor.

## What ships in SV-5 (this PR)

- `scripts/measure_doc_recognizer_accuracy.py` — operator + CI accuracy tool. Walks `data/fixtures/doc_recognizer/<doctype>/` and runs each fixture through the rule-engine classifier (no LLM). `--output {text,json,jsonl}` (Sprint U S156 `argparse_output()` helper). `--strict` enforces per-doctype SLO (hu_invoice ≥90%, hu_id_card ≥80%, pdf_contract ≥80%, hu_address_card ≥70%, eu_passport ≥70%).
- `data/fixtures/doc_recognizer/<doctype>/` — 8 synthetic `.txt` starter fixtures (2 invoice, 2 id_card, 1 address_card, 1 passport, 2 contract). Real-document corpus extension tracked as **SV-FU-1** for operator curation.
- `.github/workflows/ci.yml` — new `doc-recognizer-accuracy` job runs on every PR with `--strict` (hermetic, no DB, no LLM).
- `.github/workflows/nightly-regression.yml` — new `doc-recognizer-weekly-matrix` job (Mon 08:00 UTC + workflow_dispatch). Runs full per-doctype matrix + uploads json + jsonl artifacts (90-day retention).
- `docs/sprint_v_retro.md` — 5-section retrospective (decisions log SV-1..SV-5, what worked, what hurt, 6 follow-ups SV-FU-1..SV-FU-6).
- `docs/sprint_v_pr_description.md` — this document.
- `CLAUDE.md` — Sprint V DONE banner + key numbers update.
- `session_prompts/NEXT.md` — Post-Sprint-V audit prompt.

## Sub-PR digest (already merged)

### #50 SV-1 — Foundation (contracts + safe-eval + skill rename)

8 Pydantic contracts + 4 nested config types · DocTypeRegistry skeleton with per-tenant override + runtime register · `safe_eval_intent_rule` (simpleeval-based, restricted) · skill rename `invoice_finder` → `document_recognizer` (`git mv` preserves history) · deprecated alias shim. **+66 unit tests.**

### #51 SV-2 — Classifier rule engine + 2 doctypes + orchestrator

5 rule kinds (regex / keyword_list / structure_hint / filename_match / parser_metadata) · `classify_doctype` with score normalization + top-k · `DocumentRecognizerOrchestrator` (4 entry points + LLM fallback graceful degradation + audit payload) · 2 bootstrap doctypes (`hu_invoice` reuses Sprint T `invoice_extraction_chain`, `hu_id_card` PII-aware) · `id_card_extraction_chain.yaml` (4-step DAG). **+46 unit tests.**

### #52 SV-3 — API router + Alembic 048 + 2 more doctypes + repository

5 routes mounted at `/api/v1/document-recognizer` · Alembic 048 `doc_recognition_runs` (13 col + 4 CHECK + 3 idx) · `DocRecognitionRepository` with PII redaction boundary · 2 more doctypes (`hu_address_card`, `pdf_contract`) · OpenAPI snapshot refresh. **+20 unit tests.**

### #53 SV-4 — Admin UI page + 1 doctype + Playwright wiring

`/document-recognizer` admin page (Browse + Recognize tabs) · DocTypeDetailDrawer with YAML editor + tenant override save/delete · RecognizePanel multipart upload · PiiBadge Tailwind v4 · 5th doctype `eu_passport.yaml` (PII high). **0 net unit (UI).**

## Cumulative Sprint V metrics

| Metric | Sprint U tip | Sprint V tip | Delta |
|---|---|---|---|
| Unit tests | 2475 | **2606** | **+131** |
| Integration tests | ~116 | ~116 | 0 |
| API endpoints | 196 | **201** | **+5** |
| API routers | 31 | **32** | **+1** (`document-recognizer`) |
| UI pages | 26 | **27** | **+1** (`/document-recognizer`) |
| DB tables | 50 | **51** | **+1** (`doc_recognition_runs`) |
| Alembic head | 047 | **048** | **+1** |
| PromptWorkflow descriptors | 5 | **6** | **+1** (`id_card_extraction_chain`) |
| Doctype descriptors | 0 | **5** | **+5** |
| `ci.yml` jobs | 4 | **5** | **+1** (`doc-recognizer-accuracy`) |
| `nightly-regression.yml` jobs | 5 | **6** | **+1** (`doc-recognizer-weekly-matrix`) |
| Synthetic fixture corpus | 0 | **8 files / 5 doctypes** | **+8** |

## Validation

- ✅ All 4 sub-PRs (#50–#53) merged on `main` with green CI
- ✅ Pre-commit hook (lint + 2606 unit, ~1.5min) green for every Sprint V commit
- ✅ `scripts/measure_doc_recognizer_accuracy.py` reports **100% top-1** on the 8-fixture starter corpus (all 5 doctypes PASS their SLO gates)
- ✅ OpenAPI drift gate (`scripts/check_openapi_drift.py`) `[ok]` post-SV-3 snapshot refresh
- ✅ Alembic 048 round-trip on Docker dev DB (047 → 048 clean upgrade applied)
- ✅ UI tsc check clean (`npx tsc --noEmit` exit 0)
- ✅ UC1 invoice_processor golden path **byte-stable** (no behavior change)
- ✅ All 3 Sprint T PromptWorkflow consumers unchanged
- ✅ Default-off rollout preserved on every existing flag

## Test plan

- [ ] CI runs all jobs green: lint+unit, admin-build, openapi-drift, integration-1024-dim, **doc-recognizer-accuracy** (new SV-5)
- [ ] Manual `gh workflow run nightly-regression.yml` to verify the new `doc-recognizer-weekly-matrix` job triggers
- [ ] Local: navigate to `/document-recognizer` after `bash scripts/start_stack.sh --full`; verify 5 doctypes listed, drawer opens, recognize panel uploads work
- [ ] Tag `v1.6.0` queued for post-merge

## Carry-forward to Sprint W

The post-Sprint-V audit per the Sprint V plan §9 is the next operator decision. Highest-priority follow-up: **SV-FU-4** — wire the real PromptWorkflow extraction step into `recognize_and_extract` so the recognize endpoint produces fields, not just a doc-type match.

Other Sprint W candidates documented in `docs/sprint_v_retro.md`:
- SV-FU-1 — Real-document fixture corpus extension (anonymized real PDFs/scans)
- SV-FU-2 — UI bundle size guardrail in pre-commit hook
- SV-FU-3 — Live Playwright `tests/ui-live/document-recognizer.md`
- SV-FU-5 — Monaco YAML editor (if operator feedback demands)
- SV-FU-6 — Live Playwright `tests/ui-live/prompt-workflows.md` (carried from Sprint U)

Plus Sprint U/S/Q/P/N/M/J unchanged carry-forwards (customer→tenant_id rename, Vault prod hardening, Profile B Azure live, coverage uplift 80%, observability).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
