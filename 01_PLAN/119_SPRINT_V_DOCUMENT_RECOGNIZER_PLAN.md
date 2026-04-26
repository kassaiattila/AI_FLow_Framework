# AIFlow v1.6.0 Sprint V — Generic Document Recognizer (UC1-General)

> **Status:** PUBLISHED 2026-04-26 by Sprint U S157 close session.
> **Branch convention:** `feature/v-s{N}-*` (each session its own branch → PR → squash-merge).
> **Parent docs:**
> - `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` — audit + design depth (SOURCE)
> - `01_PLAN/110_USE_CASE_FIRST_REPLAN.md` — UC trajectory anchor
> **Predecessor:** v1.5.4 Sprint U (operational hardening, MERGED)
> **Target tag (post-merge):** `v1.6.0`

---

## 1. Goal

Sprint V ships a **paraméterezhető, általános dokumentum-felismerő + adatkinyerő skill** that helyettesíti és általánosítja a jelenlegi `invoice_finder` scaffold-ot. Pluggable doc-type registry: az operator YAML-ban definiál új doc-típust + extraction field-eket, **kód-változás nélkül**. UC1 invoice_processor változatlan marad — a doc_recognizer additive új skill, a régi UC1 path nem romlik.

### Capability cohort delta

| Cohort | Sprint U close | Sprint V close (target) |
|---|---|---|
| Skills | 8 (`aszf_rag_chat`, `cubix_course_capture`, `email_intent_processor`, `invoice_finder`, `invoice_processor`, `process_documentation`, `qbpp_test_automation`, `spec_writer`) | **8** — `invoice_finder` renamed to `document_recognizer` (preserves git history; same skill registry slot) |
| Doc-types supported | 1 implicit (HU invoice via `invoice_processor`) | **5 explicit** (`hu_invoice`, `hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`) + operator-extensible YAML |
| Document intents | 0 explicit | **5** (`process`, `route_to_human`, `rag_ingest`, `respond`, `reject`) |
| API endpoints | 196 | **199** (+3: `POST /document-recognizer/recognize`, `GET /document-recognizer/doctypes`, `GET /document-recognizer/doctypes/{name}`, `PUT /document-recognizer/doctypes/{name}` per-tenant override, `DELETE` override — actually +5 routes for the new router) |
| API routers | 31 | **32** (+1 `document_recognizer`) |
| UI pages | 26 | **27** (+1 `/document-recognizer` Browse + Recognize + DocTypeEditor) |
| DB tables | 50 | **51** (+1 `doc_recognition_runs` audit + observability) |
| Alembic head | 047 | **048** (`doc_recognition_runs`) |
| PromptWorkflow descriptors | 5 (`uc3_intent_and_extract`, `email_intent_chain`, `invoice_extraction_chain`, `aszf_rag_chain`, `aszf_rag_chain_expert`, `aszf_rag_chain_mentor`) | **6+** (+1 `id_card_extraction_chain` minimum; per-doctype descriptors as needed) |
| Provider Registry slots | 5 ABC slots (parser, classifier, extractor, embedder, chunker) | **5** unchanged (DocTypeProvider deferred to post-Sprint-V if needed) |

---

## 2. Sessions

### SV-1 — Contracts + DocTypeDescriptor + safe-eval + skill rename
**Scope.** The foundation layer. Pure-Python, zero LLM, zero DB. Pickup blockers BEFORE any classifier or extractor work.

1. **Contracts** — `src/aiflow/contracts/doc_recognition.py` (~150 LOC, 8 Pydantic class):
   - `DocRecognitionRequest` — file path + bytes + optional `doc_type` hint + tenant_id
   - `DocTypeMatch` — doc_type + confidence + alternatives list (top-3)
   - `DocFieldValue` — value + confidence + source_text_hint
   - `DocExtractionResult` — doc_type + extracted_fields dict + per-field confidence + validation_warnings
   - `DocIntentDecision` — intent enum + reason + next_action
   - `DocTypeDescriptor` — name + display_name + language + category + parser_preferences + type_classifier rules + extraction config + intent_routing
   - `RuleSpec` — kind enum + pattern/keywords/threshold + weight (5 kinds: regex, keyword_list, structure_hint, filename_match, parser_metadata)
   - `IntentRoutingRule` — if_expr + intent + reason
