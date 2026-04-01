# AIFlow Service Generalizalas - Reszletes Atalakitasi Terv

**Datum:** 2026-04-01
**Alapja:** Backend audit (endpoint vs dokumentacio), dead code analzis, skill pipeline analzis, felhasznaloi vizioA
**Kiindulo verzio:** `v0.9.0-stable` (rollback pont)
**Status:** TERVEZES

> **Elozmeny:** Az eredeti framework implementacio (Phase 1-7, Het 1-22, ld. `04_IMPLEMENTATION_PHASES.md`) **KESZ**.
> A `src/aiflow/` framework mag teljes egeszeben implementalva lett (v0.1.0 → v0.9.0-stable).
> Ez a terv (Fazis 0-4) egy **UJ, onallo fejezet**: a skill-specifikus kodot altalanos, konfiguralhato szolgaltatasokka alakitjuk.
> A ket fazis-rendszer fuggetlen: Phase 1-7 = framework mag, Fazis 0-4 = service generalizacio.

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

## 4. Infrastruktura Epitokockak (Architektura Audit Alapjan)

Az architektura audit a korabbi tervdokumentumok (01-30) es a valos implementacio osszevetese alapjan
**15 hianyzo infrastruktura komponenst** azonositott. Ezek a domain szolgaltatasok (3.1-3.7) ELENGEDHETETLEN
alapjai — nelkuluk a szolgaltatasok nem uzemeltethetoak megbizhatoan.

### 4.1 Cache Layer (Kritikus — LLM + Embedding + Vector)

**Statusz:** 30_RAG_PRODUCTION_PLAN.md emliti, de nincs implementalas.
**Hatas:** 20-40% LLM koltseg csokkenes + 10x gyorsabb RAG valasz ismetelt kerdesekre.

```
src/aiflow/services/cache/
  __init__.py
  embedding_cache.py        # Redis: text_hash → embedding vector
  llm_response_cache.py     # Redis: prompt_hash+input_hash → response
  vector_query_cache.py     # Redis: query_embedding_hash → top-K results
  invalidation.py           # Collection-alapu invalidacio (ingest utan)
```

**Konfiguracio:**
```yaml
cache:
  backend: "redis"           # redis | memory (teszthez)
  embedding:
    ttl_hours: 168           # 1 het
    max_entries: 100000
  llm_response:
    ttl_hours: 24            # ismetlodo kerdesekre
    scope: "per_collection"  # kollekcio valtozaskor invalidalodik
  vector_query:
    ttl_hours: 1             # rovid, mert ingest valtoztatja
```

**API:**
```
GET  /api/v1/admin/cache/stats       → { embedding_hits, llm_hits, vector_hits, memory_mb }
POST /api/v1/admin/cache/invalidate  → { scope: "collection:hr_policies" }
```

### 4.2 Event Bus + Notification Service

**Statusz:** 09_MIDDLEWARE_INTEGRATION.md definialt MessageBroker ABC-t, de nincs bekotes.
**Hatas:** Service-ek kozotti kommunikacio, alertek, webhook triggerek.

```
src/aiflow/services/events/
  __init__.py
  bus.py                     # EventBus (publish/subscribe)
  types.py                   # Tipizalt esemenyek (Pydantic)
  consumers.py               # Event handler registry

src/aiflow/services/notifications/
  __init__.py
  service.py                 # NotificationService
  channels/
    email_channel.py         # SMTP
    slack_channel.py         # Slack webhook
    webhook_channel.py       # Altalanos HTTP webhook
    teams_channel.py         # MS Teams webhook
```

**Esemeny tipusok:**
```python
class EventTypes:
    WORKFLOW_STARTED = "workflow.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    QUALITY_GATE_FAILED = "quality.gate_failed"
    BUDGET_ALERT = "budget.threshold_reached"     # 50%, 80%, 100%
    HUMAN_REVIEW_NEEDED = "human.review_required"
    COLLECTION_INGESTED = "rag.collection_ingested"
    SERVICE_HEALTH_DEGRADED = "service.health_degraded"
```

**API:**
```
POST /api/v1/services/notifications/channels       → CRUD notification csatorna
POST /api/v1/services/notifications/rules           → Event → Channel mapping
POST /api/v1/services/events/publish                → Manualis esemeny kuldes
GET  /api/v1/services/events/log?last=100           → Esemeny naplo
```

### 4.3 Config Versioning & Rollback

**Statusz:** 28_MODULAR_DEPLOYMENT.md definialt instance YAML-t, de nincs verziozas.
**Hatas:** Barmilyen service config visszaallithato, audit trail.

```
src/aiflow/services/config/
  __init__.py
  versioning.py              # Config version CRUD
  diff.py                    # Config diff keszites
  validation.py              # Pre-deploy schema validacio
```

**DB tabla:** `service_config_versions`
```sql
CREATE TABLE service_config_versions (
    id UUID PRIMARY KEY,
    service_instance_id UUID REFERENCES skill_instances(id),
    version INTEGER NOT NULL,
    config_jsonb JSONB NOT NULL,
    deployed_at TIMESTAMPTZ,
    deployed_by VARCHAR(100),
    is_active BOOLEAN DEFAULT false,
    change_description TEXT,
    UNIQUE(service_instance_id, version)
);
```

**API:**
```
GET  /api/v1/services/{id}/config/versions          → Verziok listaja
GET  /api/v1/services/{id}/config/diff/{v1}/{v2}    → Ket verzio kozotti kulonbseg
POST /api/v1/services/{id}/config/rollback/{version} → Visszaallas korabbi verziora
POST /api/v1/services/{id}/config/deploy             → Uj config deploy (uj verzio)
```

