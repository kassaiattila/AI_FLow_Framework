# AIFlow — Project audit (2026-04-26) + Sprint U rescope + Sprint V direction

> **Status:** APPROVED 2026-04-26 by operator. Output of a comprehensive audit triggered after the OneDrive→`C:\00_DEV_LOCAL` move regression cleared. This doc captures the as-is state, the rescope of Sprint U, and the strategic direction for Sprint V. Source: `C:\Users\kassaiattila\.claude\plans\most-csin-ljunk-egy-teljlesk-r-dreamy-boole.md`.

## Context

A projekt mappa költöztetése után (`OneDrive → C:\00_DEV_LOCAL`) teljes regression zöld, stack indítható. Az operator most teljes audit-ot kért:

1. **Mi van ténylegesen kész** — funkciók + állapot
2. **Mi funkcionálisan hiányos** — open follow-up-ok, scaffold-szintű komponensek
3. **Mi nem készült el a tervekből** — Sprint J → T retrospektívekben dokumentált debt
4. **Új implementációs terv** — frissítve a `session_prompts/NEXT.md` által jelzett Sprint U trajectory-vel

**Stratégiai redirekció (user input alapján):**

- **`invoice_finder` ne legyen számla-specifikus skill** → általánosítsuk **paraméterezhető dokumentum-típus + intent felismerő + adatkinyerő komponensre**. Pluggable doc-type config (számla, személyi igazolvány, …); minden type-hoz külön mező-csoport definiálható, ugyanaz a pipeline futtatja.
- **`qbpp_test_automation` skill** → backlog (most nem priority, scaffold marad).
- **Strategic gap audit** (Vault prod, customer→tenant_id rename, coverage 80%, observability) → **defer**, akkor csináljunk amikor UC1 + UC2 + UC3 + doc-recognizer mind szilárdan működik.

---

## Audit synthesis

### A. Sprint trajectory (J → T DONE; U mid-flight)

| Sprint | Tag | Status | Headline |
|--------|-----|--------|----------|
| J | v1.4.5 | DONE | UC2 RAG (BGE-M3 + Azure surrogate, MRR@5 ≥0.55 baseline) |
| K | v1.4.7 | DONE | UC3 email intent (4/4 golden path) |
| L | v1.4.8 | DONE | Cost monitoring + ci-cross-uc 42-test smoke |
| M | v1.4.9 | DONE | Vault hvac + self-hosted Langfuse + air-gap Profile A |
| N | v1.4.10 | DONE | Per-tenant budget + cost preflight guardrail |
| O | v1.4.11 | DONE | UC3 attachment-aware intent (32% misclass) |
| P | v1.4.12 | DONE | LLM fallback body/mixed cohort (4% misclass) |
| Q | v1.5.0 | DONE | UC1 invoice extraction wired (85.7% accuracy, 10-fixture) |
| R | v1.5.1 | DONE | PromptWorkflow scaffold (descriptor + DAG validator + admin UI) |
| S | v1.5.2 | DONE | Multi-tenant + multi-profile vector DB + admin UI |
| T | v1.5.3 | DONE | PromptWorkflow per-skill consumer migration (3 skills × 3 chains) |
| **U** | v1.5.4 | **mid-flight** (S152 kickoff merged, S153–S157 ütemezve) | Operational hardening |

### B. Open follow-ups összegzése (~30 db)

A Sprint J–T retrók 30+ FU ID-t hagytak. **Sprint U S153–S157 lefedi:** SR-FU-4/5/6 (a rescope után csak SR-FU-5), ST-FU-2/3/4/5, SQ-FU-1/2/4, SN-FU subset, SP-FU-2.

**Sprint U után is nyitva marad** (jelenlegi 118_ plan szerint Sprint V):

- `customer` → `tenant_id` model rename (SS-FU-1/5)
- Vault rotation E2E + AppRole IaC (SM-FU-1/2/4)
- Langfuse v3 → v4 server migration (SM-FU-5)
- Azure OpenAI Profile B live MRR@5 (SS-SKIP-2, blocked: credit pending)
- Coverage uplift 70% → 80% (SJ-FU-7)
- Grafana panel: `cost_guardrail_refused` vs `cost_cap_breached` (SN-FU-3)
- UC1 corpus extension to 25 fixtures (SQ-FU-3)
- UC3 `024_complaint_about_invoice` body-vs-attachment intractable conflict (SP-FU-1)
- **NEW** SR-FU-4 live Playwright `/prompts/workflows` + SR-FU-6 Langfuse listing (S155 rescope-ról ide tolódott)

**A user direkt instrukciója:** ezeket NE most tervezzük, hanem az UC1+UC2+UC3+DocRecognizer post-stable audit-on. Most csak Sprint V kickoff-ig megyünk.

### C. Skill-ek funkcionális mélysége (8 db)

