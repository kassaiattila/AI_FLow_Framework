# AIFlow v1.1.4 — Kovetkezo Session Prompt

> **Datum:** 2026-04-03 (4. session utan)
> **Elozo session:** ~2600 sor, 20+ fajl, per-file progress, ChatPanel redesign, Outlook COM, email intent pipeline, 16 bugfix
> **Branch:** main (NEM commitolva meg — ELSO TEENDO!)
> **Port:** API 8102, Frontend 5173 (Vite proxy → 8102)
> **Dokumentacio:** `01_PLAN/47_SESSION4_DOCUMENTATION.md` (reszletes), `01_PLAN/46_RAG_CHAT_REDESIGN_PLAN.md` (chat terv)
> **Konzisztencia audit:** 10/10 PASS (Section 12 a 47-es dokban)

---

## ELSO TEENDO: Git Commit

```bash
git add -A && git status  # ellenorizd mit commitolsz
git commit -m "feat: per-file pipeline progress, ChatPanel redesign, Outlook COM connector, email intent pipeline, media STT fixes

- Unified FileProgressRow component across all 6 pipeline pages
- ChatPanel modular architecture (10 files): LLM selector, history, copy, scroll
- Outlook COM email connector (win32com MAPI)
- Email intent processing: fetch-and-process-stream, process-batch-stream
- Media STT fixes: ffmpeg acodec, transcript keys, output_dir
- Verification overlay toggle, Documents action spacing
- 16 bug fixes, Alembic migration 026
- Full consistency audit: 10/10 PASS

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Szerver inditas

```bash
.venv\Scripts\python.exe -B -m uvicorn aiflow.api.app:create_app --factory --port 8102
cd aiflow-admin && npm run dev
```

---

## FO FELADAT: Orchestralhato Szolgaltatasi Architektura

### Vizioio

A jelenlegi rendszerben az egyes pipeline-ok (document, email, RAG, media, BPMN) **onalloan mukodnek**, de nincs kozottuk **automatikus lancolas**. A cel: **ujrahasznalhato, promptokkal parameterezhezo, egymasra epulo szolgaltatasi egysegek** amik YAML-bol orchestralhatoak.

### Jelenlegi Allapot (v1.1.4)

```
[Outlook COM] → .eml fajlok → data/emails/outlook/
[Document Upload] → PDF fajlok → data/uploads/invoices/
[Media Upload] → video/audio → data/uploads/media/
[RAG Ingest] → PDF/DOCX → pgvector chunks
[BPMN Generate] → szoveg → mermaid diagram
```

Ezek **fuggetlenul** mukodnek. Nincs automatikus lancolas.

### Cel Architektura: Service Mesh / Pipeline Orchestrator

```yaml
# Pelda: Email Intent → Document Processing → Routing
pipeline: email_to_document
trigger: email_fetched
steps:
  - service: email_intent_classifier
    config:
      model: openai/gpt-4o-mini
      confidence_threshold: 0.7
    output: intent, entities, priority

  - service: attachment_router
    condition: "intent.intent_id in ['invoice', 'contract', 'report']"
    config:
      extract_attachments: true
      filter_mime: ["application/pdf", "image/*"]
    output: attachment_files[]

  - service: document_extractor
    for_each: attachment_files
    config:
      parser: docling
      extraction_model: openai/gpt-4o
      document_type: "{{ intent.intent_id }}"  # prompt parameter
    output: extracted_data

  - service: data_router
    config:
      rules:
        - intent: invoice → output_dir: data/processed/invoices/
        - intent: contract → output_dir: data/processed/contracts/
        - intent: report → notify: admin@bestix.hu
    output: routed_files[]

  - service: notification
    config:
      channel: email
      template: "{{ intent.intent_display_name }}: {{ extracted_data.summary }}"
```

### Tervezesi Feladatok (5. session)

#### 1. Service Registry + Interface
Minden szolgaltatas egyseges interface-szel:
```python
class AIFlowService(ABC):
    name: str
    version: str
    input_schema: BaseModel   # Pydantic
    output_schema: BaseModel  # Pydantic
    config_schema: BaseModel  # YAML-bol parameterezhezo

    async def execute(self, input: InputModel, config: ConfigModel) -> OutputModel
    async def health_check() -> bool
```

Meglevo szolgaltatasok interface-re huzasa:
| Szolgaltatas | Jelenlegi hely | Input | Output |
|-------------|---------------|-------|--------|
| email_fetcher | services/email_connector | {connector_id, days, limit} | FetchedEmail[] |
| email_classifier | skills/email_intent_processor | {eml_path} | {intent, entities, priority, routing} |
| document_extractor | services/document_extractor | {file_path, doc_type} | {fields, line_items, validation} |
| rag_ingestor | services/rag_engine | {files[], collection_id} | {chunks_created} |
| rag_query | services/rag_engine | {question, collection, model} | {answer, sources} |
| media_transcriber | services/media_processor | {file_path} | {transcript, sections} |
| bpmn_generator | skills/process_documentation | {description} | {mermaid_code, review} |
| data_router | UJ | {files[], rules} | {routed_files[]} |
| notifier | UJ | {channel, template, data} | {sent: bool} |

#### 2. Pipeline Orchestrator (YAML-driven)
```
01_PLAN/pipelines/
  email_to_document.yaml     — email → intent → attachment → extract → route
  rag_knowledge_update.yaml  — email attachment → RAG ingest → notify
  media_to_docs.yaml         — video → STT → BPMN diagram
  invoice_audit.yaml         — document → verify → export CSV → notify