### 4.4 Health Monitoring per Service

**Statusz:** `/health` endpoint letezik globalis szinten, de service-enkent nincs.
**Hatas:** Degradalt szolgaltatas automatikus detektalasa + alertek.

```
src/aiflow/services/monitoring/
  __init__.py
  health_checker.py          # Periodikus health check (dependency-nkent)
  metrics_collector.py       # P50/P95/P99 latency, success rate
  dashboard_data.py          # Admin UI szamara aggregalt metrikak
```

**Fuggoseg checkek per service:**
```yaml
health_checks:
  email_connector:
    - type: "smtp_connect"
      target: "{{ config.smtp_host }}:{{ config.smtp_port }}"
      timeout_ms: 5000
    - type: "oauth_token_valid"
      target: "{{ config.oauth_token }}"
  rag_engine:
    - type: "pgvector_ping"
    - type: "embedding_model_available"
      model: "openai/text-embedding-3-small"
    - type: "collection_non_empty"
      collection: "{{ config.collection }}"
  document_extractor:
    - type: "docling_import"
    - type: "llm_model_available"
      model: "openai/gpt-4o"
```

**API:**
```
GET /api/v1/services/{id}/health       → { status, checks: [{name, status, latency_ms}] }
GET /api/v1/services/{id}/metrics      → { p50_ms, p95_ms, success_rate, runs_24h }
GET /api/v1/admin/services/dashboard   → Osszes service osszesitett allapota
```

### 4.5 Rate Limiting & Cost Budget

**Statusz:** 09_MIDDLEWARE_INTEGRATION.md emliti a back-pressure-t, de nincs szolgaltatas szintu rate limit.
**Hatas:** LLM koltseg kontroll, fair use per tenant.

```
src/aiflow/services/rate_limiter/
  __init__.py
  limiter.py                 # Redis sliding window rate limiter
  budget.py                  # Koltseg budget allokacio + enforcement
  cost_optimizer.py          # Minta-alapu koltseg optimalizalasi javaslatok
```

**Tobbszintu budget:**
```yaml
budgets:
  team_level:
    monthly_usd: 500
    alert_at: [50, 80, 100]   # % kuldjon alertet
    enforcement: "soft"        # soft=alert | hard=reject
  service_instance_level:
    daily_usd: 20
    enforcement: "hard"        # tullepes eseten elutasit
  per_run_level:
    max_usd: 5                 # egy futtatas max koltsege
```

**API:**
```
GET  /api/v1/admin/budgets                → Osszes budget allapot
POST /api/v1/admin/budgets/{team_id}      → Budget allokacio modositas
GET  /api/v1/services/{id}/cost/forecast  → Becsult havi koltseg (trend alapjan)
POST /api/v1/services/cost-optimizer/analyze → Koltseg optimalizalasi javaslatok
```

### 4.6 Retry & Circuit Breaker

**Statusz:** 01_ARCHITECTURE.md definialt RetryPolicy ABC + CircuitBreakerOpenError, de nincs kozponti kezeles.

```
src/aiflow/services/resilience/
  __init__.py
  retry.py                   # Konfiguralhato retry (exponential backoff + jitter)
  circuit_breaker.py         # Per-fuggoseg circuit breaker (closed→open→half-open)
  fallback.py                # Fallback strategiak (cache, default, degraded)
```

**Konfiguracio:**
```yaml
resilience:
  llm_calls:
    retry:
      max_attempts: 3
      backoff: "exponential"   # linear | exponential | decorrelated_jitter
      base_delay_ms: 1000
    circuit_breaker:
      failure_threshold: 5     # 5 egymas utani hiba → open
      recovery_timeout_s: 60   # 60 mp utan half-open probalkoazs
      fallback: "cache"        # cache | error | degraded_response
  database:
    retry:
      max_attempts: 2
      backoff: "linear"
      base_delay_ms: 500
```

### 4.7 Human-in-the-Loop Approval Service

**Statusz:** 01_ARCHITECTURE.md definialt HumanReviewRequiredError, DB tabla letezik, de API nincs.
**Hatas:** Magas confidence igenyeknel (szamla jovahagyas, szerzodes review) ember bevonasa.

```
src/aiflow/services/human_review/
  __init__.py
  service.py                 # Review request lifecycle
  state_machine.py           # pending → approved|rejected → resumed|cancelled
  escalation.py              # Timeout → masik approver
```

**API:**
```
POST /api/v1/services/human-review/requests             → Review keres letrehozasa
GET  /api/v1/services/human-review/requests?status=pending → Fugo review-k
POST /api/v1/services/human-review/requests/{id}/approve → Jovahagyas
POST /api/v1/services/human-review/requests/{id}/reject  → Elutasitas
```

**Workflow integracio:**
```python
# Barmely service step-ben:
if confidence < config.review_threshold:
    raise HumanReviewRequiredError(
        context=extracted_data,
        fields=low_confidence_fields,
        timeout_hours=24,
        escalate_to="team_lead"
    )
```

### 4.8 Audit Trail Service

**Statusz:** 20_SECURITY_HARDENING.md + 10_BUSINESS_AUDIT_DOCS.md emliti, de nincs implementacio.
**Hatas:** GDPR compliance, valtozas kovetese, visszakereshetoseg.

```
src/aiflow/services/audit/
  __init__.py
  logger.py                  # Immutable audit log
  query.py                   # Audit log lekerdezes + export
  retention.py               # Megorzesi politika (archivalas > 1 ev)
```