2. **DocTypeRegistry skeleton** — `src/aiflow/services/document_recognizer/registry.py`:
   - YAML loader: `data/doctypes/<name>.yaml` + per-tenant override `data/doctypes/_tenant/<tenant_id>/<name>.yaml`
   - `register_doctype(descriptor)` / `list_doctypes(tenant_id?)` / `get_doctype(name, tenant_id?)`
   - Validation: Pydantic `DocTypeDescriptor` parse on load; invalid YAML → log warning + skip + audit log entry
3. **Safe-expression-eval** — `src/aiflow/services/document_recognizer/safe_eval.py` (~80 LOC):
   - Wraps `simpleeval` (battle-tested, pinned version)
   - Restricted operator list: `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, `in`
   - Restricted name space: `extracted.<field>`, `field_confidence_min`, `field_confidence_max`, `doc_type_confidence`, `pii_detected`
   - **NOT Python `eval()`** — explicit name-resolution boundary
4. **Skill rename** — `skills/invoice_finder/` → `skills/document_recognizer/`:
   - `git mv skills/invoice_finder skills/document_recognizer` (preserves history)
   - Update `skill.yaml`: `name: document_recognizer` + `display_name: "Document Recognizer"`
   - Stub `__init__.py` + `__main__.py` for the new entry point
   - Skeleton `workflows/recognize_and_extract.py`, `prompts/doctype_classifier.yaml` (placeholder DAG, no LLM call yet)
5. **`invoice_finder` deprecated alias** — keep `skills/invoice_finder/__init__.py` as a re-export shim that imports from `document_recognizer` + emits a `DeprecationWarning` on first import. Keeps old imports compiling for one minor version.

**Gate.** ruff clean + 2475+ unit collected (no test count change at SV-1; the new contracts are exercised by SV-2 tests).

**Expected diff.** ~600 LOC new code + skill rename. **+18 unit tests** (Pydantic round-trip × 8 contracts + safe-eval grammar × 5 + DAG load × 5).

**Risk.** R1 (low) — skill rename git history preservation.

### SV-2 — Type classifier (rule-engine + LLM fallback) + 2 doctype kickoff
**Scope.** The recognizer head. Wires up the 3-stage pipeline (parse → rule-scorer → LLM fallback).

1. **Rule engine** — `src/aiflow/services/document_recognizer/classifier.py`:
   - 5 rule kinds: `regex`, `keyword_list`, `structure_hint`, `filename_match`, `parser_metadata`
   - Score normalization: weights sum to 1.0 per descriptor; aggregate = `sum(matched_weights)`
   - Top-k aggregation: returns `DocTypeMatch` with primary + alternatives list
2. **LLM fallback gate** — when top-1 rule-score < `descriptor.type_classifier.llm_threshold_below` (default 0.7):
   - Build LLM prompt with top-k descriptors' metadata + first 1500 chars of parsed text
   - LLM returns enum + confidence; if confidence > rule-score, replace
   - Cost-tracked via `CostPreflightGuardrail` (S154 `check_step()` API)
3. **2 doctype kickoff** — `data/doctypes/`:
   - `hu_invoice.yaml` — full descriptor (rules: tax_number regex 0.35, ÁFA regex 0.25, keyword_list 0.25, table_count structure 0.10, filename 0.05; extraction reuses Sprint T `invoice_extraction_chain`)
   - `hu_id_card.yaml` — full descriptor (rules: MAGYARORSZÁG regex 0.20, "Személyazonosító igazolvány" 0.40, ID-number pattern 0.30, page_count==1 0.10; new `id_card_extraction_chain.yaml`)
4. **`id_card_extraction_chain.yaml`** — new PromptWorkflow descriptor (4-step DAG: ocr_normalize → fields → confidence → validate):
   - `ocr_normalize` — strip OCR noise from MRZ + identity field area
   - `fields` — extract full_name, birth_date, id_number, issue_date, validity_date, nationality, mother_name
   - `confidence` — per-field confidence scoring
   - `validate` — `regex:^\\d{6}[A-Z]{2}$` for id_number; `iso_date` + `before_today` for birth_date
5. **Orchestrator** — `src/aiflow/services/document_recognizer/orchestrator.py`:
   - `recognize_and_extract(file_bytes, tenant_id, doc_type_hint=None) -> DocExtractionResult`
   - Pipeline: `document_extractor` parser routing → `classifier` → if matched → run extraction PromptWorkflow → assemble `DocExtractionResult` + `DocIntentDecision`
6. **Per-tenant override loader** — runtime tenant-aware: if `data/doctypes/_tenant/<tenant_id>/<name>.yaml` exists, override the bootstrap descriptor; otherwise use bootstrap

**Gate.**
- Real-LLM integration test on 1 fixture per doctype (hu_invoice + hu_id_card): doc_type top-1 match + full extraction round-trip
- UC1 `invoice_processor` golden-path slice still ≥ 75% / `invoice_number` ≥ 90% (regression check — `hu_invoice` descriptor reuses the existing `invoice_extraction_chain` so no behavior change)
- ruff clean + 2495+ unit (+20)

**Expected diff.** ~700 LOC new + 2 YAML descriptors + 1 PromptWorkflow YAML. **+20 unit + 4 integration** (real PG + real docling + real OpenAI on 1 fixture per doctype, real BGE-M3 not needed at this stage).

**Risk.** R2 (medium) — HU regex brittleness on real ID-card scans.

### SV-3 — API endpoint + Alembic 048 + cost preflight integration + 2 további doctype
**Scope.** The customer-facing surface. After SV-3 the recognizer is callable via JWT-authed REST.

1. **API router** — `src/aiflow/api/v1/document_recognizer.py`:
   - `POST /api/v1/document-recognizer/recognize` — multipart file upload + optional `doc_type` query param + tenant_id from JWT
   - `GET /api/v1/document-recognizer/doctypes` — list registered doc-types (tenant-aware override merged)
   - `GET /api/v1/document-recognizer/doctypes/{name}` — single doc-type detail (descriptor + sample fixtures count)
   - `PUT /api/v1/document-recognizer/doctypes/{name}` — operator-side per-tenant override creation (YAML body + tenant_id from JWT; persists to `data/doctypes/_tenant/<tenant_id>/<name>.yaml`)
   - `DELETE /api/v1/document-recognizer/doctypes/{name}` — remove the per-tenant override (descriptor falls back to bootstrap)
2. **Alembic 048** — `alembic/versions/048_doc_recognition_runs.py`:
   - Table `doc_recognition_runs`:
     - `id` UUID PK
     - `tenant_id` TEXT NOT NULL
     - `doc_type` TEXT NOT NULL
     - `confidence` REAL NOT NULL
     - `extracted_fields` JSONB NOT NULL DEFAULT '{}'
     - `intent` TEXT NOT NULL
     - `cost_usd` REAL NOT NULL DEFAULT 0
     - `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
   - Indexes: `(tenant_id, created_at DESC)`, `(doc_type, created_at DESC)`, `(intent, tenant_id)` for routing-board queries
