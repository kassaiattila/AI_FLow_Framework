# AIFlow Service Generalizalas - Reszletes Atalakitasi Terv

**Datum:** 2026-04-01
**Alapja:** Backend audit (endpoint vs dokumentacio), dead code analzis, skill pipeline analzis, felhasznaloi vizioA
**Kiindulo verzio:** `v0.9.0-stable` (rollback pont)
**Status:** TERVEZES

---

## 1. Jelenlegi Helyzet Osszefoglalasa

### 1.1 Backend Endpoint Audit Eredmenye

| Kategoria | Implementalt | Hianyzo | Megjegyzes |
|-----------|-------------|---------|------------|
| Health | 3/3 | — | Teljes, valos DB check |
| Documents | 6/5+ | — | Teljes + SSE stream |
| Emails | 3/3 | — | Teljes, DB + JSON fallback |
| Runs | 2/7 | cancel, result, DLQ (5 db) | Csak list + detail |
| Costs | 1/1 | — | Teljes, PostgreSQL aggregacio |
| Feedback | 2/2 | — | Teljes |
| Auth | 2/4 | refresh, api-keys | JWT login + /me van |
| Workflows | 3/5 | docs, replay | Placeholder adat |
| Skills API | 1/5 | detail, install, delete, ingest | Csak list (hardcoded) |
| Prompts | 0/6 | MIND | Egyaltalan nem implementalt |
| Evaluation | 0/3 | MIND | Egyaltalan nem implementalt |
| Scheduling | 0/4 | MIND | Egyaltalan nem implementalt |
| Admin | 0/8+ | MIND | Egyaltalan nem implementalt |
| **Osszesen** | **29/50+** | **~25 endpoint** | **58% lefedettse** |

### 1.2 Dead Code Audit

- **Halott kod:** 0 fajl (nincs felesleg)
- **__all__ export hianyzo:** 7 modul (core, engine, models, documents, ingestion, state, observability)
- **Teszt hianyzo:** tools/, skill_system/ — 0 teszt fajl
- **Backward-compat stub:** 4 db contrib/ (szandekos, dokumentalt)
- **Stub skill:** qbpp_test_automation (nincs __main__.py)

### 1.3 Skill Pipeline Osszehasonlitas

| Skill | Lepesek | Kulso fuggoseg | Altalanosithatosag |
|-------|---------|----------------|---------------------|
| process_documentation | 5 (classify→elaborate→extract→review→generate) | gpt-4o, Kroki, DrawIO | Diagram generator kulonvalaszthato |
| aszf_rag_chat | 6+6 (ingest + query) | pgvector, gpt-4o, embeddings | Teljes RAG engine kulonvalaszthato |
| email_intent_processor | 7 (parse→attach→classify→entity→priority→route→log) | sklearn, gpt-4o-mini, Kafka | Classifier + Entity extractor kulonvalaszthato |
| invoice_processor | 6 (parse→classify→extract→validate→store→export) | Docling, gpt-4o, PostgreSQL | Document extractor altalanosithatao |
| cubix_course_capture | 6 (probe→extract→chunk→STT→merge→structure) | ffmpeg, Whisper, Playwright | Media processor + RPA kulonvalaszthato |
| qbpp_test_automation | 0 (STUB) | Playwright (tervezett) | Stub → RPA service-be olvaszthato |

---

## 2. Cel: Altalanos Szolgaltatasok Architekturaja

### 2.1 Vizioio

A jelenlegi projekt-specifikus skill-eket **ujrahasznosithaato, konfiguralhato szolgaltatasokka** alakitjuk:

```
JELENLEGI (projekt-specifikus):
  cubix_course_capture → csak Cubix oldalhoz
  aszf_rag_chat → csak ASZF dokumentumokhoz
  email_intent_processor → fix intent schema
  invoice_processor → csak szamlakhoz

UJ (altalanos szolgaltatasok):
  RPA Browser Service → barmilyen weboldalhoz, parameterezheto
  Media Processor → barmilyen video/audio → szoveg
  RAG Engine → barmilyen dokumentum kollekcio + chat
  Email Connector + Intent Classifier → barmilyen postafiaok, konfiguralhato intentek
  Document Extractor → barmilyen dokumentum tipus + adatpontok
  Diagram Generator → barmilyen strukturalt adat → diagram
```

### 2.2 Szolgaltatas Terkep

