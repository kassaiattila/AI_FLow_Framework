# AIFlow Sprint B — Session 27 Prompt (B3.5: Confidence Scoring Hardening)

> **Datum:** 2026-04-06
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `aecce10`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S26 — B3.2 DONE (Invoice Finder extract + payment + report + notify — 16 unit test)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B3.5 szekció, sor 1057+)

---

## KONTEXTUS

### B3.2 Eredmenyek (S26 — DONE)

- `payment_status_adapter.py` — PaymentStatusAdapter (date-based: overdue/due_soon/not_due/unknown)
- `report_generator_adapter.py` — ReportGeneratorAdapter (Markdown + CSV riport generalas)
- 4 uj prompt YAML: `invoice_field_extractor.yaml`, `invoice_payment_status.yaml`, `invoice_report_generator.yaml`, `invoice_report_notification.yaml`
- `PaymentStatus` + `ReportResult` modellek hozzaadva `skills/invoice_finder/models/__init__.py`-hez
- 16 unit test PASS (4 fajl), 0 regresszio
- Regression: 1352 unit test, commit aecce10

### Infrastruktura (v1.3.0 — frissitett szamok)

- 26 service | 165 API endpoint (25 router) | 46 DB tabla | 29 migracio
- 21 pipeline adapter | 7 pipeline template | 6 skill | 22 UI oldal
- 1352 unit test | 129 guardrail teszt | 97 security teszt | 54 promptfoo teszt
- Guardrail: A5 rule-based + B1.1 LLM fallback + B1.2 per-skill config
- Invoice Finder pipeline: 8-step komplett (search→acquire→classify→extract→payment→organize→report→notify)

### Jelenlegi Confidence Scoring Allapot (AUDIT — B3.5.1)

```
=== PROBLEMA TERKEP ===

KRITIKUS (routing-ot befolyasol):

  #1: Confidence→Review routing NEM LETEZIK
      HumanReviewService kesz (src/aiflow/services/human_review/service.py),
      de SEMMI nem hivja automatikusan confidence alapjan.
      Tervezett kuszobok (>=0.90 auto, >=0.70 review, <0.50 reject)
      de NINCS bekotve a kodban!

  #2: LLM self-report konfidencia MEGBIZHATATLAN
      4 komponens vakon bizik: classifier, doc_extractor,
      entity_extractor, free_text. Az LLM 0.9-et mond de
      a valos pontossag lehet 60%.

  #3: NINCS per-field konfidencia
      Dokumentum extrakcional csak 1 osszesitett szam van.
      A user NEM TUDJA melyik mezo lehet hibas.

KOZEPES (minoseg):
  - BM25 nem normalizalt (0.6*cosine + 0.4*BM25 > 1.0 lehetseges)
  - SequenceMatcher hallucination scoring (karakter, nem szemantikus)
  - Hardcoded entity confidence (regex=0.9, LLM=0.8)
  - Classifier ensemble "magic number" (0.1 agreement bonus)

JOL MUKODO (megtartando mintak):
  - AttachmentProcessor._compute_quality_score(): 5-faktor sulyozott atlag — MINTA!
  - CalibratedClassifierCV: sklearn predict_proba — megbizhato
  - Invoice validator: szabaly-alapu (1.0 - buntetesek) — determinisztikus
```

---

## B3.5 FELADAT: Confidence Scoring Hardening + Review Routing

> **Gate:** Per-field confidence mukodik, routing bekotve (auto/review/reject), 15+ unit test PASS
> **Eszkozok:** `/dev-step`, `/new-test`, `/regression`
> **Lenyeg:** Megbizhato konfidencia szamitas + automatikus routing human review-ba

### Implementacios Lepesek

#### LEPES 1: Per-Field Confidence Calculator (UJ modul)

