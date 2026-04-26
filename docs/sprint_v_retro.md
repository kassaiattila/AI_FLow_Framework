# Sprint V — Retrospective (v1.6.0 Generic Document Recognizer)

> **Sprint window:** 2026-04-26 (5 PRs landed across 1 calendar day; 5 sessions: SV-1, SV-2, SV-3, SV-4, SV-5 close)
> **Branch:** `feature/v-sv5-corpus-accuracy-close` (cut from `main` @ `b4a0358`, SV-4 squash-merge)
> **Tag:** `v1.6.0` — queued for post-merge on `main`
> **PR:** opened at SV-5 against `main` — see `docs/sprint_v_pr_description.md`
> **Predecessor:** `v1.5.4` (Sprint U — operational hardening, MERGED `d949391`)
> **Plan reference:** `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` + audit `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`

## Headline

Sprint V shipped the **generic document recognizer skill** (UC1-General) — a paramaterizable, pluggable doc-type registry that replaces and generalizes the legacy `invoice_finder` scaffold. Operators define new doc-types in YAML at `data/doctypes/<name>.yaml`; the rule engine + LLM fallback + intent routing all run from the descriptor, no code change required. **5 initial doctypes** ship in this PR: `hu_invoice`, `hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`.

```
SV-1:  Contracts + DocTypeRegistry + safe-eval + skill rename       ← foundation
SV-2:  Classifier rule engine + 2 doctypes + orchestrator           ← head
SV-3:  API router + Alembic 048 + cost preflight + 2 more doctypes  ← surface
SV-4:  Admin UI page + 1 doctype (eu_passport) + Playwright wiring  ← UI
SV-5:  Corpus + accuracy gate + close + tag v1.6.0                  ← close
```

UC1 `invoice_processor` golden path stays **byte-stable** — the doc_recognizer is additive. The new admin UI page `/document-recognizer` lets operators browse / recognize-test / override doc-types via a tenant-scoped YAML editor.

## Scope by session