3. **Cost preflight integration** — `recognize_and_extract` calls `CostPreflightGuardrail.check_step(step_name="doc_recognizer.classify_and_extract", ...)` before the LLM fallback + per-step `metadata.cost_ceiling_usd` from the descriptor's classifier + extraction blocks
4. **2 további doctype** — `data/doctypes/`:
   - `hu_address_card.yaml` — magyar lakcímkártya (név, lakcím, kiállítás dátuma)
   - `pdf_contract.yaml` — szerződés (felek, tárgy, hatály, díjazás)
   - Both use simpler `extraction.workflow` descriptors (3-step: ocr_normalize → fields → validate)
5. **Audit boundary PII redactor** — `src/aiflow/services/document_recognizer/pii_redactor.py`:
   - For descriptors with `pii_level: high` (e.g. `hu_id_card`)
   - Strips PII fields from `audit_log` write-time payload (replaces values with `<redacted>`)
   - Hash of original written for forensic recovery
   - `extracted_fields` JSONB DB column unaffected (operator opt-in `AIFLOW_PII_ENCRYPTION__ENABLED` for column-level encryption deferred to post-Sprint-V)

**Gate.**
- Path traversal guard test (tenant_id mismatch on `PUT /doctypes/{name}`)
- Alembic 048 round-trip test (upgrade → downgrade → upgrade clean)
- Cost preflight refusal on a deliberately tiny `cost_ceiling_usd` (`check_step` returns `allowed=False`)
- OpenAPI drift CI gate (S153) green — snapshot refreshed for the 5 new routes