```
┌─────────────────────────────────────────────────────────┐
│                    CORE SERVICES                         │
├──────────────┬──────────────┬──────────────┬────────────┤
│ LLM Gateway  │ Document     │ Vector Store │ Schema     │
│ (ModelClient │ Parser       │ (pgvector    │ Registry   │
│  + prompts)  │ (Docling)    │  + hybrid)   │ (JSON)     │
├──────────────┴──────────────┴──────────────┴────────────┤
│                  BUILDING BLOCKS                         │
├──────────────┬──────────────┬──────────────┬────────────┤
│ Structured   │ Classifier   │ Ingestion    │ Validation │
│ Extractor    │ (ML + LLM    │ Pipeline     │ Service    │
│ (text→model) │  hybrid)     │ (load→chunk  │ (math,date │
│              │              │  →embed→store)│  ,ref)     │
├──────────────┴──────────────┴──────────────┴────────────┤
│                 DOMAIN SERVICES                          │
├──────────────┬──────────────┬──────────────┬────────────┤
│ Email        │ Document     │ RAG Engine   │ RPA Browser│
│ Connector    │ Extractor    │ (ingest +    │ Service    │
│ (O365/Gmail/ │ (barmilyen   │  query +     │ (Playwright│
│  IMAP param) │  doc tipus)  │  chat UI)    │  + Shell)  │
├──────────────┼──────────────┼──────────────┼────────────┤
│ Media        │ Diagram      │ Export       │ Notif.     │
│ Processor    │ Generator    │ Service      │ Service    │
│ (video→text) │ (DrawIO/SVG) │ (CSV/Excel/  │ (email,    │
│              │              │  JSON/PDF)   │  webhook)  │
├──────────────┴──────────────┴──────────────┴────────────┤
│                SKILL INTEGRACIOK                         │
│  Cubix = RPA Browser + Media Processor + RAG Engine      │
│  Email = Email Connector + Classifier + Entity Extractor │
│  Invoice = Document Extractor + Validation + Export      │
│  ASZF RAG = Ingestion Pipeline + RAG Engine              │
│  ProcessDoc = Structured Extractor + Diagram Generator   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Reszletes Szolgaltatas Tervek

### 3.1 Email Connector Service

**Cel:** Barmilyen postafiaok paramterezheto csatlakozasa es email letoltese.

**Jelenlegi helyzet:** `skills/email_intent_processor/tools/` tartalmaz IMAP + Graph API fetchert, de fix konfiguracioval.

**Uj funkcionalitas:**

```yaml
# Konfiguracio pelda
email_connector:
  provider: "o365"  # o365 | gmail | imap | outlook_local
  credentials:
    tenant_id: "..."
    client_id: "..."
    client_secret: "..."  # vagy: oauth_token_path
  mailbox: "info@company.hu"
  filters:
    last_days: 30           # utolso 30 nap
    folder: "INBOX"         # vagy: "INBOX/Szamlak"
    unread_only: false
    subject_contains: ""    # opcionalis szuro
    from_contains: ""       # opcionalis szuro
  output:
    format: "structured"    # structured | raw_eml | both
    include_attachments: true
    attachment_dir: "./downloads"
```

**API Endpoint:**
```
POST /api/v1/services/email-connector/fetch
Body: { config: EmailConnectorConfig }
Response: { emails: EmailMessage[], count: number, source: "o365"|"gmail"|"imap" }

POST /api/v1/services/email-connector/test
Body: { config: EmailConnectorConfig }
Response: { success: boolean, message: string, sample_count: number }
```

**Implementacios lepesek:**
1. Kiemelni `email_fetcher_imap.py` + `email_fetcher_graph.py` → `src/aiflow/services/email_connector/`
2. Gmail API fetcher hozzaadasa (OAuth2)
3. Lokalis Outlook fetcher (win32com vagy EWS)
4. Egyseges `EmailConnectorFactory` → provider alapjan valaszt
5. Filter rendszer (datum, mappa, targy, felado)
6. Admin UI: "Email Connector" konfiguracios oldal

**Fuggosegek:** O365 SDK, google-api-python-client, imaplib (stdlib)

---

### 3.2 Intent Classifier Service (Altalanositott)

**Cel:** Barmilyen szoveg osztalyozasa konfiguralhato intent schemak alapjan.

**Jelenlegi helyzet:** `email_intent_processor` tartalmaz hibrid sklearn+LLM classifier-t, de email-specifikus.

**Uj funkcionalitas:**

```yaml
# Konfiguracio pelda
classifier:
  name: "support-ticket-classifier"
  strategy: "hybrid"         # hybrid | llm_only | ml_only
  ml_model: "tfidf_linearsvc" # opcionalis
  llm_model: "openai/gpt-4o-mini"
  confidence_threshold: 0.6  # ml alatti → LLM fallback
  intents:
    - name: "billing_question"
      description: "Szamlazassal kapcsolatos kerdes"
      examples: ["Mikor erkezik a szamla?", "Nem kaptam meg a szamlat"]
    - name: "technical_issue"
      description: "Technikai problema bejelentes"
      examples: ["Nem mukodik a rendszer", "Hiba uzenet jelent meg"]
    - name: "general_inquiry"
      description: "Altalanos kerdes"
      examples: ["Mik a nyitvatartasi idok?"]