| Skill | Mélység | Status |
|-------|---------|--------|
| `aszf_rag_chat` | 1287 LOC workflow, 7 prompt yaml, 1002 LOC test | **Production** (UC2) |
| `email_intent_processor` | 674 LOC workflow, 5 prompt yaml, 721 LOC test | **Production** (UC3) |
| `invoice_processor` | 1004 LOC workflow, 312 LOC test | **Production** (UC1) |
| `process_documentation` | ~1000 LOC, BPMN/diagram pipeline | **Production** |
| `cubix_course_capture` | 1977 LOC, RPA + transcript | **Production** (specific tenant) |
| `spec_writer` | 335 LOC workflow, 388 LOC test | **Partial** (stub-tesztek, kevés prompt) |
| `invoice_finder` | csak `__init__.py`+`__main__.py`+ models/ + prompts/ | **Scaffold** → **REFOCUS** (lásd Sprint V) |
| `qbpp_test_automation` | csak `tests/` mappa | **Scaffold** → **BACKLOG** (drop active scope) |

### D. UC fedettség

| UC | Status | Open FU-k Sprint U-ban | Open Sprint V-be |
|----|--------|-----------------------|------------------|
| **UC1 invoice extraction** | 85.7% accuracy | SQ-FU-1 issue_date fix (S156), SQ-FU-2 docling warmup (S156), SQ-FU-4 ISO date (S156) | SQ-FU-3 corpus 25 fixtures |
| **UC2 RAG chat** | MRR@5 ≥0.55 baseline | ST-FU-2 expert/mentor descriptors (S155) | Profile B Azure live (blocked) |
| **UC3 email intent** | 4% misclass | — (Sprint P done) | SP-FU-1 024 conflict, SO-FU-2/6/7 minor |
| **UC4 monitoring/cost** | per-tenant budgets + preflight | SN-FU-1/2/6 cost consolidation (S154) | SN-FU-3 Grafana, SN-FU-4 litellm CI audit |
| **UC1-General DocRecognizer** | nem létezik | — | **Sprint V headline scope** ✨ |

### E. Kód-szintű hiányosságok (top 5)

1. **`invoice_finder` skill üres** — nincs workflow, csak loader stub. Sprint V-ben általánosítjuk.
2. **`qbpp_test_automation` skeleton** — csak `tests/` dir. Backlog.
3. **`data_router` + `metadata_enricher` services** regisztráltak (305-306 LOC) de **nincs pipeline adapter / workflow hook** → "infrastructure ready, feature isolated".
4. **`aszf_rag_chat` Reflex UI upload TODO** — `ui/config_page.py:27` `rx.window_alert("Upload - TODO")`. RAG ingest pipeline él, csak UI hiányzik (admin-on át már működik a `/rag/collections` page).
5. **Pre-existing stale gate** — `tests/e2e/v1_4_1_phase_1b/test_multi_source_e2e.py:586` `assert passed == 199` (tényleges: 198). 1-soros fix kell, nem regresszió.

---

## Plan: Sprint U átrendezése

### Eredeti `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md`

5 session: S153 (CI gates) · S154 (cost consolidation) · S155 (PromptWorkflow ergonomics + personas) · S156 (Sprint Q polish + operator scripts) · S157 (close).

### Javasolt átrendezés

**Tartsd meg ahogy van**, EGY módosítással:

- **S155 csak az ST-FU-2 expert/mentor descriptors-t** szállítsa (additive, 2 új YAML, persona resolver update — kicsi, biztos)
- **SR-FU-4 live Playwright + SR-FU-6 Langfuse listing** S155-ből → Sprint V-be tolódik (alacsony érték; Sprint V doc-recognizer scope mellett természetesebben kezelhető)
- **S154 cost consolidation MARAD** Sprint U-ban — Sprint T S149 introducált egy ad-hoc `CostEstimator` + `CostGuardrailRefused` mintát ami az invoice_processor-ban él; ezt konszolidálni kell MIELŐTT a Sprint V doc-recognizer is bevezetné a saját implementációját. Tehát S154 hygiene-blocker a Sprint V scope-ra.

**Új Sprint U scope összefoglaló:**

| Session | Témakör | Diff (becslés) | Tesztek | Risk |
|---------|---------|----------------|---------|------|
| S153 | CI hookups (5 micro-win) | ~80 LOC | 0 | low (revertable per-batch) |
| S154 | Cost/Settings consolidation | ~250 LOC | +8-14 unit | medium (env-alias shim) |
| S155 | Expert/mentor descriptors + persona resolver | ~80 LOC | +4-6 unit | low (additive) |
| S156 | UC1 polish (issue_date + docling warmup + ISO date + operator script parity) | ~180 LOC | +8-12 unit | medium (issue_date regression on already-correct fixtures) |
| S157 | Sprint U close + Sprint V plan publish | ~60 LOC docs | 0 | low |

**Mit teszünk hozzá az eredeti tervhez:** `S157` close session deliver-eli a **`01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`** dokumentumot — Sprint V kickoff plan. (Ez a plan-doc maga a Sprint V-be tolt kickoff.)

---

## Plan: Sprint V vázlat — Generic Document Recognizer (UC1-General)

### Cél

Egy **paraméterezhető, általános dokumentum felismerő + adatkinyerő skill**, ami helyettesíti és általánosítja a jelenlegi `invoice_finder` scaffold-ot. Pluggable doc-type registry: az operator YAML-ban definiál új doc-típust + extraction field-eket, kód-változás nélkül.

**Use cases bedrótozva:**