**API:**
```
GET  /api/v1/admin/audit-logs?action=config_change&team_id=X&from=2026-01-01
POST /api/v1/admin/audit-logs/export   → CSV/JSON export
POST /api/v1/admin/data-erasure        → GDPR: adott user osszes adatanak torlese
```

### 4.9 Schema Registry (Kozponti)

**Statusz:** `email_intent_processor` hasznal SchemaRegistry-t, de skill-specifikus.
**Hatas:** Intent/entity/doc-type schemak kozponti kezelese, verziozas, A/B teszt.

```
src/aiflow/services/schema_registry/
  __init__.py
  registry.py                # Kozponti schema tarolo
  versioning.py              # Schema verziozas + backward compat check
  validator.py               # Input validacio schema alapjan
```

**Altalanositott schema tipusok:**
```
schemas/
  classifiers/               # Intent definiciok (barmilyen classifier-hez)
    email_intents_v1.json
    support_ticket_intents_v1.json
  extractors/                # Mezo definiciok (barmilyen extractor-hoz)
    invoice_fields_v1.json
    contract_fields_v1.json
    receipt_fields_v1.json
  validators/                # Validacioas szabalyok
    invoice_validation_v1.json
    contract_validation_v1.json
```

---

## 4.10 Alembic Migracios Strategia (DB Schema Management)

**Statusz:** 13 Alembic migracio letezik fizikailag (`alembic/versions/001-013`).
A `03_DATABASE_SCHEMA.md` 36 tablat + 13 view-t dokumental (ez az AUTHORITATIVE referencia).
Az alabbi lista a 13 migracio altal letrehozott fo tablakat mutatja (egyszerusitett nezet).
**Szabaly:** SOHA ne hozz letre tablat Alembic nelkul! (`CLAUDE.md` MANDATORY rule)

### Jelenlegi DB allapot (13 migracio, ld. 03_DATABASE_SCHEMA.md a teljes listaert)

```
LETEZO TABLAK (13 migracio altal letrehozva):
  Core:          users, teams, skills, skill_instances, workflow_definitions, workflow_runs, step_runs
  Documents:     documents, document_sync_schedules
  Costs:         cost_records
  ML:            model_registry, embedding_models
  RAG:           rag_collections, rag_chunks, rag_query_log, collections, chunks
  Security:      audit_log
  Scheduling:    schedules
  Human Review:  human_reviews
  A/B Testing:   ab_experiments, ab_assignments, ab_outcomes
  Testing:       test_datasets, test_cases, test_results
  Prompts:       skill_prompt_versions
  Alembic:       alembic_version

LETEZO VIEWK:
  v_daily_team_costs, v_instance_stats, v_model_usage,
  v_monthly_budget, v_test_trends, v_workflow_metrics
```

### Uj migraciok fazisokent

Minden fazisnak kulon Alembic migracio kell. A migraciok ELORE keszulnek, MIELOTT a service kod irasra kerul.

**Fazis 0 — Infra (014-016):**
```
014_add_service_config_versions.py
  - service_config_versions (id, service_instance_id FK, version, config_jsonb, deployed_at, deployed_by, is_active, change_description)
  - UNIQUE(service_instance_id, version)

015_add_cache_stats.py
  - cache_stats (id, cache_type, hit_count, miss_count, memory_bytes, recorded_at)
  - INDEX on (cache_type, recorded_at)

016_add_rate_limit_state.py
  - rate_limit_state (id, key, window_start, request_count, limit_value)
  - INDEX on (key, window_start)
```

**Fazis 1 — Domain A (017-019):**
```
017_add_email_connector_configs.py
  - email_connector_configs (id, name, provider, credentials_encrypted, mailbox, filters_jsonb, created_at)
  - email_fetch_history (id, config_id FK, fetched_at, email_count, error)

018_add_document_extractor_configs.py
  - document_type_configs (id, name, document_type, parser, fields_jsonb, validation_rules_jsonb, created_at)
  - extraction_results (id, config_id FK, source_file, extracted_data_jsonb, confidence, created_at)

019_add_invoices_table.py
  - invoices (id, source_file, direction, vendor_*, buyer_*, header_*, totals_*, validation_*, line_items_jsonb, parser_used, confidence_score, created_at)
  - invoice_line_items (id, invoice_id FK, line_number, description, quantity, unit, unit_price, net_amount, vat_rate, vat_amount, gross_amount)
  - MEGJEGYZES: Ez a tabla HIANYZIK a DB-bol! A documents.py jelenleg JSON fallback-et hasznal.
```

**Fazis 2 — RAG + Monitoring (020-022):**
```
020_add_notification_system.py
  - notification_channels (id, channel_type, config_jsonb, enabled, created_at)
  - notification_rules (id, event_type, channel_id FK, template_text, created_at)
  - notification_log (id, channel_id FK, event_type, sent_at, delivery_status, retry_count, error)

021_add_service_metrics.py
  - service_metrics (id, service_instance_id FK, metric_name, value_float, collected_at)
  - INDEX on (service_instance_id, metric_name, collected_at)

022_add_event_log.py
  - event_log (id, event_type, payload_jsonb, source_service, published_at)
  - event_subscriptions (id, event_type, subscriber_url, active)
```

**Fazis 3 — RPA + Media (023-024):**
```
023_add_rpa_configs.py
  - rpa_configs (id, name, steps_jsonb, browser, headless, created_at)
  - rpa_execution_log (id, config_id FK, started_at, completed_at, status, results_jsonb, error)

024_add_media_processor_configs.py
  - media_configs (id, name, pipeline_jsonb, provider, language, created_at)
  - media_results (id, config_id FK, source_file, transcript_text, structured_jsonb, created_at)
```