```

#### 3. Prompt Parameterezes (Jinja2 template-ek)
Minden service config-ja Jinja2 template-eket tamogat:
```yaml
extraction_model: "{{ env.DEFAULT_MODEL }}"
document_type: "{{ trigger.intent.intent_id }}"
output_dir: "data/processed/{{ trigger.intent.intent_id }}/{{ now().strftime('%Y-%m') }}"
```

#### 4. Event Bus (Redis Pub/Sub)
Szolgaltatasok kozott event-alapu kommunikacio:
```
email_fetched → email_classifier
email_classified → attachment_router (ha van csatolmany)
attachment_extracted → data_router
document_processed → notifier
```

#### 5. Admin UI: Pipeline Builder
- Vizualis pipeline szerkeszto (drag-and-drop)
- Service catalog (elerheto szolgaltatasok listaja)
- Pipeline futtatasi naplo (Runs oldalon)
- Konfiguracio szerkesztes (YAML editor)

### Pelda Uzleti Folyamatok

**1. Szamla Automatizacio:**
```
Email bejon → Intent: "invoice" → PDF csatolmany kinyeres →
Document Extractor (szamla fieldek) → Verify → CSV export → Konyvelo ertesites
```

**2. RAG Tudasbazis Frissites:**
```
Email bejon → Intent: "report" / "documentation" → PDF csatolmany →
RAG Ingest (kollekcio: "belso_dokumentumok") → Notify: "Uj dokumentum ingesztalva"
```

**3. Ertekesitesi Ajanlat Feldolgozas:**
```
Email bejon → Intent: "sales_inquiry" → Entity extraction (cegnev, osszeg) →
BPMN diagram (ajanlati folyamat) → Notify: sales@bestix.hu
```

**4. Media Feldolgozas → Dokumentacio:**
```
Video feltoltes → STT transcript → Szekcio kinyeres →
BPMN diagram (oktatas folyamat) → RAG ingest (tudásbázis) → Notify
```

---

## Jelenlegi Rendszer Allapot

### Infrastruktura
- PostgreSQL 5433, Redis 6379 (Docker)
- API: 8102, Frontend: 5173
- Auth: admin@bestix.hu / admin
- 26 Alembic migracio, 41 DB tabla, 112+ endpoint, 19 router, 17 UI oldal

### Mukodo Szolgaltatasok
| Szolgaltatas | Allapot | Teszt |
|-------------|---------|-------|
| Document upload + extract | MUKODIK | E2E PASS |
| RAG ingest + query | MUKODIK | E2E PASS (86% eval) |
| Email Outlook COM fetch | MUKODIK | 56 email letoltve |
| Email intent classification | MUKODIK | LLM-based |
| Media STT (Whisper) | MUKODIK | completed status |
| BPMN diagram generation | MUKODIK | mermaid output |

### Email Connectorok
| Nev | Provider | Allapot |
|-----|----------|---------|
| BestIx IMAP | imap | FAIL (O365 BasicAuth blocked) |
| BestIx Outlook | outlook_com | MUKODIK |

---

## Hasznos Parancsok

```bash
# Login token
TOKEN=$(curl -s -X POST http://localhost:8102/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"admin"}' | python -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Szolgaltatasok listaja
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8102/api/v1/services | python -m json.tool

# Email fetch + process
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"config_id":"OUTLOOK_ID","since_days":7,"limit":10}' \
  http://localhost:8102/api/v1/emails/fetch-and-process-stream

# RAG query + model override
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"Mi az ASZF?","model":"openai/gpt-4o-mini"}' \
  http://localhost:8102/api/v1/rag/collections/COLLECTION_ID/query
```

---

## Fajl Referencia

| Kategoria | Fajlok |
|-----------|--------|
| Session 4 doksi | `01_PLAN/47_SESSION4_DOCUMENTATION.md` |
| Chat terv | `01_PLAN/46_RAG_CHAT_REDESIGN_PLAN.md` |
| Service terv | `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` |
| UI terv | `01_PLAN/43_UI_RATIONALIZATION_PLAN.md` |
| API spec | `01_PLAN/22_API_SPECIFICATION.md` |
| DB schema | `01_PLAN/03_DATABASE_SCHEMA.md` |
| Master plan | `01_PLAN/AIFLOW_MASTER_PLAN.md` |
| Pipeline peldak | Meg nem letezik — 5. session-ben letrehozando |