- **DocType: `hu_invoice`** — magyar számla (vendor, buyer, invoice_number, dates, items, totals — mint UC1 invoice_processor)
- **DocType: `hu_id_card`** — magyar személyi igazolvány (név, szem.szám, születési dátum, kiállítás dátuma, érvényesség, állampolgárság)
- **DocType: `hu_address_card`** — magyar lakcímkártya (név, lakcím, kiállítás dátuma)
- **DocType: `eu_passport`** — EU útlevél (név, útlevélszám, születési dátum, kiállítás, érvényesség)
- **DocType: `pdf_contract`** — szerződés (felek, tárgy, hatály, díjazás)
- (operator-extensible)

### Architektúra reuse

A skill **NEM újraépíti** ami már megvan:

- **`document_extractor` service** routing szétválaszt parser-ek között (docling / Azure DI / unstructured) — már megvan
- **`PromptWorkflow` scaffold** (Sprint R) — DAG-validated multi-step prompt chain, doc-type-onként 1 descriptor
- **`invoice_extraction_chain.yaml`** (Sprint T S149) — már létezik mint sablon, `hu_invoice` doc-type-nak ez a default workflow
- **`UnstructuredChunker` + `EmbedderProvider`** (Sprint J) — opcionális enrichment doc-típus-onként
- **`ClassifierService`** (UC3 keretek között) — doc-type recognition layer (PDF/DOCX/IMG felismerés a doc body alapján)

### Új komponensek (Sprint V szállít)

1. **`skills/document_recognizer/`** — átnevezzük az `invoice_finder/` mappát + bővítjük (alternatíva: új skill, `invoice_finder` deprecated)
   - `skill.yaml` — `name: document_recognizer`
   - `workflows/recognize_and_extract.py` — egyetlen workflow, paraméter `doc_type`
   - `prompts/doctype_classifier.yaml` — doc-type identification (input: parsed text; output: `doc_type` enum)
   - `prompts/extract_<doctype>.yaml` — per-doc-type extraction prompt (3-5 prompt yaml a kezdő 5 doc-type-hoz)
   - `tests/` — 1 fixture per doc-type, end-to-end accuracy gate

2. **`src/aiflow/services/document_recognizer/registry.py`** — DocType registry
   - `DocTypeDescriptor` Pydantic model (név, várt mezők lista, validators, prompt-ID, parser preferences)
   - `register_doctype(descriptor)` + `list_doctypes()` + `get_doctype(name)`
   - YAML loader: `data/doctypes/<name>.yaml`
   - Bootstrap: 5 built-in YAML fájl (hu_invoice, hu_id_card, hu_address_card, eu_passport, pdf_contract)

3. **`src/aiflow/contracts/doc_recognition.py`** — Pydantic szerződések
   - `DocRecognitionRequest` (file path / bytes + optional `doc_type` hint)
   - `DocTypeMatch` (doc_type + confidence + alternatives)
   - `DocExtractionResult` (doc_type + extracted_fields dict + per-field confidence)

4. **API endpoint** — `POST /api/v1/document-recognizer/recognize`
   - Input: file upload + optional doc_type hint
   - Output: `DocExtractionResult`
   - Ugyanazon a JWT-n + multi-tenant (tenant_id) mint a többi router
   - Cost guardrail integration (consolidated `CostPreflightGuardrail` Sprint U S154 után)

5. **Admin UI page** — `/document-recognizer`
   - Doc-type registry browser (lista + detail)
   - Upload + recognize teszt felület (drag-drop file → result panel)
   - Operator-side new doc-type form (POST creates YAML descriptor)

6. **Alembic migration `048`** — `doc_recognition_runs` tábla (audit + observability)
   - oszlopok: `id`, `tenant_id`, `doc_type`, `confidence`, `extracted_fields_jsonb`, `cost_usd`, `created_at`
   - indexek: `(tenant_id, created_at DESC)`, `(doc_type, created_at DESC)`

### Sprint V ülésrendje (5 session, ~3 hét)