### Migracio Szabalyok

1. **Elnevezesi konvencio:** `NNN_add_{feature}.py` (haromjegyu sorszam)
2. **Upgrade + downgrade:** Minden migracio KOTELEZO `downgrade()` fuggveny (rollback!)
3. **Teszt:** `alembic upgrade head` + `alembic downgrade -1` + `alembic upgrade head` — mindharom HIBA NELKUL
4. **Review:** Minden migracio elott `alembic check` — konzisztencia ellenorzes
5. **Sorrend:** Migracio ELOSZOR, service kod MASODSZOR — soha ne legyen kod tabla nelkul
6. **Adat migracio:** Ha letezo tablat modositunk, `op.execute()` az adat migraciohoz
7. **Index:** Minden FK-ra es gyakori WHERE feltetelre INDEX

### Parancsok
```bash
# Uj migracio letrehozasa
make migrate-new NAME=add_invoices_table

# Migracio futtatasa
alembic upgrade head

# Rollback (1 lepes)
alembic downgrade -1

# Jelenlegi allapot
alembic current

# Migracio tortenete
alembic history
```

---

## 5. Bovitett Implementacios Fazisok

### Fazis 0: Infrastruktura Alapozas (1 het) ← UJ!
**Cel:** Epitokockak nelkul a domain service-ek nem uzemeltethetoak.

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 0.1 | `src/aiflow/services/` konyvtar + base class | `services/base.py`, `registry.py` | 4 ora |
| 0.2 | **Cache Layer** (Redis embedding + LLM cache) | `services/cache/` | 8 ora |
| 0.3 | **Config Versioning** (DB tabla + CRUD) | `services/config/versioning.py` | 6 ora |
| 0.4 | **Rate Limiter** (Redis sliding window) | `services/rate_limiter/` | 4 ora |
| 0.5 | **Retry/Circuit Breaker** kozponti konfiguracio | `services/resilience/` | 4 ora |
| 0.6 | Service API router alap | `api/v1/services.py` | 3 ora |
| 0.7 | `__all__` export hozzaadasa 7 modulhoz | core, engine, models, stb. | 2 ora |

**Vegeredmeny:** Stabil infra alap — cache, config versioning, rate limit, retry.
**Tag:** `v0.9.1-infra`

### Fazis 1: Domain Szolgaltatasok A (2-3 het)
**Cel:** Email Connector + Document Extractor + Schema Registry

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 1.1 | **Schema Registry** kozponti kiemelese | `services/schema_registry/` | 6 ora |
| 1.2 | **Email Connector** (O365 + IMAP + Gmail) | `services/email_connector/` | 10 ora |
| 1.3 | **Document Extractor** (altalanos mezo definicio) | `services/document_extractor/` | 12 ora |
| 1.4 | **Intent Classifier** (hibrid ML+LLM) | `services/classifier/` | 8 ora |
| 1.5 | Email Connector + Classifier end-to-end | integracio | 4 ora |
| 1.6 | Admin UI: Service config oldalak | `aiflow-admin/` | 8 ora |
| 1.7 | Auth: `/refresh` + `/api-keys` | `api/v1/auth.py` | 6 ora |

**Vegeredmeny:** Email + Document extraction mukodik altalanosan.
**Tag:** `v0.10.0-services`

### Fazis 2: RAG Engine + Monitoring (3-4 het)
**Cel:** RAG mint onallo szolgaltatas + uzemi megfigyeles

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 2.1 | **RAG Engine** multi-collection | `services/rag_engine/` | 12 ora |
| 2.2 | RAG Chat UI (kollekcio valaszto + chat) | `aiflow-admin/` | 10 ora |
| 2.3 | **Health Monitoring** per service | `services/monitoring/` | 8 ora |
| 2.4 | **Event Bus + Notifications** | `services/events/`, `services/notifications/` | 10 ora |
| 2.5 | **Cost Budget** service szintu | `services/rate_limiter/budget.py` | 6 ora |
| 2.6 | Runs: cancel, result, DLQ endpointok | `api/v1/runs.py` | 6 ora |

**Vegeredmeny:** RAG chat barmilyen dokuemntum kollekcional. Szolgaltatas monitoring + alerted.
**Tag:** `v0.11.0-rag`

### Fazis 3: RPA + Media + Approval (4-5 het)
**Cel:** Browser automatizalas, media feldolgozas, emberi jovahagyas

| # | Feladat | Fajlok | Becsult ido |
|---|---------|--------|-------------|
| 3.1 | **RPA Browser Service** (YAML steps) | `services/rpa_browser/` | 10 ora |
| 3.2 | **Media Processor** (multi-provider STT) | `services/media_processor/` | 8 ora |
| 3.3 | **Diagram Generator** kiemelese | `services/diagram_generator/` | 6 ora |
| 3.4 | **Human Review Service** | `services/human_review/` | 8 ora |
| 3.5 | Cubix skill → RPA + Media + RAG compose | skill refactor | 6 ora |
| 3.6 | Skills API: detail, manifest, ingest | `api/v1/skills_api.py` | 6 ora |

**Vegeredmeny:** Teljes service portfolio. Barmilyen skill composable.
**Tag:** `v0.12.0-complete`

### Fazis 4: Governance & Production Readiness (5-6 het)
**Cel:** Audit trail, compliance, teljes API lefedettse