```

**API Endpoint:**
```
POST /api/v1/services/classifier/classify
Body: { text: string, config_name: string }
Response: { intent: string, confidence: number, method: "ml"|"llm", alternatives: [] }

POST /api/v1/services/classifier/train
Body: { config_name: string, training_data: [{text, intent}] }
Response: { model_path: string, accuracy: number, f1_score: number }
```

---

### 3.3 Document Extractor Service (Altalanositott)

**Cel:** Barmilyen dokumentum tipusbol konfiguralhato adatpontok kinyerase.

**Jelenlegi helyzet:** `invoice_processor` szamla-specifikus; fix mezo definiciok.

**Uj funkcionalitas:**

```yaml
# Konfiguracio pelda - Szerzodes
document_extractor:
  name: "contract-extractor"
  document_type: "contract"
  parser: "docling"          # docling | pypdfium2 | azure_di
  extraction_model: "openai/gpt-4o"
  fields:
    - name: "parties"
      type: "list[object]"
      description: "Szerzodo felek nevei es cimei"
      required: true
    - name: "effective_date"
      type: "date"
      description: "Hatalyba lepes datuma"
      required: true
    - name: "termination_date"
      type: "date"
      description: "Lejarat datuma"
      required: false
    - name: "contract_value"
      type: "number"
      description: "Szerzodes erteke"
      required: false
    - name: "clauses"
      type: "list[object]"
      description: "Fo pontok/klauuzulak"
      required: false
  validation_rules:
    - "effective_date < termination_date"
    - "contract_value >= 0"
  output_formats: ["json", "csv", "excel"]
```

**API Endpoint:**
```
POST /api/v1/services/document-extractor/extract
Body: FormData { file: PDF, config_name: string }
Response: SSE stream { step_start, step_done, complete(extracted_data) }

GET /api/v1/services/document-extractor/configs
Response: { configs: [{ name, document_type, field_count }] }

POST /api/v1/services/document-extractor/configs
Body: { DocumentExtractorConfig }
Response: { created: true, name: string }
```

**Implementacios lepesek:**
1. `invoice_processor` pipeline altalanositasa → mezo definiciok JSON schema-bol
2. Prompt template parameterezheto (document_type + fields → Jinja2)
3. Validation engine altalanositasa (szabaly-alapu)
4. Verification UI altalanositasa (nem csak szamla, hanem barmilyen doc)
5. Admin UI: "Document Types" konfiguracios oldal

---

### 3.4 RAG Engine Service

**Cel:** Dokumentum feltoltes, feldolgozas, es chat — cserelheto tudasbazissal.

**Jelenlegi helyzet:** `aszf_rag_chat` fix ASZF dokumentumokra van bekotve.

**Uj funkcionalitas:**

```yaml
# Konfiguracio pelda
rag_engine:
  name: "hr-policy-chat"
  collection: "hr_policies_2024"
  language: "hu"

  ingestion:
    supported_formats: ["pdf", "docx", "txt", "md", "xlsx"]
    chunk_size: 512
    chunk_overlap: 64
    embedding_model: "openai/text-embedding-3-small"

  query:
    search_model: "hybrid"    # hybrid | semantic | bm25
    search_results: 5
    answer_model: "openai/gpt-4o"
    citation_enabled: true
    hallucination_check: true

  chat_ui:
    title: "HR Szabalyzat Asszisztens"
    welcome_message: "Kerdezhetsz a HR szabalyzatokrol!"
    suggested_questions:
      - "Mi a szabadsag kiadasi rendje?"
      - "Hogyan kell tavollet kerelmet beadni?"
    role: "expert"            # baseline | expert | mentor