| Session | Téma | Deliverables | Diff (becslés) | Tesztek |
|---------|------|--------------|----------------|---------|
| **SV-1** | Contracts + DocTypeDescriptor Pydantic + safe-eval + skill rename | `src/aiflow/contracts/doc_recognition.py` (8 Pydantic class) · `src/aiflow/services/document_recognizer/{registry,classifier,intent_router,extractor}.py` skeleton · `src/aiflow/services/document_recognizer/safe_eval.py` (simpleeval wrapper) · `skills/document_recognizer/` rename `invoice_finder/` → `document_recognizer/` (keep git history) · `skills/invoice_finder/` becomes deprecated alias (re-export only) | ~600 LOC + skill rename | +18 unit (Pydantic round-trip + safe-eval grammar + DAG load) |
| **SV-2** | Type classifier (rule-engine + LLM fallback) + 2 doctype kickoff | `services/document_recognizer/classifier.py` 5 rule-kind support · `data/doctypes/hu_invoice.yaml` + `hu_id_card.yaml` (full descriptor) · `prompts/workflows/id_card_extraction_chain.yaml` (új 4-step DAG: ocr_normalize → fields → confidence → validate) · `services/document_recognizer/orchestrator.py` (parse → classify → extract → intent) · per-tenant override loader | ~700 LOC + 2 YAML descriptor + 1 PromptWorkflow YAML | +20 unit (rule-engine 5 kind + LLM fallback gate + tenant override) + 4 integration (real PG, real docling, real OpenAI on 1 fixture per doctype) |
| **SV-3** | API endpoint + Alembic 048 `doc_recognition_runs` + cost preflight integration + 2 további doctype | `src/aiflow/api/v1/document_recognizer.py` (5 routes: POST /recognize, GET /doctypes, GET /doctypes/{name}, PUT /doctypes/{name} per-tenant override, DELETE override) · `alembic/versions/048_doc_recognition_runs.py` · `data/doctypes/hu_address_card.yaml` + `pdf_contract.yaml` · CostPreflightGuardrail integration (S154 `check_step()` API after consolidation) · `audit_log` boundary PII redactor | ~450 LOC + 2 YAML | +14 unit (router shape + path traversal guard + tenant_id mismatch + Alembic round-trip) + 3 integration (real PG + real OpenAI per-doctype) |
| **SV-4** | Admin UI page (3 felület) + 1 további doctype + Playwright | `aiflow-admin/src/pages-new/DocumentRecognizer/` (Browse + Recognize + DocTypeEditor) · Monaco YAML editor (read-only validate + save) · `data/doctypes/eu_passport.yaml` (5. és utolsó kezdő doctype) · `tests/ui-live/document-recognizer.md` Playwright spec a `/document-recognizer` flow-ra (upload → recognize → result panel + per-tenant YAML override save → re-recognize) | ~700 LOC TS + 1 YAML | +1 live Playwright E2E (live admin stack) + 8 vitest (page + child component) |
| **SV-5** | Per-doctype golden-path corpus + accuracy gate + close | `data/fixtures/doc_recognizer/<doctype>/` (5 fixture per type × 5 doctypes = 25 file) · `scripts/measure_doc_recognizer_accuracy.py` (uniform `--output {text,json,jsonl}` per S156 ST-FU-4 pattern) · `docs/sprint_v_retro.md` + `docs/sprint_v_pr_description.md` · CLAUDE.md banner flip · tag `v1.6.0` queued | ~500 LOC + 25 fixture | +1 ci-cross-uc gate (3 doctype slice ≥75% accuracy on CI) + +1 nightly weekly per-doctype matrix |

**Sprint V gate:**

1. **Doc-type accuracy** — `hu_invoice` ≥ 90% (mert `invoice_extraction_chain` reuse-ból), `hu_id_card` ≥ 80%, `pdf_contract` ≥ 80% on 5-fixture-per-type corpus. `hu_address_card` és `eu_passport` ≥ 70% (best-effort, kevés HU-fixture nyilvánosan elérhető).
2. **Type classifier accuracy** — top-1 doc-type match ≥ 90% on the 25-fixture full corpus (cross-doctype false-positive ≤ 4%).
3. **Intent routing** — minden fixture pontosan EGY intent-et generál (no `process` + `route_to_human` egyszerre).
4. **Regression** — UC1 `invoice_processor` byte-stable (Sprint Q UC1 ≥ 75% / `invoice_number` ≥ 90% gate), UC2 MRR@5 ≥ 0.55, UC3 4/4 unchanged.
5. **API contract** — OpenAPI drift CI step (Sprint U S153) zöld; `docs/api/openapi.json` snapshot frissítve a 5 új route-tal.

### Sprint V kockázatok (R1–R5)

| ID | Kockázat | Mitigation |
|----|----------|-----------|
| **R1** | LLM fallback cost amplification — minden bizonytalan típusú dok 2× LLM call (klasszifier + extraktor) | Per-step CostPreflightGuardrail.check_step() limit (S154 után), per-doctype `llm_threshold_below` operator-tunable, dry-run mode default-tested |
| **R2** | HU-specifikus regex/keyword brittleness — pl. `8 számjegy + kötőjel + szám + kötőjel + 2 számjegy` adószám csak 1986+ számokra ad jó találatot | Multiple weighted rules per doc-type, LLM fallback safety net, per-tenant override |
| **R3** | OCR pontosság képszerű igazolványoknál (rossz minőségű scan) | Azure DI primary, docling fallback, retry logic; ha pontosság < threshold → automatic `route_to_human` |
| **R4** | PII leak in audit log/Langfuse trace — id_card extracted_fields PII | `pii_redaction: true` boundary-n, `extracted_fields` JSONB encrypted (opt-in), audit log csak hash + tag |
| **R5** | Per-tenant YAML override → invalid YAML → service crash | YAML-load Pydantic validation gate, fallback to bootstrap descriptor on parse error + UI warning + audit log entry |

### Doc-type classification — működési mechanizmus

A felismerő egy **3-lépcsős pipeline**:

```
File (bytes/path)
    │
    ▼  parser_preferences (docling → azure_di → unstructured)
[Parsed text + structure (pages, tables, blocks) + metadata]
    │
    ▼  rule-based scorer (regex + keyword_list + structure hints)
[Per-doc-type rule scores: hu_invoice=0.82, hu_id_card=0.05, ...]
    │
    ▼  if max_score < llm_threshold → LLM classifier with top-k descriptors
[DocTypeMatch: doc_type=hu_invoice, confidence=0.82, alternatives=[(pdf_contract, 0.18)]]
    │
    ▼  selected DocType's extraction PromptWorkflow runs
[DocExtractionResult: doc_type=hu_invoice, extracted_fields={invoice_number=..., total_gross=...},
                     per_field_confidence={...}, validation_warnings=[...]]
    │
    ▼  intent_routing rules evaluated against extracted_fields + confidence
[DocIntentDecision: intent=process | route_to_human | reject | rag_ingest | respond,
                    reason=..., next_action=...]
```

**Classifier rule kinds (YAML-driven):**

| Kind | Match | Weight |
|------|-------|--------|
| `regex` | regex hit a parsed text-ben (case-insensitive default) | per-rule weight |
| `keyword_list` | min N kulcsszó hits (operator állítja a threshold-ot) | per-rule weight |
| `structure_hint` | pl. "table_count >= 1" vagy "page_count == 1" | per-rule weight |
| `filename_match` | regex a fájlnévre (pl. `^szamla_.*\\.pdf$`) | per-rule weight |
| `parser_metadata` | docling/Azure DI által visszaadott `language`, `mime_type` | per-rule weight |

A score-ok normalizáltak (`sum(weights) == 1.0` per descriptor); az aggregált doc-type score a hits weight-jeinek összege.

**LLM fallback** csak akkor fut, ha a top rule-score < `llm_threshold_below` (default 0.7). Az LLM-nek a top-k (default k=3) doc-type descriptor metadata + first 1500 chars of parsed text van adva; a válasz egy enum + confidence.

### Intent routing — szemantika

Az **intent** itt nem azonos a Sprint K UC3 email-intent fogalmával (ami a `EXTRACT/REPLY/IGNORE` triage volt). Document intent = **mit csináljunk a dokumentummal a felismerés után**:

| Intent | Mit jelent | Tipikus trigger |
|--------|-----------|-----------------|
| `process` | Extract → persist (DB, JSONB) → done | High confidence + complete required fields |
| `route_to_human` | Human review queue (Reviews UI page) | Low confidence OR business rule (pl. nagy összeg) OR PII detected |
| `rag_ingest` | Doc-recognizer kihagyja a strukturált extraction-t, helyette RAG ingest pipeline-ba küldi | Knowledge-base / referencia doc-type-ok (`pdf_contract` template-ek) |
| `respond` | Választ generálni (LLM válasz draft a Reviews UI-on) | Customer letter / panaszlevél |
| `reject` | Strukturált hibaüzenet, nem perzistál | Tiltott tartalom, validation hard-fail, PII without consent |

A descriptor `intent_routing` szekciója egy default + feltételes szabálylista:

```yaml
intent_routing:
  default: process
  conditions:
    - if: "extracted.total_gross > 1000000"     # safe expr eval (Pydantic + restricted operators)
      intent: route_to_human
      reason: "Magas összegű számla — kötelező manuális ellenőrzés"
    - if: "field_confidence_min < 0.6"
      intent: route_to_human
      reason: "Alacsony adatkinyerési bizonyosság"
    - if: "doc_type_confidence < 0.75"
      intent: route_to_human
      reason: "Bizonytalan dokumentum-típus"
```

A safe-expression-eval **NEM** Python `eval()` — egy zárt grammatika (Pydantic + operator: `==`, `!=`, `<`, `>`, `<=`, `>=`, `and`, `or`, `not`, `in`, `extracted.<field>`, `field_confidence_min`, `field_confidence_max`, `doc_type_confidence`, `pii_detected`).

### YAML descriptor minta — `hu_invoice`

```yaml
# data/doctypes/hu_invoice.yaml
name: hu_invoice
display_name: "Magyar számla"
description: "ÁFA-tartalmú HU számla, B2B/B2C"
language: hu
category: financial
version: 1
parser_preferences:
  - docling      # PDF/DOCX szerkezet-aware
  - azure_di     # OCR scan-ekhez
  - unstructured # last-resort
type_classifier:
  rules:
    - kind: regex
      pattern: "\\bSzámla\\s*sz[aá]m\\b|\\bszámlasorszám\\b"
      weight: 0.35
    - kind: regex
      pattern: "\\bÁfa-azonosító\\b|\\bAdószám\\b"
      weight: 0.25
    - kind: keyword_list
      keywords: ["fizetési határidő", "teljesítés időpontja", "nettó", "bruttó", "ÁFA", "végösszeg"]
      threshold: 2
      weight: 0.25
    - kind: structure_hint
      hint: "table_count >= 1"
      weight: 0.10
    - kind: filename_match
      pattern: "^(invoice|szamla|szla|sz)[-_].*\\.(pdf|png|jpg|jpeg|tiff)$"
      weight: 0.05
  llm_fallback: true
  llm_threshold_below: 0.70
extraction:
  workflow: invoice_extraction_chain   # Sprint T S149 PromptWorkflow descriptor (reused)
  fields:
    - name: invoice_number
      type: string
      required: true
      validators: ["non_empty", "regex:^[A-Za-z0-9/-]+$"]
    - name: vendor_name
      type: string
      required: true
    - name: vendor_tax_id
      type: string
      validators: ["regex:^\\d{8}-\\d-\\d{2}$"]   # HU adószám pattern
    - name: buyer_name
      type: string
      required: true
    - name: buyer_tax_id
      type: string
      validators: ["regex:^\\d{8}-\\d-\\d{2}$"]
    - name: invoice_date
      type: date
      required: true
      validators: ["iso_date"]
    - name: due_date
      type: date
      validators: ["iso_date"]
    - name: total_net
      type: money
      currency_default: HUF
    - name: total_vat
      type: money
      currency_default: HUF
    - name: total_gross
      type: money
      required: true
      currency_default: HUF
    - name: line_items
      type: list[invoice_line]
      schema_ref: hu_invoice_line
intent_routing:
  default: process
  conditions:
    - if: "extracted.total_gross > 1000000"
      intent: route_to_human
      reason: "Magas összegű számla — kötelező manuális ellenőrzés (HU > 1M HUF)"
    - if: "field_confidence_min < 0.6"
      intent: route_to_human
      reason: "Alacsony adatkinyerési bizonyosság"
    - if: "doc_type_confidence < 0.75"
      intent: route_to_human
      reason: "Bizonytalan dokumentum-típus klasszifikáció"
```