| # | Feladat | Prioritas |
|---|---------|-----------|
| 4.1 | **Audit Trail** service | Magas |
| 4.2 | Prompts API: list, sync, promote | Kozepes |
| 4.3 | Scheduling API (cron + webhook trigger) | Kozepes |
| 4.4 | Admin endpointok (users, teams, system-config) | Kozepes |
| 4.5 | Evaluation API (test run, results, golden datasets) | Alacsony |
| 4.6 | Multi-tenant RLS (PostgreSQL row-level security) | Alacsony |
| 4.7 | Backup/DR strategia dokumentalasa + implementalas | Kozepes |
| 4.8 | tools/ + skill_system/ tesztek (≥80% coverage) | Kozepes |

**Vegeredmeny:** Production-ready framework, 90%+ API lefedettse.
**Tag:** `v1.0.0-rc1`

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

### 6.3 Git Verziozas

```
v0.9.0-stable     ← Jelenlegi stabil (rollback pont)
v0.9.1-infra      ← Fazis 0 utan (cache, config versioning, rate limit, retry)
v0.10.0-services  ← Fazis 1 utan (Email + Document + Classifier + Schema Registry)
v0.11.0-rag       ← Fazis 2 utan (RAG Engine + Monitoring + Events)
v0.12.0-complete  ← Fazis 3 utan (RPA + Media + Human Review + Diagram)
v1.0.0-rc1        ← Fazis 4 utan (Audit Trail + Governance + Production Ready)
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

## 8. Sikerkritieriumok

> **ARANY SZABALY:** Egy fazis CSAK AKKOR "KESZ" ha MINDEN sikerkriteriuma teljesul,
> es MINDEN teszt VALOS adatokkal, valos backend-del, valos bongeszioben tortenik.
> Mock/fake teszteles NEM SZAMIT — a fazist NEM lehet lezarni mock tesztekkel!

### Fazis 0 utan (Infra):
- [ ] Redis cache mukodik (embedding + LLM response)
- [ ] Config versioning: uj verzio deploy + rollback
- [ ] Rate limiter: per-service konfiguralhato limit
- [ ] Retry/Circuit breaker: LLM hivasokon aktiv
- [ ] 7 modul `__all__` export javitva
- [ ] Alembic migraciok (014-016) HIBA NELKUL: `upgrade head` + `downgrade -1` + `upgrade head`
- [ ] **VALOS TESZT:** `curl` hivással cache hit/miss ellenorizve, rate limit 429-et ad, config CRUD mukodik

### Fazis 1 utan (Domain A):
- [ ] Schema Registry: intent + entity + doc-type schemak kozpontilag kezelve
- [ ] Email Connector: O365 + IMAP mukodik parameterezhetoen
- [ ] Document Extractor: szamla + 1 masik doc tipus (pl. szerzodes)
- [ ] Intent Classifier: email + 1 masik kontextus (pl. support ticket)
- [ ] Auth: refresh token + API key management
- [ ] Admin UI-ban konfiguralhato mindegyik
- [ ] Regi skill-ek tovabbra is mukodnek (backward compat)
- [ ] Alembic migraciok (017-019) HIBA NELKUL futnak
- [ ] **VALOS TESZT:** Valos email fetch (IMAP), valos PDF extraction (Docling), Playwright E2E az Admin UI-n
- [ ] **VALOS TESZT:** `python -m skills.invoice_processor` valos PDF-fel — eredmeny JSON helyes

### Fazis 2 utan (RAG + Monitoring):
- [ ] RAG Chat: uj kollekcio letrehozasa + dokumentum feltoltes + kerdezes
- [ ] Chat UI: kollekcio valaszto, streaming valasz, citaciok
- [ ] Health monitoring: minden service egeszseget mutatja az Admin UI
- [ ] Event bus: step_completed, budget_alert esemenyek mukodnek
- [ ] Notification: email/Slack/webhook csatornak konfiguralhatoak
- [ ] Cost budget: service szintu koltseg limit + alert
- [ ] Runs API: cancel, result, DLQ endpointok
- [ ] Alembic migraciok (020-022) HIBA NELKUL futnak
- [ ] **VALOS TESZT:** RAG ingest valos PDF + query valasz relevanciaja, Playwright chat E2E
- [ ] **VALOS TESZT:** Health endpoint valos service statuszt mutat, event publish + subscribe mukodik

### Fazis 3 utan (RPA + Media + Approval):
- [ ] RPA: YAML konfiguracioval bongeszo automatizalas
- [ ] Media: video → szoveg barmilyen formatumbol, tobbfele STT provider
- [ ] Diagram Generator: onallo service, nem csak process_doc skill-bol
- [ ] Human Review: approval flow mukodik (pending → approved → workflow resume)
- [ ] Cubix skill: RPA + Media + RAG Engine compose-kent fut
- [ ] Skills API: detail, manifest, ingest endpointok
- [ ] Alembic migraciok (023-024) HIBA NELKUL futnak
- [ ] **VALOS TESZT:** Playwright-tal valos weboldal scrape, valos video transcript (ffmpeg+Whisper)
- [ ] **VALOS TESZT:** Human review approval flow Playwright E2E, diagram SVG valos render (Kroki)

### Fazis 4 utan (Governance):
- [ ] Audit Trail: immutable log, GDPR data erasure
- [ ] 90%+ endpoint lefedettse (45+ / 50)
- [ ] Prompts API: list, sync, promote, version history
- [ ] Scheduling: cron + webhook trigger konfiguralhas
- [ ] tools/ + skill_system/ tesztek ≥ 80% coverage
- [ ] Multi-tenant RLS aktiv a fo tablakon
- [ ] Backup/DR strategia dokumentalva + tesztelve
- [ ] **VALOS TESZT:** Audit rekord letezik DB-ben valos muvelet utan, RLS blokkol mas team adatait
- [ ] **VALOS TESZT:** Teljes E2E regresszio (L4 Complete): unit + integration + skill + Playwright UI
- [ ] **VALOS TESZT:** `pytest tests/ --cov=aiflow` ≥ 80% OVERALL coverage

---

## 9. Kockazatok es Mitigacio

| Kockazar | Valoszinuseg | Hatas | Mitigacio |
|----------|-------------|-------|-----------|
| Backward compat tores | Kozepes | Magas | Skill-ek belul hivjak a service-t, kulso API valtozatlan |
| LLM koltseg novekedes | Alacsony | Kozepes | Cache layer (4.1) + budget enforcement (4.5) |
| Docling lassusag | Magas | Kozepes | pypdfium2 fallback + asyncio.to_thread + embedding cache |
| pgvector skalazas | Alacsony | Magas | HNSW index + collection partitioning + query cache |
| OAuth2 token lejarat | Kozepes | Kozepes | Auto-refresh + retry logic (4.6) |
| Redis kiesés | Alacsony | Kozepes | Memory fallback cache + circuit breaker |
| Config valtozas incidensek | Kozepes | Magas | Config versioning + rollback (4.3) + audit trail (4.8) |
| LLM provider kiesés | Alacsony | Magas | Circuit breaker (4.6) + LLM response cache (4.1) + fallback model |
| GDPR compliance hiány | Kozepes | Magas | Audit trail (4.8) + data erasure endpoint |
| Emberi review bottle-neck | Kozepes | Kozepes | SLA timeout + escalation (4.7) + notification (4.2) |

---

## 10. Architektura Audit Osszefoglalas

### Dokumentalt de NEM implementalt komponensek

| Komponens | Dokumentum | Statusz | Fazis |
|-----------|-----------|---------|-------|
| Embedding cache | 30_RAG_PRODUCTION_PLAN | Hianyzo | F0 |
| MessageBroker ABC | 09_MIDDLEWARE_INTEGRATION | ABC van, nincs bekotes | F2 |
| RetryPolicy ABC | 01_ARCHITECTURE | ABC van, nincs config | F0 |
| CircuitBreaker | 01_ARCHITECTURE | Error osztaly van, logika nincs | F0 |
| HumanReviewRequiredError | 01_ARCHITECTURE | Error van, API nincs | F3 |
| Audit log | 20_SECURITY_HARDENING | Emlitve, nem implementalt | F4 |
| Budget enforcement | 01_ARCHITECTURE | Mezo van, logika nincs | F2 |
| Schema versioning | 28_MODULAR_DEPLOYMENT | Instance YAML van, verzio nincs | F0 |
| PII detection | 20_SECURITY_HARDENING | Emlitve, nem implementalt | F4 |
| Prompt sync (Langfuse) | 06_CLAUDE_CODE_INTEGRATION | Tervezett, nincs API | F4 |

### DB tablak API nelkul (Zombie tablak) — Teljes Audit (2026-04-01)

> **19 tabla NINCS API-ja, 4 tabla RESZLEGES API-val rendelkezik.**
> Minden zombie tablat a megfelelo fazisban kell "eletre kelteni" (CRUD endpoint + valos teszt).

| Tabla | Migracio | API Statusz | Tervezett fazis | Megjegyzes |
|-------|----------|------------|-----------------|------------|
| skills | 002 | ZOMBIE | F1 | Hardcoded registry helyett DB-bol |
| workflow_definitions | 002 | ZOMBIE | F2 | Placeholder adat helyett DB CRUD |
| skill_prompt_versions | 002 | ZOMBIE | F4 | Langfuse sync API |
| model_registry | 003 | ZOMBIE | F4 | Model CRUD + version management |
| embedding_models | 003 | ZOMBIE | F2 | RAG Engine hasznalja |
| collections | 004 | ZOMBIE | F2 | RAG multi-collection CRUD |
| documents | 004 | ZOMBIE | F1 | Document Extractor hasznalja |
| chunks | 004 | ZOMBIE | F2 | RAG Engine belso tabla |
| document_sync_schedules | 004 | ZOMBIE | F4 | Scheduling API |
| teams | 005 | ZOMBIE | F4 | Admin CRUD |
| users | 005 | RESZLEGES | F1 | Auth: hardcoded → DB-backed |
| audit_log | 005 | ZOMBIE | F4 | Audit Trail service |
| cost_records | 006 | RESZLEGES | F2 | Csak read, CRUD kell |
| schedules | 007 | ZOMBIE | F4 | Scheduling API |
| human_reviews | 008 | ZOMBIE | F3 | Human Review service |
| ab_experiments | 009 | ZOMBIE | F4 | Evaluation API |
| ab_assignments | 009 | ZOMBIE | F4 | Evaluation API |
| ab_outcomes | 009 | ZOMBIE | F4 | Evaluation API |
| test_datasets | 010 | ZOMBIE | F4 | Evaluation API |
| test_cases | 010 | ZOMBIE | F4 | Evaluation API |
| test_results | 010 | ZOMBIE | F4 | Evaluation API |
| skill_instances | 012 | ZOMBIE | F1 | Instance CRUD (service config) |
| rag_collections | 013 | ZOMBIE | F2 | RAG multi-collection |
| rag_query_log | 013 | RESZLEGES | F2 | Feedback endpoint van, analitika kell |
| rag_chunks | 013 | RESZLEGES | F2 | Health check van, CRUD kell |
| workflow_runs | 001 | RESZLEGES | F2 | Csak LIST+READ, cancel/DLQ kell |
| step_runs | 001 | RESZLEGES | F2 | Implicit FK read, kello endpoint |

**Zombie eloszlas fazisokent:**
- **F1:** 4 tabla (skills, documents, users, skill_instances)
- **F2:** 9 tabla (workflow_definitions, embedding_models, collections, chunks, cost_records, rag_collections, rag_query_log, rag_chunks, workflow_runs+step_runs)
- **F3:** 1 tabla (human_reviews)
- **F4:** 13 tabla (prompt_versions, model_registry, doc_sync, teams, audit_log, schedules, 6x eval/test tablak)

---

## 11. UI Fejlesztesi Strategia (User Journey Alapu, API-First)

> **ALAPELV:** A UI fejlesztes MINDIG az API utan kovetkezik, SOHA nem elotte.
> Eloszor: User Journey definicio → Szukseges API endpointok → Backend implementacio → UI/UX tervezes → UI fejlesztes → Playwright E2E teszt
> A service generalizacio (F0-F4) a **fo cel** — a UI fejlesztes ezekre epul.

### 11.1 Jelenlegi UI Allapot (2026-04-01)

| Oldal | User Journey | API | UI Statusz | Blocker |
|-------|-------------|-----|-----------|---------|
| InvoiceUpload | Upload → Process → Results | ✅ Teljes | **MUKODO** | Verify endpoint hianyzik |
| InvoiceList | List → Filter → Detail | ✅ Teljes | **MUKODO** | — |
| InvoiceShow | Detail → Image → Fields | ✅ Teljes | **MUKODO** | Image preview nem hasznalt |
| InvoiceVerify | Show → Edit → Save | ❌ HIANYZIK | **STUB** | POST verify endpoint + UI |
| EmailUpload | Upload → Process → Results | ✅ Teljes | **MUKODO** | Szekvencialis (nem batch) |
| EmailList | List → Filter → Detail | ✅ Teljes | **MUKODO** | — |
| EmailShow | Detail → Intent → Entities | ❌ GET /{id} | **WORKAROUND** | List fallback (N+1 issue) |
| ProcessDocs | Describe → Generate → Review | ✅ Teljes | **MUKODO** | Nem perzisztens |
| RagChat | Question → Stream → Feedback | ✅ Teljes | **MUKODO** | Feedback nem bekotve |
| CubixViewer | View courses | ✅ Teljes | **DEMO** | View-only, nincs interakcio |
| RunList/Show | List → Detail → Steps | ✅ Teljes | **MUKODO** | Cancel/DLQ hianyzik |
| CostsPage | View costs by skill/step | ✅ Teljes | **MUKODO** | Client-side aggregacio |

### 11.2 User Journey-k es Szukseges API-k Fazisokent

#### F1: Service Config + Email + Document Journey

**Journey A: Service Konfiguracio**
```
Admin → Service lista → Uj service config → Mentés → Verzio kezeles
```
Szukseges API-k:
- `GET /api/v1/services` — service lista
- `POST /api/v1/services/{type}/config` — uj config
- `GET /api/v1/services/{id}/versions` — verzio tortentet
- `PUT /api/v1/services/{id}/config` — config frissites
- `POST /api/v1/services/{id}/rollback/{version}` — rollback

**Journey B: Email Feldolgozas (teljes)**
```
Email Connector config → Fetch test → List → Detail → Intent → Entities → Routing
```
Szukseges HIANYZIO API-k:
- `GET /api/v1/emails/{email_id}` — **KRITIKUS** (jelenleg list fallback!)
- `POST /api/v1/services/email-connector/test` — kapcsolat teszt
- `GET /api/v1/services/email-connector/stats` — statisztikak

**Journey C: Szamla Verifikacio (teljes)**
```
Upload → Process → List → Detail → Verify → Save corrected → Export
```
Szukseges HIANYZIO API-k:
- `POST /api/v1/documents/{source_file}/verify` — **KRITIKUS** (verification save)
- `GET /api/v1/documents/{source_file}/images/{page}` — oldal kepek (letezik, UI nem hasznalja)

#### F2: RAG + Monitoring Journey

**Journey D: RAG Kollekcio Kezeles**
```
Kollekcio letrehozas → Dokumentum feltoltes → Ingest → Query → Feedback → Analitika
```
Szukseges API-k:
- `GET /api/v1/services/rag/collections` — kollekcio lista
- `POST /api/v1/services/rag/collections` — uj kollekcio
- `POST /api/v1/services/rag/collections/{id}/ingest` — dokumentum ingest
- `GET /api/v1/services/rag/collections/{id}/stats` — kollekcio statisztika
- Feedback endpointok: `POST /api/v1/feedback` (letezik, UI nem bekotve!)

**Journey E: Monitoring Dashboard**
```
Service health → Alerts → Metrics → Cost drilldown → Budget config
```
Szukseges API-k:
- `GET /api/v1/services/health` — osszes service allapot
- `GET /api/v1/services/{id}/metrics` — service metrikak
- `GET /api/v1/costs/summary` — server-side aggregacio (jelenleg client-side)
- `GET /api/v1/runs/{id}/cancel` — run cancel
- `GET /api/v1/runs/{id}/dlq` — dead letter queue

#### F3: RPA + Media + Approval Journey

**Journey F: Human Review Approval**
```
Pending reviews → Detail → Approve/Reject → Resume workflow → History
```
Szukseges API-k:
- `GET /api/v1/reviews/pending` — varakozo review-k
- `POST /api/v1/reviews/{id}/approve` — jovahagyas
- `POST /api/v1/reviews/{id}/reject` — elutasitas
- `GET /api/v1/reviews/history` — torteneti lista

#### F4: Admin + Governance Journey

**Journey G: Admin Felulet**
```
Users → Teams → Roles → API keys → Audit log → Schedules
```
Szukseges API-k:
- `GET/POST/PUT/DELETE /api/v1/admin/users` — user CRUD
- `GET/POST/PUT/DELETE /api/v1/admin/teams` — team CRUD
- `GET/POST/DELETE /api/v1/admin/api-keys` — API key management
- `GET /api/v1/admin/audit-log` — audit log lista + szures
- `GET/POST/PUT/DELETE /api/v1/admin/schedules` — scheduling CRUD

### 11.3 UI/UX Fejlesztesi Pipeline (7 lepes, 3 MCP eszkozzel)

> **Eszkozok:** Figma MCP (design), Playwright MCP (teszteles), Claude Code (fejlesztes)
> **Design System:** Untitled UI (React 19 + Tailwind v4 + React Aria), Figma Kit
> **Figma channel:** `e71e0crh` | **Figma sync:** `aiflow-admin/figma-sync/`

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. USER JOURNEY DEFINICIO (/ui-journey)                             │
│    Ki? Mit? Hogyan? Milyen lepesekbol all?                          │
│    ↓                                                                 │
│ 2. API AUDIT + TERVEZES                                             │
│    Letezik az API? → ✅ tovabb | ❌ eloszor /ui-api-endpoint         │
│    Zombie tabla? → 🧟 eloszor Alembic migracio + CRUD endpoint      │
│    ↓                                                                 │
│ 3. BACKEND IMPLEMENTACIO + VALOS TESZT                              │
│    curl hivás → valos adat? → source: "backend"?                     │
│    ↓                                                                 │
│ 4. FIGMA UI/UX DESIGN (/ui-design)                         ← MCP   │
│    Figma MCP-vel: create_frame → set_auto_layout → komponensek      │
│    PAGE_SPECS.md frissites + screenshot exportalas                    │
│    Design elvek: Governor Pattern, Progressive Disclosure, i18n      │
│    ↓                                                                 │
│ 5. UI FEJLESZTES (/ui-page, /ui-component)                         │
│    Figma design alapjan: React Admin + MUI (jelenleg)                │
│    Kesobb: Untitled UI + Tailwind v4 (ld. REDESIGN_PLAN.md)         │
│    ↓                                                                 │
│ 6. PLAYWRIGHT E2E TESZT                                     ← MCP   │
│    MCP Playwright: navigate → snapshot → click → screenshot          │
│    Valos backend-del! Console hiba ellenorzes! i18n toggle!          │
│    ↓                                                                 │
│ 7. FIGMA ↔ CODE SZINKRON + "KESZ"                                   │
│    Design token drift ellenorzes (figma-to-code.ts)                  │
│    Ha elteres: Figma VAGY kod frissitese                             │
│    Git tag ha fazis lezaras                                          │
└─────────────────────────────────────────────────────────────────────┘
```