```

**API Endpoint:**
```
POST /api/v1/services/rag/collections
Body: { name, description, config: RAGConfig }
Response: { collection_id, name }

POST /api/v1/services/rag/collections/{id}/ingest
Body: FormData { files: [PDF, DOCX, ...] }
Response: SSE stream { parsing, chunking, embedding, storing, done(chunk_count) }

POST /api/v1/services/rag/collections/{id}/query
Body: { question: string, role?: string }
Response: SSE stream { rewriting, searching, generating, citing, answer(text, citations) }

GET /api/v1/services/rag/collections/{id}/stats
Response: { chunk_count, doc_count, last_updated, avg_confidence }

DELETE /api/v1/services/rag/collections/{id}
Response: { deleted: true }
```

**Chat UI:** Allandao felulket, ahol:
- Bal oldal: dokumentum kollekcio valaszto + feltoltes
- Jobb oldal: chat interface (streaming valasz, citaciok, forrasok)
- A mögötte levo tudas cserelheto a kollekcio valasztassal

---

### 3.5 RPA Browser Service

**Cel:** Paramterezheto bongeszo automatizalas (kattintas, navigalas, adat gyujtes).

**Jelenlegi helyzet:** `cubix_course_capture` Playwright-ot hasznal, de Cubix-specifikus login + navigacio.

**Uj funkcionalitas:**

```yaml
# Konfiguracio pelda - Altalanos web scraping
rpa_browser:
  name: "course-downloader"
  browser: "chromium"
  headless: true

  steps:
    - action: "navigate"
      url: "https://learning.example.com/login"
    - action: "fill"
      selector: "#username"
      value: "{{ credentials.username }}"
    - action: "fill"
      selector: "#password"
      value: "{{ credentials.password }}"
    - action: "click"
      selector: "button[type=submit]"
    - action: "wait"
      selector: ".dashboard"
      timeout: 10000
    - action: "collect_links"
      selector: "a.video-link"
      output: "video_urls"
    - action: "download_each"
      urls: "{{ video_urls }}"
      output_dir: "./downloads"

  error_handling:
    screenshot_on_failure: true
    max_retries: 3
    retry_delay_ms: 2000
```

**API Endpoint:**
```
POST /api/v1/services/rpa/execute
Body: { config_name: string, variables: {} }
Response: SSE stream { step_start, step_done, screenshot?, complete(results) }

POST /api/v1/services/rpa/record
Body: { url: string }
Response: { recording_id, ws_url }  (WebSocket a browser stream-hez)
```

---

### 3.6 Media Processor Service

**Cel:** Video/audio → szoveg pipeline (kulonvalasztva az RPA-tol).

**Jelenlegi helyzet:** `cubix_course_capture` tartalmaz ffmpeg + Whisper pipeline-t.

**Uj funkcionalitas:**

```yaml
media_processor:
  name: "meeting-transcriber"
  input_formats: ["mp4", "mkv", "m4a", "mp3", "wav"]

  pipeline:
    - step: "probe"           # ffprobe metadata
    - step: "extract_audio"   # ffmpeg → wav/m4a
      options:
        sample_rate: 16000
        channels: 1
    - step: "chunk"           # split large files
      options:
        chunk_duration_seconds: 300
    - step: "transcribe"      # STT
      provider: "openai_whisper"  # openai_whisper | azure_speech | local_whisper
      language: "hu"
    - step: "merge"           # timestamp merge + dedup
    - step: "structure"       # LLM → fejezetek, temak, osszefoglalas
      options:
        output_format: "chapters"  # chapters | summary | full