### YAML descriptor minta — `hu_id_card`

```yaml
# data/doctypes/hu_id_card.yaml
name: hu_id_card
display_name: "Magyar személyi igazolvány"
description: "Magyar állampolgári személyi igazolvány (eID és kártya formátum)"
language: hu
category: identity
version: 1
pii_level: high                          # PII-aware — lásd intent_routing
parser_preferences:
  - azure_di                             # OCR-heavy, kép-alapú
  - docling
type_classifier:
  rules:
    - kind: regex
      pattern: "MAGYARORSZÁG|HUNGARY"
      weight: 0.20
    - kind: regex
      pattern: "Személyazonos[ií]t[oó]\\s+igazolv[aá]ny|IDENTITY CARD"
      weight: 0.40
    - kind: regex
      pattern: "\\b\\d{6}[A-Z]{2}\\b"    # HU igazolvány-szám pattern
      weight: 0.30
    - kind: structure_hint
      hint: "page_count == 1"
      weight: 0.10
  llm_fallback: true
  llm_threshold_below: 0.65
extraction:
  workflow: id_card_extraction_chain     # NEW PromptWorkflow descriptor (Sprint V SV-2)
  fields:
    - name: full_name
      type: string
      required: true
    - name: birth_date
      type: date
      required: true
      validators: ["iso_date", "before_today"]
    - name: birth_place
      type: string
    - name: id_number
      type: string
      required: true
      validators: ["regex:^\\d{6}[A-Z]{2}$"]
    - name: issue_date
      type: date
      validators: ["iso_date"]
    - name: validity_date
      type: date
      validators: ["iso_date"]
    - name: nationality
      type: string
      default: "magyar"
    - name: mother_name
      type: string
intent_routing:
  default: route_to_human                # PII → mindig human review default
  pii_redaction: true                    # extracted_fields PII oszlopok REDACTED log-ban
  conditions:
    - if: "doc_type_confidence < 0.85"
      intent: reject
      reason: "ID-kártya bizonyítatlan klasszifikáció — PII miatt nem perzisztálható"
```

### Field types + validators

| Type | Pydantic alap | Példa validator |
|------|---------------|-----------------|
| `string` | `str` | `non_empty`, `regex:<pattern>`, `min_length:N`, `max_length:N` |
| `date` | `datetime.date` (ISO `YYYY-MM-DD` string) | `iso_date`, `before_today`, `after_today`, `not_in_future` |
| `money` | `Decimal` + currency code | `min:N`, `max:N`, `currency_in:[HUF,EUR,USD]` |
| `int` | `int` | `min:N`, `max:N` |
| `enum` | `Literal[...]` | YAML `enum: [val1, val2]` |
| `list[<type>]` | `list[<inner>]` | `min_count:N`, `schema_ref:<doctype>_<sub>` |
| `bool` | `bool` | — |

A validator-ek **post-extraction** futnak a `DocExtractionResult` ellen. Ha hard validator fail → `validation_warnings` mezőbe kerül + a field `confidence = 0`. Ha `required=true` mezőre fail → automatikusan `intent_routing.conditions` `field_confidence_min < threshold`-jét triggereli (és onnan `route_to_human`).

### Multi-tenancy + per-tenant override

A descriptor-ok két forrásból töltődnek (sorrendben):

1. **Bootstrap (built-in):** `data/doctypes/<name>.yaml` — git-ben tárolt 5 alap (hu_invoice, hu_id_card, hu_address_card, eu_passport, pdf_contract).
2. **Per-tenant override:** `data/doctypes/_tenant/<tenant_id>/<name>.yaml` — operator-uploaded YAML; ha létezik tenant-specific verzió ugyanazon a `name`-en, az felülírja.

A `DocTypeRegistry` runtime-ban tenant-aware → ha tenant X-nek van saját `hu_invoice.yaml`-je (pl. külön VAT tax-id pattern), akkor azt látja, különben a bootstrap-et.