**Expected diff.** ~450 LOC + 1 Alembic + 2 YAML descriptors. **+14 unit + 3 integration** (real PG + real OpenAI per-doctype + 1 alembic round-trip).

**Risk.** R3 (medium) — OCR quality on image-heavy doctypes (address card, passport).

### SV-4 — Admin UI page + 1 további doctype + Playwright
**Scope.** The operator-facing surface. After SV-4 operators can browse / test / override doc-types via the admin dashboard.

1. **Admin UI page** — `aiflow-admin/src/pages-new/DocumentRecognizer/`:
   - `index.tsx` Browse view: doc-type list table (tenant filter dropdown + per-doctype overlay for tenant-specific overrides)
   - `Detail.tsx` Side drawer: doc-type detail (descriptor + bootstrap-vs-tenant indicator + recent runs)
   - `Recognize.tsx` Test panel: drag-drop file upload + result panel (DocTypeMatch + DocExtractionResult + DocIntentDecision)
   - `DocTypeEditor.tsx` YAML editor: Monaco read-only validate + save (tenant-scoped); operator clicks "Override for tenant" + edits YAML + saves → calls `PUT /doctypes/{name}`
2. **1 további doctype** — `data/doctypes/eu_passport.yaml` (5. és utolsó kezdő doctype: név, útlevélszám, születési dátum, kiállítás, érvényesség)
3. **`tests/ui-live/document-recognizer.md`** — Python Playwright spec on live admin stack:
   - Test 1: navigate to `/document-recognizer`, list shows 5 bootstrap doctypes
   - Test 2: drag-drop a `hu_invoice` fixture → recognize → result panel shows extracted fields
   - Test 3: click "Override for tenant" → edit YAML (change a regex) → save → re-recognize → updated descriptor used
4. **+1 Playwright + 8 vitest** — page + child component coverage

**Gate.**
- Live admin stack required (`bash scripts/start_stack.sh --full`)
- 5 doctypes browseable in the UI
- Per-tenant override creation + persistence + re-load works
- Type check (`npx tsc --noEmit`) clean

**Expected diff.** ~700 LOC TS + 1 YAML descriptor + 1 Playwright + 8 vitest.

**Risk.** R4 (low) — Monaco editor integration; mitigated by reusing the existing `RagCollections` side-drawer pattern.

### SV-5 — Per-doctype golden-path corpus + accuracy gate + close
**Scope.** The validation layer. Operator-curated fixture corpora + accuracy measurement script.

1. **Golden-path corpus** — `data/fixtures/doc_recognizer/<doctype>/`:
   - 5 fixture per doctype × 5 doctypes = 25 files (anonymized real documents where possible; synthetic where not)
   - `manifest.yaml` per doctype with expected extraction values for each fixture