**Claude Code Slash Commands a pipeline lepeseihez:**

| Lepes | Command | MCP | Output |
|-------|---------|-----|--------|
| 1. Journey | `/ui-journey` | — | Journey doc + API audit tabla |
| 2-3. API | `/ui-api-endpoint` | — | FastAPI endpoint + curl teszt |
| 4. Design | `/ui-design` | Figma MCP | Figma frame + PAGE_SPECS.md |
| 5. Fejlesztes | `/ui-page` / `/ui-component` / `/ui-viewer` | — | React komponens + i18n |
| 6. Teszt | `/dev-step` | Playwright MCP | E2E teszt + screenshot |
| 7. Szinkron | manualis | Figma MCP | Design token diff |

> **FONTOS:** A UI fejlesztes NEM kulon fazis — hanem MINDEN service fazis RESZE.
> F1-ben az Email + Document UI, F2-ben a RAG + Monitoring UI, stb.
> De a pipeline MINDIG sorrendben halad: Journey → API → Design → UI → Teszt!

### 11.4 Azonnali UI Blocker-ek (Service Generalizacio ELOTT javitando)

| Blocker | Hatas | Javitas | Becsult ido |
|---------|-------|---------|-------------|
| `GET /api/v1/emails/{email_id}` hianyzik | EmailShow N+1 query | Endpoint implementalas | 2 ora |
| `POST /api/v1/documents/{file}/verify` hianyzik | Verification nem mukodik | Endpoint + UI | 4 ora |
| Feedback gombok nem bekotve (RagChat) | Felhasznaloi visszajelzes elvesz | Wire up POST /feedback | 1 ora |

Ezek a F1 fazis elso feladatai — a service generalizacio elott kell megoldani, mert a meglevo UI-t torik.

---

## Hivatkozasok

- `01_PLAN/01_ARCHITECTURE.md` — Core architektura (RetryPolicy, CircuitBreaker, HumanReview)
- `01_PLAN/09_MIDDLEWARE_INTEGRATION.md` — MessageBroker ABC, back-pressure
- `01_PLAN/20_SECURITY_HARDENING.md` — PII detection, audit trail kovetelmeny
- `01_PLAN/22_API_SPECIFICATION.md` — Eredeti API specifikacio (50+ endpoint)
- `01_PLAN/28_MODULAR_DEPLOYMENT.md` — Multi-customer instance architektura
- `01_PLAN/29_OPTIMIZATION_PLAN.md` — Korabbi optimalizacios lepesek
- `01_PLAN/30_RAG_PRODUCTION_PLAN.md` — RAG pipeline checklist (embedding cache!)
- `v0.9.0-stable` git tag — Rollback pont