**Admin UI flow** (Sprint V SV-4):
- Operator a `/document-recognizer/doctypes` lapon látja a doc-type listát
- Klikk + "Override for tenant" gomb → YAML-szerkesztő side-drawer (Monaco editor)
- Mentés → `data/doctypes/_tenant/<tenant_id>/<name>.yaml` perzistál + cache invalidate
- "Test" gomb → file upload + dry-run a frissen mentett descriptor-ral

### Sprint V open kérdések (S157-ben kell eldönteni)

- **Renaming vs új skill:** átnevezzük `invoice_finder` → `document_recognizer`, vagy új skill létrehozása + `invoice_finder` törlés? (recommendation: **rename**, mert preserve git history és skill registry már várja)
- **`invoice_processor` jövője:** marad-e külön skill UC1-re, vagy doc_recognizer wrap-eli? (recommendation: **mindkettő marad**; doc_recognizer ÚJ skill, invoice_processor a "specifikus" path; doc_recognizer alapértelmezetten az invoice_processor extraction chain-et hívja `hu_invoice` doc-type-ra — kompatibilitás megmarad)
- **Magyar OCR pontosság:** a docling vs Azure DI-t hogyan választjuk személyi igazolvány képhez (JPG/PNG)? Profile A (air-gap) vs Profile B (Azure).
- **PII redaction layer:** `hu_id_card` descriptor-ben `pii_level: high` jelölve. **Ki a felelős** a redakcióért? Lehetőségek: (a) `DocRecognitionService.run()` post-extraction lépésben, (b) `audit` service log-write boundary-n, (c) per-doc-type custom redactor plugin. **Recommendation:** (b) — boundary-on, az audit logba PII-mentes hash + per-field tag (`pii_redacted=true`) megy, a `extracted_fields` JSONB DB-ben titkosítva (operator opt-in `AIFLOW_PII_ENCRYPTION__ENABLED`).
- **Type classifier rule-engine vs ML model:** a 3-lépcsős pipeline első fázisa rule-based; van-e később hozzáadott ML klasszifier (kis fasttext / sklearn / kis BERT)? **Recommendation:** Sprint V scope-ban CSAK rule-based + LLM fallback; ML klasszifier post-Sprint-V audit + külön sprint, ha a fixture-corpus pontatlan eredményeket mutat.
- **`safe-expression-eval` engine:** saját parser vs. `simpleeval` library. Recommendation: `simpleeval` (battle-tested, pinned version), restricted operator list a config-ban.

---

## Post-Sprint-V audit gate (DEFER)

Ha Sprint V gate green (3 doctype ≥ 80% accuracy + UC1/2/3 unchanged), akkor — és **csak akkor** — csináljunk teljes audit-ot a "professzionális működéshez szükséges struktúra" témára:

- Multi-tenant prod readiness (Vault AppRole IaC, `AIFLOW_ENV=prod` guard, customer→tenant_id rename)
- Observability bővítés (Grafana panels, ci-cross-uc kibővítés UC1-General-rel)
- Coverage uplift 70%→80% (most ~70% — a Sprint V kódbázis bővítéssel várhatóan nem változik dramatikusan)
- Profile B Azure live (ha közben jött credit)
- UC3 thread-aware classification (body-only cohort 100% felé)
- Test corpus expansion (UC1 25, doc_recognizer per-type 10+)

Ennek az audit-nak az output-ja Sprint W kickoff plan + post-v1.6 roadmap.

---

## Critical files (módosítandó / létrehozandó)

### Most létrehozandó (Sprint V plan publishing — S157 close-ban szállítandó)

- `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md` — Sprint V plan dokumentum (struktúra: Goal · Capability cohort delta · Sessions · Risk register · Gate matrix · Skipped tracker)

### Sprint V execution során

- `skills/document_recognizer/` — új vagy átnevezett skill mappa
- `src/aiflow/services/document_recognizer/` — új service (registry + orchestrator)
- `src/aiflow/contracts/doc_recognition.py` — új contract
- `src/aiflow/api/v1/document_recognizer.py` — új router
- `data/doctypes/*.yaml` — új doc-type descriptors (5 db kezdetben)
- `prompts/workflows/recognize_<doctype>_chain.yaml` — új PromptWorkflow descriptors (5 db)
- `aiflow-admin/src/pages-new/DocumentRecognizer/` — új admin UI page
- `alembic/versions/048_doc_recognition_runs.py` — új migration
- `tests/integration/services/document_recognizer/` — új integration test mappa
- `tests/e2e/v1_6_0_doc_recognizer/` — új E2E suite

### Sprint U S157-ben módosítandó (átrendezés tükre)

- `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` — S155 scope szűkítés (csak ST-FU-2; SR-FU-4/6 → Sprint V/W)
- `session_prompts/NEXT.md` — S153 prompt változatlan, de close section frissítése S154 helyett S155 ütemmel
- `CLAUDE.md` — Sprint U scope-frissítés (S155 csak persona descriptors)

### Drop / dormant — szándékos

- `skills/qbpp_test_automation/` — backlog, kódbázisban marad de roadmap-en NEM Sprint V scope (külön, ha priority)

---

## Existing functions / utilities to reuse (no need to re-implement)