```
Hol: src/aiflow/engine/confidence.py (UJ fajl)

Cel: determinisztikus, per-mezo konfidencia szamitas dokumentum extrakciohoz.
Az AttachmentProcessor 5-faktor mintajat kell kovetni!

Meglevo minta (attachment_processor.py:232-303):
  _compute_quality_score() — 5 sulyozott faktor:
    text_density=0.25, word_coherence=0.25, table_quality=0.15,
    line_structure=0.20, content_length=0.15

Uj implementacio — FieldConfidenceCalculator:

  Per-mezo konfidencia (4 faktor, ossz. = 1.0):
    format_match (0.30): mezo-specifikus formatum illesztes
      - datum: YYYY-MM-DD regex → 1.0, "aprilis 15" → 0.7, ures → 0.0
      - adoszam: XXXXXXXX-X-XX regex → 1.0, 8+ szamjegy → 0.5, ures → 0.0
      - osszeg: szam format → 1.0, szoveg → 0.3, ures → 0.0
      - szoveg mezok: min. 2 karakter → 1.0, ures → 0.0

    regex_validation (0.25): mezo-specifikus regex
      - invoice_number: minta: [A-Z]{2,5}[-/]\d{4}[-/]\d{3,6}
      - tax_number: \d{8}-\d-\d{2}
      - bank_account: \d{8}-\d{8}(-\d{8})?
      - email: standard email regex
      - date: \d{4}-\d{2}-\d{2}

    cross_field_consistency (0.25): mezok kozti konzisztencia
      - netto + afa ≈ brutto (tolerance 1%) → 1.0, >5% elteres → 0.3
      - invoice_date <= fulfillment_date <= due_date → 1.0, nem → 0.5
      - vendor.tax_number prefix megegyezik a cim regioval → 1.0

    source_quality (0.20): forras minoseg
      - Docling + tiszta PDF → 1.0
      - Azure DI → 0.9
      - OCR/scan → 0.7
      - Keziras → 0.4
      - Ismeretlen → 0.5

  Document overall confidence:
    overall = weighted_mean(field_confidences) * structural_penalty
    structural_penalty: -0.15 / hianyzo kotelezo mezo (min 0.3)

  Pydantic modellek:
    FieldConfidence(field_name, value, confidence, factors)
    DocumentConfidence(overall, field_scores, structural_penalty, source_quality)

Unit tesztek (5):
  test_field_confidence_date_format()         — helyes/hibas datum → kulonbozo score
  test_field_confidence_tax_number()           — valid/invalid adoszam
  test_field_confidence_cross_field_amounts()  — netto+afa=brutto konzisztencia
  test_field_confidence_source_quality()       — parser tipus → minoseg score
  test_document_overall_confidence()           — structural penalty + weighted mean
```

#### LEPES 2: Confidence Router (UJ modul)

```
Hol: src/aiflow/engine/confidence_router.py (UJ fajl)

Cel: confidence alapjan automatikus routing: auto_approve / review / reject

RoutingDecision enum:
  AUTO_APPROVED = "auto_approved"
  SENT_TO_REVIEW = "sent_to_review"
  REJECTED_FOR_REVIEW = "rejected_for_review"

ConfidenceRoutingConfig (Pydantic):
  auto_approve_threshold: float = 0.90
  review_threshold: float = 0.70
  reject_threshold: float = 0.50

async def route_by_confidence(
    document_confidence: DocumentConfidence,
    config: ConfidenceRoutingConfig,
    review_service: HumanReviewService | None = None,
    entity_type: str = "extraction",
    entity_id: str = "",
    document_title: str = "",
) -> RoutingDecision:
    score = document_confidence.overall

    if score >= config.auto_approve_threshold:
        return RoutingDecision.AUTO_APPROVED

    elif score >= config.review_threshold:
        if review_service:
            low_fields = [f.field_name for f in document_confidence.field_scores if f.confidence < 0.70]
            await review_service.create_review(
                entity_type=entity_type,
                entity_id=entity_id,
                title=f"Review: {document_title}",
                priority="normal",
                metadata={"confidence": score, "low_confidence_fields": low_fields},
            )
        return RoutingDecision.SENT_TO_REVIEW

    else:
        if review_service:
            await review_service.create_review(
                entity_type=entity_type,
                entity_id=entity_id,
                title=f"LOW CONFIDENCE: {document_title}",
                priority="high",
                metadata={"confidence": score, "reason": "below_reject_threshold"},
            )
        return RoutingDecision.REJECTED_FOR_REVIEW

FONTOS: A review_service OPCIONALIS! Ha None, csak a routing decision-t adjuk vissza
        (routing logika teszt-ek NEM fuggnek PostgreSQL-tol).

Unit tesztek (5):
  test_route_auto_approved()             — score 0.95 → AUTO_APPROVED
  test_route_sent_to_review()            — score 0.80 → SENT_TO_REVIEW
  test_route_rejected_for_review()       — score 0.40 → REJECTED_FOR_REVIEW
  test_route_review_creates_review_item() — mock review_service.create_review hivva
  test_route_without_review_service()    — review_service=None → decision OK, no call
```

#### LEPES 3: Confidence Config YAML (Invoice Finder)

```
Hol: skills/invoice_finder/confidence_config.yaml (UJ fajl)

Tartalom:
  routing:
    auto_approve_threshold: 0.90
    review_threshold: 0.70
    reject_threshold: 0.50

  field_weights:
    invoice_number: 0.15
    invoice_date: 0.10
    due_date: 0.10
    vendor_name: 0.10
    vendor_tax_number: 0.10
    amount: 0.20          # penzugyi mezo magasabb suly!
    line_items: 0.15
    payment_method: 0.10

  source_quality_scores:
    docling_clean: 1.0
    azure_di: 0.9
    ocr_scan: 0.7
    handwriting: 0.4
    unknown: 0.5

  mandatory_fields:
    - invoice_number
    - invoice_date
    - vendor_name
    - amount

Unit tesztek (2):
  test_confidence_config_yaml_valid()   — YAML parse + kotelezp kulcsok
  test_confidence_config_thresholds()   — threshold ertekek logikaiak (reject < review < auto)
```