2. **Accuracy measurement script** — `scripts/measure_doc_recognizer_accuracy.py`:
   - Reads all per-doctype fixture corpora
   - Runs `recognize_and_extract` on each
   - Compares extracted fields against expected; emits per-doctype accuracy + per-field accuracy
   - Uses the S156 `argparse_output()` helper (uniform `--output {text,json,jsonl}`)
3. **CI 3-doctype slice** — fast subset (1 fixture per doctype on 3 priority types: `hu_invoice`, `hu_id_card`, `pdf_contract`) gated at ≥ 75% overall accuracy
4. **Weekly per-doctype matrix** — promote `measure_doc_recognizer_accuracy.py` to `nightly-regression.yml` Mon 08:00 UTC (after the existing `uc3-4combo-matrix` at 07:00)
5. **Sprint V close docs** — `docs/sprint_v_retro.md`, `docs/sprint_v_pr_description.md`, `CLAUDE.md` banner flip + key-numbers update, `session_prompts/NEXT.md` → Post-Sprint-V audit prompt
6. **Tag `v1.6.0`** queued for post-merge

**Gate.**
- 3 doctype accuracy ≥ 80% on 5-fixture-per-type corpus (`hu_invoice` ≥ 90%, `hu_id_card` ≥ 80%, `pdf_contract` ≥ 80%; `hu_address_card` ≥ 70% best-effort, `eu_passport` ≥ 70% best-effort)
- Type classifier top-1 ≥ 90% on 25-fixture full corpus (cross-doctype false-positive ≤ 4%)
- Intent routing single-decision invariant (no fixture generates both `process` and `route_to_human`)
- UC1/2/3 regression unchanged (Sprint Q UC1 + Sprint J UC2 + Sprint K UC3 all green flag-off)
- OpenAPI drift gate green (snapshot refreshed for the 5 new SV-3 routes)

**Expected diff.** ~500 LOC + 25 fixture files + Sprint close docs.

**Risk.** R5 (low) — fixture curation bandwidth; mitigated by syntheticly-generated fixtures for non-PII types.

---

## 3. Plan, gate matrix

| Session | Theme | Golden-path test | Threshold | Rollback path |
|---|---|---|---|---|
| SV-1 | Contracts + safe-eval + skill rename | ruff clean + unit collect | 2475+ collected (no test count change yet) | Revert squash; skill rename preserves git history |
| SV-2 | Classifier + 2 doctype kickoff | UC1 invoice_processor regression check (existing path unchanged) + 2-doctype real-LLM round-trip | UC1 ≥ 75% / `invoice_number` ≥ 90% (regression); 2-doctype top-1 match success | Revert squash; doc_recognizer skill is additive, no shared state with invoice_processor |
| SV-3 | API endpoint + Alembic 048 + cost preflight + 2 doctype | OpenAPI drift gate green; cost preflight refusal contract test; alembic 048 round-trip | Drift gate `[ok]`; alembic upgrade → downgrade → upgrade clean | Revert squash; alembic downgrade -1 |
| SV-4 | Admin UI + 1 doctype + Playwright | live-stack Playwright + tsc clean | 3-test Playwright spec PASS | Revert squash; UI page is in `pages-new/` namespace, separate route from existing pages |
| SV-5 | Corpus + accuracy gate + close | 3 doctype accuracy ≥ 80%; classifier top-1 ≥ 90%; UC1/2/3 regression | All thresholds met; tag `v1.6.0` queued | Revert squash; sprint reschedules SV-5 with adjusted descriptors / fixtures |

**Threshold column blocks merge.** Any session that fails its gate halts; the operator either rolls forward (debug) or reverts the session and reschedules.

---

## 4. Risk register

### R1 — LLM fallback cost amplification
Every uncertain doc-type triggers 2 LLM calls (classifier + extractor) → cost 2× the per-call estimate. Mitigation: per-step `CostPreflightGuardrail.check_step()` (Sprint U S154 API) limits, per-doctype `llm_threshold_below` operator-tunable, dry-run mode tested by default in SV-3 integration tests.