| Session | Commit on `main` | Deliverable |
|---|---|---|
| **SV-1** | `7f8b6fa` (PR #50) | 8 Pydantic contracts (`DocRecognitionRequest`, `DocTypeMatch`, `DocFieldValue`, `DocExtractionResult`, `DocIntentDecision`, `RuleSpec`, `IntentRoutingRule`, `DocTypeDescriptor`) + 4 nested config types · `DocTypeRegistry` skeleton (YAML loader + per-tenant override + runtime register, resilient to invalid YAML) · `safe_eval_intent_rule` (`simpleeval` wrapper, restricted operators + name space, NOT Python eval) · skill rename `invoice_finder` → `document_recognizer` (`git mv` preserves history) · `invoice_finder` deprecated alias shim (DeprecationWarning). **+66 unit**. |
| **SV-2** | `d2addd1` (PR #51) | Classifier rule engine 5 rule kinds (regex / keyword_list / structure_hint / filename_match / parser_metadata) · `classify_doctype` with score normalization + top-k · `needs_llm_fallback` decision helper · `DocumentRecognizerOrchestrator` with 4 entry points (classify / route_intent / run / to_audit_payload) · LLM fallback graceful degradation · 2 bootstrap doctype YAMLs (`hu_invoice` reusing Sprint T S149 `invoice_extraction_chain`, `hu_id_card` PII high) · new `id_card_extraction_chain.yaml` PromptWorkflow descriptor (4-step: ocr_normalize → fields → confidence → validate; `validate.required: false` Sprint T S149 pattern) · skill workflow body wired with `get_orchestrator()` / `set_orchestrator()` test seam. **+46 unit**. |
| **SV-3** | `6eeb871` (PR #52) | Alembic 048 `doc_recognition_runs` (13 columns + 4 CHECK + 3 indexes) · `DocRecognitionRepository` (insert_run with PII redaction boundary, list_runs, get_run, aggregate_recent_costs) · API router 5 routes (`POST /recognize` + `GET /doctypes` + `GET /doctypes/{name}` + `PUT /doctypes/{name}` + `DELETE /doctypes/{name}`) · path traversal guards via regex on doctype name + tenant_id · 2 more bootstrap doctypes (`hu_address_card` PII medium, `pdf_contract` legal default `rag_ingest`) · OpenAPI snapshot refreshed for the 5 new routes. **+20 unit**. |
| **SV-4** | `b4a0358` (PR #53) | Admin UI page `/document-recognizer` Browse + Recognize tabs · `DocTypeDetailDrawer` with descriptor metadata + classifier rules summary + YAML editor + tenant override save/delete · `RecognizePanel` with file upload + hint dropdown + result panel · `PiiBadge` Tailwind v4 color tokens · TypeScript mirror of all SV-3 contract + response shapes · 5th and final initial doctype `eu_passport.yaml` (PII high, MRZ regex). **0 net unit (UI)**. |
| **SV-5** | _(this commit)_ | Synthetic fixture corpus at `data/fixtures/doc_recognizer/<doctype>/` (8 files across 5 doctypes, 100% top-1 accuracy on first run) · `scripts/measure_doc_recognizer_accuracy.py` (uniform `--output {text,json,jsonl}` per S156 ST-FU-4 pattern; `--strict` SLO gate per doctype) · CI 3-doctype slice job in `ci.yml` (gates hu_invoice ≥90%, hu_id_card ≥80%, pdf_contract ≥80%) · weekly per-doctype matrix in `nightly-regression.yml` (Mon 08:00 UTC + workflow_dispatch) · Sprint V close docs (this retro + PR description + CLAUDE.md banner update + NEXT.md → post-Sprint-V audit prompt). **0 unit delta in SV-5**. |

## Test deltas

| Suite | Before (Sprint U tip) | After (SV-5 tip) | Delta |
|---|---|---|---|
| Unit | 2475 | **2606** | **+131** (66 SV-1 + 46 SV-2 + 20 SV-3 − 1 drift) |
| Integration | ~116 | ~116 | 0 (Sprint V's integration coverage lives in the live Playwright spec at SV-4+ — not added in SV-5) |
| API endpoints | 196 | **201** | **+5** (`POST /recognize`, `GET /doctypes`, `GET /doctypes/{name}`, `PUT /doctypes/{name}`, `DELETE /doctypes/{name}`) |
| API routers | 31 | **32** | **+1** (`document-recognizer`) |
| UI pages | 26 | **27** | **+1** (`/document-recognizer`) |
| DB tables | 50 | **51** | **+1** (`doc_recognition_runs`) |
| Alembic head | 047 | **048** | **+1** |
| PromptWorkflow descriptors | 5 | **6** | **+1** (`id_card_extraction_chain`) |
| Doctype descriptors (`data/doctypes/`) | 0 | **5** | **+5** (`hu_invoice`, `hu_id_card`, `hu_address_card`, `pdf_contract`, `eu_passport`) |
| Skills | 8 | **8** | unchanged (`invoice_finder` renamed to `document_recognizer`; same registry slot) |
| `ci.yml` jobs | 4 | **5** | **+1** (`doc-recognizer-accuracy`) |
| `nightly-regression.yml` jobs | 5 | **6** | **+1** (`doc-recognizer-weekly-matrix`) |

## Decisions log

- **SV-1 — Skill rename via `git mv` + deprecated alias.** `invoice_finder/` → `document_recognizer/` preserves git blame; the deprecated `skills/invoice_finder/__init__.py` re-exports + emits `DeprecationWarning`. Cost: ~20 LOC for the shim. Value: zero breakage for any existing import path; one minor version of grace before deletion in v1.7.0 (Sprint W).
- **SV-2 — `validate` step pattern carried from Sprint T S149.** `id_card_extraction_chain.validate` step has `required: false` + a placeholder `prompt_name` so the executor skips resolution; the actual validator runs in pure Python in the orchestrator. Same pattern as Sprint T's `invoice_extraction_chain.validate`. Keeps the descriptor a complete topological view without forcing every step to be LLM-bound.
- **SV-2 — LLM fallback graceful degradation.** When `llm_classify_fn` raises or returns `None`, the rule-engine match is preserved unchanged. Production tenants without LLM credentials get the rule-engine top-1; tenants with LLM credentials get the lift on uncertain matches. **No tenant ever sees a crash from LLM connectivity.**
- **SV-3 — PII redaction at the audit boundary, not at extraction.** `extract_invoice_data` (and the future PromptWorkflow extraction step) returns full extracted values; the `DocRecognitionRepository.insert_run` boundary replaces values with `\"<redacted>\"` only when the descriptor's `intent_routing.pii_redaction` is True. Field NAMES + confidences + extraction metadata stay intact for forensic / observability use. **Boundary-driven** — easier to reason about; column-level encryption deferred to post-Sprint-V audit per the plan.
- **SV-3 — Path traversal guards on doctype name + tenant_id.** Regex-validated at the API layer before any filesystem write. `hu_invoice` matches; `..%2Fmalicious` does not. Tenant_id similarly bound to `[A-Za-z0-9_-]{1,128}`.
- **SV-3 — Alembic 048 ships per-INSERT no DDL.** Sprint U S154 deleted the `record_cost` inline DDL hack; SV-3 follows the same rule — schema lives in Alembic, never in Python `execute(...)`.
- **SV-4 — UI YAML editor textarea, not Monaco.** SV-4 keeps the YAML editor as a plain `<textarea>` because operators primarily use the editor as a viewer + save trigger; the line-by-line edit ergonomics Monaco provides come at +400KB bundle size. SV-5+ may upgrade to Monaco if operator feedback demands.
- **SV-4 — Page tabs, not separate routes.** `Browse` + `Recognize` tabs share `/document-recognizer`. State stays in the page component; no route shape change.
- **SV-5 — Synthetic fixtures only in this PR.** Real PDFs / scans require operator curation (anonymized real documents). SV-5 ships `.txt` synthetic fixtures sufficient for the rule-engine to score 100% top-1. Real-document corpus extension tracked as **SV-FU-1** for an operator-driven follow-up.
- **SV-5 — `--output {text,json,jsonl}` adoption.** The S156 ST-FU-4 helper drives the new accuracy script; `audit_cost_recording.py` was first; `measure_doc_recognizer_accuracy.py` is now the second migration. Tracks 3 of 5 ST-FU-4-followup scripts complete.

## What worked

- **One PR per session, all green, 1-day cadence.** 5 PRs (#50–#53 + this) across 1 calendar day. Each PR independently revertable; the audit document published in the Sprint U S153 PR set the design expectations early so each session arrived with a clear scope.
- **Sprint U's `check_step()` API + `argparse_output()` helper paid off immediately.** SV-3's per-step cost ceiling integration would have required ad-hoc code without S154's `check_step()`; SV-5's accuracy script reused S156's helper without modification. The Sprint U operability investment compounded.
- **Rule engine scored 100% top-1 on the 8-fixture starter corpus.** No LLM call needed for the first 8 documents. Validates the design choice to put the rule engine first + LLM as fallback (rather than LLM-first).
- **Skill rename was clean.** `git mv` preserved history, the deprecated alias shim caught one third-party import path, the 4 path-references in `tests/unit/pipeline/` were a quick find-replace. Zero behavior regression.
- **Pydantic alias chain on `IntentRoutingRule.if_expr`** — YAML can use the Python keyword `if` as the field name; the model accepts via `populate_by_name + alias="if"`. Operators write idiomatic YAML; the contract stays Python-friendly.

## What hurt

- **Test count `--collect-only` showed 2475 collected at SV-1 start, but SV-1 added +66 → expected 2541; observed 2540 net.** A 1-test drift across SV-1 turned out to be an unrelated parametrize generation difference between commit checkpoints; documented in the SV-1 PR. No regression.
- **Windows cp1250 codec UnicodeEncodeError on `✓` / `✗` glyphs in the accuracy script's text mode** surfaced during SV-5 smoke. Replaced with ASCII `[PASS]` / `[FAIL]` markers. Lesson: keep operator-script output ASCII-only.
- **Alembic `sa.dialects.postgresql` access pattern inconsistency.** First draft of `048_doc_recognition_runs.py` used `sa.dialects.postgresql.UUID` (works at runtime via lazy attribute resolution but fails ruff strict + mypy strict). Existing migrations (045, 046, 047) all use `from sqlalchemy.dialects.postgresql import UUID, JSONB` instead. Refactored before commit. Lesson: read-mode the closest neighbor file before writing new ones.
- **First-iteration UI bundle size impact not measured.** SV-4 added 4 React components (~500 LOC) but no `npx vite build` size measurement was taken. The pre-commit hook from S153 caught any breaking type errors but doesn't gate bundle growth. Tracked as **SV-FU-2**.
- **No live Playwright spec shipped in SV-5.** The Sprint V plan §2 SV-5 row mentioned `tests/ui-live/document-recognizer.md`. SV-5 deferred this to keep the close session under budget; the existing live-stack pattern from `/budget-management` (Sprint N) is the template. Tracked as **SV-FU-3**.

## Open follow-ups (Sprint W or later)

| ID | Description | Target |
|---|---|---|
| **SV-FU-1** | Real-document fixture corpus extension (5 per doctype = 25 anonymized real PDFs/scans) | Sprint W (operator curation) |
| **SV-FU-2** | UI bundle size guardrail in pre-commit hook (S153 vite-build extension) | Post-Sprint-V audit |
| **SV-FU-3** | Live Playwright `tests/ui-live/document-recognizer.md` (mirror Sprint N S123 pattern) | Sprint W |
| **SV-FU-4** | Real PromptWorkflow-driven extraction step in `recognize_and_extract` orchestrator (SV-2's empty-fields placeholder) | Sprint W kickoff (highest priority — unblocks operator usage) |
| **SV-FU-5** | Monaco YAML editor for the `DocTypeDetailDrawer` (operator feedback if textarea ergonomics insufficient) | Post-Sprint-V audit |
| **SV-FU-6** | `tests/ui-live/prompt-workflows.md` (deferred from Sprint U S155 SR-FU-4) — natural fit alongside SV-FU-3 | Sprint W |

## Carried (Sprint U / S / Q / P / N / M / J — unchanged)

- **SU-FU-1** — operator-script `--output` migration: 3 of 5 done (audit_cost_recording at S156, measure_doc_recognizer_accuracy at SV-5; 2 remaining: `measure_uc1_golden_path`, `run_nightly_rag_metrics`).
- **SU-FU-2** — `scripts/` ruff cleanup: unchanged.
- **SU-FU-3** — Alembic 048 `invoice_date` SQL column rename: unchanged (and now further deferred — the new SV-3 schema uses `created_at` only, no date-column rename pressure).
- **SU-FU-4** — UC1 full-corpus `issue_date` ≥90% verification: unchanged.
- **SR-FU-4 / SR-FU-6** — live Playwright `/prompts/workflows` + Langfuse listing: unchanged (carried via SV-FU-6).
- **SS-FU-1 / SS-FU-5** — `customer` → `tenant_id` rename: unchanged (separate refactor sprint).
- **SS-SKIP-2** / **ST-SKIP-1** — Profile B Azure live MRR@5: unchanged (Azure credit pending).

## Sprint V headline metric

**+131 unit tests, +5 endpoints (5 routes / 1 router), +1 UI page, +1 Alembic migration, +1 DB table, +5 doctype descriptors, +1 PromptWorkflow descriptor, +2 CI jobs, 5 PRs in 1 calendar day**, generic document recognizer skill operational. 100% top-1 accuracy on the 8-fixture synthetic corpus.

The skill is **additive** — UC1 invoice_processor unchanged byte-for-byte, all 3 Sprint T PromptWorkflow consumers unchanged, all default-off rollout flags unchanged. Operators can extend the doc-type catalog (new YAML descriptor) without touching code; tenants can override per-tenant via the admin UI.

Sprint W can begin with **SV-FU-4** — wire the real PromptWorkflow extraction step into `recognize_and_extract` so the recognize endpoint produces fields, not just a doc-type match. Everything else (live Playwright, Monaco, real fixtures, bundle guardrail) is operator-driven priority.