```

**API Endpoint:**
```
POST /api/v1/services/media/process
Body: FormData { file: video/audio, config_name: string }
Response: SSE stream { probing, extracting, chunking, transcribing(N/M), merging, structuring, complete(transcript) }
```

---

### 3.7 Diagram Generator Service

**Cel:** Strukturalt adat → tobbfele diagram formatum.

**Jelenlegi helyzet:** `process_documentation` tartalmaz DrawIO builder + Mermaid + Kroki exportert.

```
POST /api/v1/services/diagrams/generate
Body: { input_text: string, diagram_type: "bpmn"|"flowchart"|"sequence"|"mindmap" }
Response: { formats: { drawio: "...", mermaid: "...", svg: "base64..." } }
```

---

## 4. Implementacios Fazisok

### Fazis 1: Alapozas (1-2 het)
**Cel:** Service infrastruktura + legertekesebb szolgaltatasok

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 1.1 | `src/aiflow/services/` konyvtar letrehozasa | Uj | 1 ora |
| 1.2 | Service base class + registry | `services/base.py`, `services/registry.py` | 4 ora |
| 1.3 | Service config YAML loader | `services/config.py` | 2 ora |
| 1.4 | API router: `/api/v1/services/` | `api/v1/services.py` | 4 ora |
| 1.5 | **Email Connector** kiemelese + altalanositasa | `services/email_connector/` | 8 ora |
| 1.6 | **Document Extractor** kiemelese + altalanositasa | `services/document_extractor/` | 12 ora |
| 1.7 | Admin UI: Service konfiguracios oldalak | `aiflow-admin/src/pages/Services*.tsx` | 8 ora |

**Vegeredmeny:** Ket mukodo altalanos szolgaltatas, Admin UI-bol konfiguralhatao.

### Fazis 2: RAG + Classifier (2-3 het)
**Cel:** RAG Engine es Intent Classifier mint onallo szolgaltatas

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 2.1 | **RAG Engine** kiemelese aszf_rag_chat-bol | `services/rag_engine/` | 12 ora |
| 2.2 | Multi-collection tamogatas | vectorstore modul bovites | 6 ora |
| 2.3 | RAG Chat UI altalanositasa | `aiflow-admin/src/pages/RagChat.tsx` | 8 ora |
| 2.4 | **Intent Classifier** kiemelese | `services/classifier/` | 8 ora |
| 2.5 | Hybrid ML + LLM classifier config | sklearn + LiteLLM | 6 ora |
| 2.6 | Email Connector + Classifier integracio | pipeline osszekapcsolas | 4 ora |

**Vegeredmeny:** RAG chat barmilyen dokumentum kollekciovaol. Email intent barmilyen postafaikkal.

### Fazis 3: RPA + Media (3-4 het)
**Cel:** Browser automatizalas es media feldolgozas kulonvalasztasa

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 3.1 | **RPA Browser Service** kiemelese | `services/rpa_browser/` | 10 ora |
| 3.2 | YAML-alapu step konfiguracio | action registry | 6 ora |
| 3.3 | **Media Processor** kiemelese | `services/media_processor/` | 8 ora |
| 3.4 | Whisper provider valaszto (OpenAI / Azure / local) | provider factory | 4 ora |
| 3.5 | Cubix skill atriaas → RPA + Media + RAG compose | skill refactor | 6 ora |

**Vegeredmeny:** RPA es media feldolgozas kulonvalasztva, ujrahasznosithatoan.

### Fazis 4: Backend Stabilitas (4-5 het)
**Cel:** Hianyzo endpointok, tesztek, __all__ exports

| # | Feladat | Prioritas |
|---|---------|-----------|
| 4.1 | Auth: `/refresh` + `/api-keys` implementalas | Magas |
| 4.2 | Runs: cancel, result, DLQ endpointok | Magas |
| 4.3 | Skills API: detail, manifest loading | Magas |
| 4.4 | `__all__` export hozzaadasa 7 modulhoz | Kozepes |
| 4.5 | tools/ + skill_system/ tesztek irasa | Kozepes |
| 4.6 | Prompts API: list, sync, promote | Alacsony |
| 4.7 | Scheduling API alapok | Alacsony |

---

## 5. Migraciaos Strategia

### 5.1 Visszafele Kompatibilitas

A jelenlegi skill-ek **tovabbra is mukodnek** a regi modon:
```bash
# Regi mod (tovabbra is tamogatott):
python -m skills.invoice_processor --input file.pdf --output ./out

# Uj mod (service API):
POST /api/v1/services/document-extractor/extract
```

### 5.2 Skill → Service Mapping

```python
# skills/invoice_processor/__init__.py — uj verzio
from aiflow.services.document_extractor import DocumentExtractorService

# A regi skill a service-t hasznalja belul:
_extractor = DocumentExtractorService.from_config("invoice")

# A pipeline lepesek delegalnak:
async def extract_invoice_data(data):
    return await _extractor.extract(data)