### R2 — HU-specific regex/keyword brittleness
Hungarian tax-number pattern (`XXXXXXXX-X-XX`) only matches 1986+ formats; ID-card keywords vary across emission years. Mitigation: multiple weighted rules per doc-type, LLM fallback safety net, per-tenant override for known-broken regions.

### R3 — OCR quality on image-heavy doctypes
Address card, passport — JPG/PNG with rotation, glare, partial occlusion. Mitigation: `parser_preferences: [azure_di, docling, unstructured]` for image-heavy types; retry logic on initial parse failure; if accuracy < threshold → automatic `route_to_human` intent.

### R4 — PII leak in audit log / Langfuse trace
`hu_id_card.extracted_fields` contains PII. Audit boundary writes `<redacted>` + hash; `extracted_fields` JSONB column unredacted by default (operator opt-in encryption deferred to post-Sprint-V). Mitigation: `pii_level: high` flag triggers default `route_to_human` intent (no auto-process for PII docs).

### R5 — Per-tenant YAML override → invalid YAML → service crash
Operator uploads malformed YAML via `PUT /doctypes/{name}`. Mitigation: YAML-load Pydantic validation gate at write time (rejects with 400 + parse-error); fallback to bootstrap descriptor on lazy-load parse error + audit log entry + UI warning banner.

---

## 5. Definition of done

- [ ] All 5 sessions (SV-1..SV-5) merged on `main` with green CI
- [ ] 5 doctypes ship: `hu_invoice`, `hu_id_card`, `hu_address_card`, `eu_passport`, `pdf_contract`
- [ ] 3-doctype CI accuracy slice ≥ 75% overall
- [ ] Operator full corpus accuracy: `hu_invoice` ≥ 90%, `hu_id_card` ≥ 80%, `pdf_contract` ≥ 80%
- [ ] Type classifier top-1 ≥ 90% on full 25-fixture corpus
- [ ] UC1 `invoice_processor` golden-path unchanged (≥ 75% / `invoice_number` ≥ 90%)
- [ ] UC2 `aszf_rag_chat` MRR@5 ≥ 0.55 unchanged
- [ ] UC3 `email_intent_processor` 4/4 unchanged
- [ ] Alembic head: 048 (`doc_recognition_runs`)
- [ ] OpenAPI drift gate `[ok]` (snapshot refreshed for 5 new routes)
- [ ] Admin UI page `/document-recognizer` accessible from sidebar nav
- [ ] Live Playwright spec on `/document-recognizer` PASS
- [ ] `tag v1.6.0` queued for post-merge
- [ ] `docs/sprint_v_retro.md` + `docs/sprint_v_pr_description.md` published
- [ ] `session_prompts/NEXT.md` → Post-Sprint-V audit prompt

---

## 6. Out of scope (deferred to post-Sprint-V audit)

- Multi-tenant prod readiness (Vault AppRole IaC, `AIFLOW_ENV=prod` guard, `customer` → `tenant_id` rename)
- Observability bővítés (Grafana panels, ci-cross-uc kibővítés UC1-General-rel)
- Coverage uplift 70% → 80%
- Profile B Azure live (if credit lands)
- UC3 thread-aware classification (body-only cohort 100% felé)
- UC1 corpus extension to 25 fixtures (operator curation)
- Doc_recognizer per-doctype corpus extension to 10+
- ML classifier (kis fasttext / sklearn / kis BERT) replacing the rule-engine if accuracy demands
- `invoice_date` SQL column rename Alembic migration (Sprint U SU-FU-3)
- Doc-recognizer column-level encryption for PII fields (`AIFLOW_PII_ENCRYPTION__ENABLED`)
- Live Playwright `/prompts/workflows` (Sprint U SR-FU-4)
- Langfuse workflow listing surface (Sprint U SR-FU-6)