#### LEPES 4: BM25 Normalizalas Fix

```
Hol: src/aiflow/vectorstore/pgvector_store.py (MEGLEVO fajl — MODOSITAS)

Jelenlegi problema (sor 44-60):
  _bm25_score() — avg_dl=200.0 hardcoded, score NEM normalizalt [0,1]-be
  combined_score = 0.6*cosine + 0.4*BM25 → TULCSORDUHAT (>1.0)

Javitas:
  1. _bm25_score() vegere: score = min(score / (score + 1.0), 1.0)  # saturation normalization
  2. avg_dl parameter: ne 200.0 hardcoded, hanem config-olhato (default 200.0 marad)

Unit tesztek (3):
  test_bm25_score_normalized_range()    — eredmeny mindig [0.0, 1.0]
  test_bm25_combined_score_capped()     — 0.6*cos + 0.4*bm25 <= 1.0
  test_bm25_empty_query()               — ures query → 0.0
```

### Teszt Fajl Struktura (UJ fajlok)

```
tests/unit/engine/
  test_field_confidence.py              — per-field confidence (5 test)
  test_confidence_router.py             — routing logika (5 test)

tests/unit/pipeline/
  test_confidence_config.py             — YAML config validacio (2 test)

tests/unit/vectorstore/
  test_bm25_normalization.py            — BM25 fix (3 test)

Osszesen: 15 unit test (4 fajl)
```

---

## VEGREHAJTAS SORRENDJE

```
--- LEPES 1: Per-Field Confidence Calculator ---
/dev-step "B3.5.1 — FieldConfidenceCalculator + DocumentConfidence + 5 teszt"
  - src/aiflow/engine/confidence.py (UJ fajl)
  - FieldConfidence, DocumentConfidence Pydantic modellek
  - Per-mezo szamitas: format_match + regex_validation + cross_field + source_quality
  - Overall confidence: weighted mean + structural penalty
  - 5 unit test

--- LEPES 2: Confidence Router ---
/dev-step "B3.5.2 — ConfidenceRouter + RoutingDecision + 5 teszt"
  - src/aiflow/engine/confidence_router.py (UJ fajl)
  - RoutingDecision enum + ConfidenceRoutingConfig
  - route_by_confidence() async fuggveny
  - HumanReviewService integracio (opcionalis)
  - 5 unit test

--- LEPES 3: Confidence Config YAML ---
/dev-step "B3.5.3 — confidence_config.yaml + 2 teszt"
  - skills/invoice_finder/confidence_config.yaml (UJ)
  - YAML validacio tesztek
  - 2 unit test

--- LEPES 4: BM25 Normalizalas Fix ---
/dev-step "B3.5.4 — BM25 score normalizalas [0,1] + 3 teszt"
  - src/aiflow/vectorstore/pgvector_store.py (MODOSITAS)
  - Saturation normalization: score / (score + 1.0)
  - 3 unit test

--- SESSION LEZARAS ---
/lint-check → 0 error
/regression → ALL PASS (1352 + 15 = 1367+ unit test)
/update-plan → 58 progress B3.5 DONE
```

---

## KORNYEZET ELLENORZES

```bash
git branch --show-current                                    # → feature/v1.3.0-service-excellence
git log --oneline -3                                         # → aecce10, 86c7641, 372e08b
python -m pytest tests/unit/pipeline/test_invoice_field_extractor.py tests/unit/pipeline/test_payment_status_adapter.py tests/unit/pipeline/test_report_generator_adapter.py tests/unit/pipeline/test_invoice_notification.py -q 2>&1 | tail -1
                                                              # → 16 passed
.venv/Scripts/ruff check src/ tests/ 2>&1 | tail -1          # → All checks passed!
ls src/aiflow/pipeline/adapters/*.py | wc -l                  # → 21 adapter
ls skills/invoice_finder/prompts/*.yaml | wc -l               # → 6 prompt
ls src/aiflow/engine/*.py | wc -l                             # → 10 fajl (confidence.py + confidence_router.py meg NEM letezik)
```

---

## S26 TANULSAGAI (alkalmazando S27-ben!)