| Reusable | Path | Mit ad |
|----------|------|--------|
| `PromptWorkflow` + `PromptWorkflowExecutor` | `src/aiflow/prompts/workflow.py`, `src/aiflow/prompts/workflow_executor.py` | DAG-validated multi-step prompt chain — doc_recognizer szerződés ezzel valósul meg |
| `DocumentExtractor` service | `src/aiflow/services/document_extractor/` | Parser routing (docling/Azure DI/unstructured) — doc_recognizer ezt hívja |
| `ClassifierService` | `src/aiflow/services/classifier/` | Doc-type recognition layer alapja (Sprint K UC3 mintára) |
| `CostPreflightGuardrail` | `src/aiflow/guardrails/cost_preflight.py` | Per-call cost gate — Sprint U S154 után `check_step()` API-t adja |
| `EmbedderProvider` + `ChunkerProvider` | `src/aiflow/providers/embedder/`, `chunker/` | Optional enrichment doc-type-onként (pl. semantic search) |
| Alembic boilerplate | `alembic/versions/047_*.py` | 048-as migration sablonja |
| Admin UI patterns | `aiflow-admin/src/pages-new/RagCollections/`, `BudgetManagement/` | Side-drawer + form patterns reuse |
| FastAPI router patterns | `src/aiflow/api/v1/rag_collections.py`, `tenant_budgets.py` | Multi-tenant + JWT + dim-guard mintáját reuse |
| ProviderRegistry | `src/aiflow/providers/registry.py` | Doc-type plugin pattern alapja (5 ABC slot van; 6.-ként `DocTypeProvider`-t lehet majd hozzáadni S?-ben) |

---

## Verification (how to test end-to-end)

### Sprint U átrendezés validáció (S157 előtt)

```bash
# 1. Sprint U S153-S155 mind merged
git log --oneline main | head -20 | grep -E "Sprint U S15[3-5]"

# 2. Sprint T golden paths zöld (S154 nem törhet)
AIFLOW_LANGFUSE__ENABLED=false PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/integration/skills/test_uc1_golden_path.py \
              tests/integration/skills/test_email_intent_workflow.py \
              tests/integration/skills/test_aszf_rag_baseline_workflow.py \
              --timeout=300

# 3. Sprint Q UC1 issue_date ≥90% (S156 gate)
.venv/Scripts/python.exe scripts/measure_uc1_golden_path.py --output text \
    | grep "issue_date" | awk '{print $NF}'   # várható: ≥0.90
```

### Sprint V kickoff validáció (SV-1 plan-doc publishing)

```bash
# 1. Sprint V plan dokumentum létezik
ls 01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md

# 2. DocTypeDescriptor unit tesztek
PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/unit/services/document_recognizer/test_registry.py -v
```

### Sprint V end-to-end validáció (SV-5 close gate)

```bash
# 1. 3 doc-type ≥80% accuracy (a per-type fixture set-en)
.venv/Scripts/python.exe scripts/measure_doc_recognizer_accuracy.py \
    --doctypes hu_invoice,hu_id_card,pdf_contract --output json \
    | jq '.results[] | select(.accuracy < 0.80)'   # várható: empty

# 2. UC1 invoice_processor változatlan (regression)
AIFLOW_LANGFUSE__ENABLED=false PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/integration/skills/test_uc1_golden_path.py --timeout=300

# 3. UC2 + UC3 golden paths zöld
AIFLOW_LANGFUSE__ENABLED=false PYTHONPATH=src .venv/Scripts/python.exe \
    -m pytest tests/integration/skills/ --timeout=300

# 4. Admin UI E2E: doc-recognizer page interactive flow
# (Sprint V SV-4 deliverable; live stack required: bash scripts/start_stack.sh --full)
.venv/Scripts/python.exe -m pytest tests/e2e/v1_6_0_doc_recognizer/test_recognizer_ui.py -v

# 5. Alembic 048 round-trip
PYTHONPATH=src .venv/Scripts/python.exe -m alembic upgrade head && \
PYTHONPATH=src .venv/Scripts/python.exe -m alembic downgrade -1 && \
PYTHONPATH=src .venv/Scripts/python.exe -m alembic upgrade head
```

### Stack health (mindig)

```bash
bash scripts/start_stack.sh --validate-only
bash scripts/smoke_test.sh
```

---

## Summary

1. **Sprint U futása változatlan** S153 + S154 + S156 + S157 ütemben, **S155 scope szűkül** csak az ST-FU-2 expert/mentor descriptors-ra. (SR-FU-4/6 Sprint V/W-be tolódik.)
2. **S157 close session deliver-eli** `01_PLAN/119_SPRINT_V_DOCUMENT_RECOGNIZER_PLAN.md`-t.
3. **Sprint V headline:** generic document recognizer skill — paraméterezhető doc-type registry + multi-doctype extraction (5 doc-type kezdetben: hu_invoice, hu_id_card, hu_address_card, eu_passport, pdf_contract).
4. **`invoice_finder` átnevezés** `document_recognizer`-re; `invoice_processor` byte-stable marad a UC1 specifikus path-on.
5. **`qbpp_test_automation` backlog** — Sprint V scope-on kívül.
6. **Strategic gap audit** (Vault prod, customer→tenant_id, coverage 80%, observability bővítés) — **defer** Sprint V close utánra, akkor csináljunk operator-driven audit-ot.