These items are tracked in `docs/sprint_u_retro.md` open-follow-ups + the audit doc's "Post-Sprint-V audit gate (DEFER)" section.

---

## 7. Skipped items tracker (initial)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| SV-SKIP-1 (planned) | `tests/integration/services/document_recognizer/test_classifier_real.py` | Real-LLM classifier accuracy test on 25-fixture corpus | `secrets.OPENAI_API_KEY` + scheduled (Mon 08:00 UTC weekly) |
| SV-SKIP-2 (planned) | `tests/ui-live/document-recognizer.md` | Live Playwright spec | Live admin stack required (`bash scripts/start_stack.sh --full`) |

Sprint U carry-forwards inherit unchanged: ST-SKIP-1, SU-SKIP-1, SU-SKIP-2, SS-SKIP-2.

---

## 8. STOP conditions

**HARD:**
1. UC1 `invoice_processor` golden-path regression — UC1 < 75% accuracy on the CI 3-fixture slice or `invoice_number` < 90%. The doc_recognizer skill is additive; if it touches existing UC1 behavior, halt.
2. Alembic 048 fails to round-trip (upgrade → downgrade → upgrade) cleanly. Halt and triage before SV-3 PR.
3. OpenAPI drift gate red after SV-3 — the new routes broke the snapshot. Halt; refresh + commit before merging.
4. Live Playwright spec on `/document-recognizer` fails on a clean stack — UI is broken. Halt; debug before SV-4 PR.
5. 3-doctype CI accuracy slice < 75%. Halt and adjust descriptors / fixtures.

**SOFT:**
- Cost amplification: weekly per-doctype matrix run cost > $2 on the 25-fixture corpus → halt cron job, adjust per-doctype `llm_threshold_below`.
- HU regex brittleness on real ID-card scans → adjust descriptor weights, fall back to LLM at lower threshold.

---

## 9. Post-Sprint-V audit (DEFER — not Sprint V scope)

Per the audit decision (`01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md` §"Post-Sprint-V audit gate"):

> Ha Sprint V gate green (3 doctype ≥ 80% accuracy + UC1/2/3 unchanged), akkor — és **csak akkor** — csináljunk teljes audit-ot a "professzionális működéshez szükséges struktúra" témára.

Audit topics for Sprint W:

- Multi-tenant prod readiness (Vault AppRole IaC, `AIFLOW_ENV=prod` boot guard, `customer` → `tenant_id` rename)
- Observability bővítés (Grafana panels for `cost_guardrail_refused`, `doc_recognizer_intent_distribution`, ci-cross-uc kibővítés UC1-General-rel)
- Coverage uplift 70% → 80%
- Profile B Azure live MRR@5 (if credit lands)
- UC3 thread-aware classification (body-only cohort 100% felé)
- Test corpus expansion (UC1 25, doc_recognizer per-type 10+)
- Doc_recognizer ML classifier (kis fasttext / sklearn / kis BERT) replacing rule-engine if accuracy demands
- Sprint U `invoice_date` → `issue_date` SQL column rename (SU-FU-3)

Output: Sprint W kickoff plan + post-v1.6 roadmap.

---

## 10. References

- Audit + design depth: `01_PLAN/AUDIT_2026_04_26_SPRINT_V_DIRECTION.md`
- Sprint U retro: `docs/sprint_u_retro.md`
- Sprint U plan: `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md`
- UC trajectory: `01_PLAN/110_USE_CASE_FIRST_REPLAN.md`
- Existing reusable contracts: `src/aiflow/contracts/cost_attribution.py`, `intake_package.py`, `routing_decision.py`, `extraction_result.py`
- Reusable services: `src/aiflow/services/document_extractor/`, `src/aiflow/services/classifier/`, `src/aiflow/guardrails/cost_preflight.py`
- Reusable PromptWorkflow: `src/aiflow/prompts/workflow.py`, `workflow_executor.py`
- Reusable admin UI patterns: `aiflow-admin/src/pages-new/RagCollections/`, `BudgetManagement/`