1. **Service nelkuli adapter pattern** — PaymentStatus + ReportGenerator adapter-ek NEM hasznalnak service-t, logika az adapter-ben van → ez a minta B3.5-ben is hasznalhato (ConfidenceCalculator nem service, hanem engine modul)
2. **Kulon fuggvenyek tesztelhetosege** — `_determine_payment_status()` es `_generate_markdown()` kulon fuggvenykent jol tesztelhetok → B3.5-ben is kulon fuggvenyek kellenek (pl. `_compute_field_confidence()`)
3. **Pydantic I/O mindenhol** — FieldConfidence + DocumentConfidence + RoutingDecision mind Pydantic/enum
4. **16 teszt > 15 minimum** — extra tesztek olcsoak, irj tobbet ha van ertelme
5. **Pre-existing test failure** — `test_rerank_fallback` HuggingFace model letoltes hiba NEM regresszio, ignore-olhato

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# Confidence scoring minta (KOVETENDO):
src/aiflow/tools/attachment_processor.py:232-303  — _compute_quality_score() 5-faktor minta

# HumanReviewService (routing celpontra):
src/aiflow/services/human_review/service.py       — create_review(), approve(), reject()

# Classifier ensemble confidence (meg nem kalibralt):
src/aiflow/services/classifier/service.py:235-270 — _ensemble() + magic number

# BM25 (javitando):
src/aiflow/vectorstore/pgvector_store.py:44-60    — _bm25_score() avg_dl=200 hardcoded

# Engine modullista (ide kerul a ket uj fajl):
src/aiflow/engine/                                — step.py, dag.py, runner.py, workflow.py, ...

# Invoice Finder modellek + promptok (B3.1 + B3.2):
skills/invoice_finder/models/__init__.py          — PaymentStatus, ReportResult (B3.2)
skills/invoice_finder/prompts/                    — 6 YAML prompt

# Teszt mintak:
tests/unit/pipeline/test_payment_status_adapter.py — adapter teszt (kulon fuggveny + async adapter)
tests/unit/pipeline/test_report_generator_adapter.py — kulon fuggveny tesztek (markdown, csv, summary)
```

---

## SPRINT B UTEMTERV

```
S19: B0   — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1 — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2 — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1 — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2 — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1 — DONE (372e08b) — Invoice Finder pipeline + email search + doc acquire (29 test)
S25: B3.2 — DONE (aecce10) — Invoice Finder: extract + payment + report + notification (16 test)
S26: B3.5 ← KOVETKEZO SESSION — Konfidencia scoring hardening + confidence→review routing
S27: B4.1 — Skill hardening: aszf_rag + email_intent
S28: B4.2 — Skill hardening: process_docs + invoice + cubix + diagram
S29: B5   — Spec writer + diagram pipeline + koltseg baseline
S30: B6   — UI Journey audit + 4 journey tervezes + navigacio redesign
S31: B7   — Verification Page v2 (bounding box, diff, per-field confidence szin)
S32: B8   — UI Journey implementacio (top 3 journey + dark mode)
S33: B9   — Docker containerization + UI pipeline trigger + deploy teszt
S34: B10  — POST-AUDIT + javitasok
S35: B11  — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (emlekeztetok)

- **`/dev-step` HASZNALANDÓ** — minden logikai blokk kulon dev-step
- **Unit test = mock** — ez NEM integration test! Pure logika tesztelese, HumanReviewService MOCK.
- **Engine modul, NEM service** — confidence.py es confidence_router.py az `src/aiflow/engine/`-be kerulnek
- **HumanReviewService integracio OPCIONALIS** — route_by_confidence() review_service=None-t is elfogad
- **BM25 modositas OVATOSAN** — a pgvector_store.py MEGLEVO fajl, csak a BM25 normalizalast add hozza
- **Async-first** — route_by_confidence() async (review_service async)
- **Pydantic modellek** — FieldConfidence, DocumentConfidence, ConfidenceRoutingConfig, RoutingDecision
- **structlog** — `logger = structlog.get_logger(__name__)`

---

## B3.5 GATE CHECKLIST

```
[ ] src/aiflow/engine/confidence.py letezik (FieldConfidenceCalculator + DocumentConfidence)
[ ] src/aiflow/engine/confidence_router.py letezik (route_by_confidence + RoutingDecision)
[ ] skills/invoice_finder/confidence_config.yaml letezik (routing thresholds + field weights)
[ ] src/aiflow/vectorstore/pgvector_store.py BM25 normalizalt [0,1]
[ ] Per-field confidence: 4-faktor szamitas (format + regex + cross-field + source)
[ ] Overall confidence: weighted mean + structural penalty
[ ] Routing: auto_approve >= 0.90, review >= 0.70, reject < 0.50
[ ] HumanReviewService.create_review() hivva review/reject eseten (ha service adott)
[ ] 15+ unit test PASS (4 fajl)
[ ] /lint-check → 0 error
[ ] /regression → ALL PASS (1367+ unit test)
[ ] Nincs regresszio a meglevo tesztekben
```