```

### 5.3 Git Verziozas

```
v0.9.0-stable     ← Jelenlegi stabil (rollback pont)
v0.10.0-services  ← Fazis 1 utan (Email Connector + Document Extractor)
v0.11.0-rag       ← Fazis 2 utan (RAG Engine + Classifier)
v0.12.0-rpa       ← Fazis 3 utan (RPA + Media)
v1.0.0-rc1        ← Fazis 4 utan (teljes backend stabilitas)
```

Minden fazis vegen `git tag` — barmikor visszaallithato.

---

## 6. Konyvtar Struktura (Tervezett)

```
src/aiflow/services/               # ← UJ
  __init__.py                       # ServiceRegistry
  base.py                           # BaseService ABC
  config.py                         # YAML config loader

  email_connector/
    __init__.py
    factory.py                      # Provider factory (O365/Gmail/IMAP)
    providers/
      imap_provider.py
      o365_provider.py
      gmail_provider.py
      outlook_local_provider.py
    models.py                       # EmailMessage, EmailFilter pydantic

  document_extractor/
    __init__.py
    extractor.py                    # Altalanos extraction pipeline
    field_schema.py                 # Mezo definicio loader
    validators.py                   # Altalanos validacioas szabalyok
    templates/                      # Prompt template-ek doc tipusonkent
      invoice.yaml
      contract.yaml
      receipt.yaml

  rag_engine/
    __init__.py
    engine.py                       # Ingest + Query orchestrator
    collections.py                  # Multi-collection manager

  classifier/
    __init__.py
    hybrid.py                       # ML + LLM hybrid
    ml_backend.py                   # sklearn wrapper

  rpa_browser/
    __init__.py
    executor.py                     # YAML step executor
    actions/                        # navigate, fill, click, collect, download

  media_processor/
    __init__.py
    pipeline.py                     # probe → extract → chunk → STT → merge
    providers/                      # whisper_openai, whisper_local, azure_speech

  diagram_generator/
    __init__.py
    generator.py                    # Multi-format export
    builders/                       # drawio, mermaid, kroki
```

---

## 7. Sikerkritieriumok

### Fazis 1 utan:
- [ ] Email Connector: O365 + IMAP mukodik parameterezhetoen
- [ ] Document Extractor: szamla + 1 masik doc tipus (pl. szerzodes)
- [ ] Admin UI-ban konfiguralhato mindketto
- [ ] Regi skill-ek tovabbra is mukodnek (backward compat)

### Fazis 2 utan:
- [ ] RAG Chat: uj kollekcio letrehozasa + dokumentum feltoltes + kerdezes
- [ ] Chat UI: kollekcio valaszto, streaming valasz, citaciok
- [ ] Intent Classifier: email + 1 masik kontextus (pl. support ticket)
- [ ] Email Connector + Classifier end-to-end mukodik

### Fazis 3 utan:
- [ ] RPA: YAML konfiguracioval bongeszo automatizalas
- [ ] Media: video → szoveg barmilyen formatumbol
- [ ] Cubix skill: RPA + Media + RAG Engine compose

### Fazis 4 utan:
- [ ] 90%+ endpoint lefedettse (45+ / 50)
- [ ] __all__ export minden modulban
- [ ] tools/ + skill_system/ tesztek ≥ 80% coverage
- [ ] Auth refresh + API key mukodik

---

## 8. Kockazatok es Mitigacio

| Kockazar | Valoszinuseg | Hatas | Mitigacio |
|----------|-------------|-------|-----------|
| Backward compat tores | Kozepes | Magas | Skill-ek belul hivjak a service-t, kulso API valtozatlan |
| LLM koltseg novekedes | Alacsony | Kozepes | Koltseg tracking (mar van), budget limitek |
| Docling lassusag | Magas | Kozepes | pypdfium2 fallback, cache layer |
| pgvector skalazas | Alacsony | Magas | HNSW index, collection partitioning |
| OAuth2 token lejarat | Kozepes | Kozepes | Auto-refresh, retry logic |

---

## Hivatkozasok

- `01_PLAN/22_API_SPECIFICATION.md` — Eredeti API specifikacio
- `01_PLAN/28_MODULAR_DEPLOYMENT.md` — Multi-customer instance architektura
- `01_PLAN/29_OPTIMIZATION_PLAN.md` — Korabbi optimalizacios lepesek
- `01_PLAN/30_RAG_PRODUCTION_PLAN.md` — RAG pipeline checklist
- `v0.9.0-stable` git tag — Rollback pont
