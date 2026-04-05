# AIFlow v1.2.0 — Document Extraction & Intent Identification

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
> **Cel:** Parameterezheeto dokumentumtipusok alapjan adatkinyeres, intent azonositas es routing, email csatolmany feldolgozas.

---

## 1. Jelenlegi Allapot

### Meglevo kepessegek:

| Komponens | Allapot | Fajl |
|-----------|---------|------|
| **DocumentExtractorService** | Mukodik | `src/aiflow/services/document_extractor/service.py` |
| **DocumentTypeConfig** | DB-ben, JSONB | `document_type_configs` tabla |
| **ClassifierService** | Mukodik (hybrid ML+LLM) | `src/aiflow/services/classifier/service.py` |
| **EmailConnectorService** | Mukodik (IMAP, Outlook COM) | `src/aiflow/services/email_connector/service.py` |
| **Email Intent Processor** | Skill (LLM-based) | `skills/email_intent_processor/` |

### Jelenlegi korlatok:

1. **Dokumentumtipusok** statikusak — uj tipus hozzaadasahoz DB config CRUD kell
2. **Intent schema** a skill-ben van hardcode-olva, nem pipeline-bol parameterezheeto
3. **Szabad szoveges kinyeres** nincs — csak elore definialt field-ek
4. **Csatolmany routing** manualis — nincs szabaly-alapu automatikus routing
5. **Konfidencia alapu eskalalas** nincs — alacsony bizonyossag eseten nincs HITL

---

## 2. Cel Architektura

### 2.1 Parameterezheeto Dokumentumtipusok

```
┌──────────────────────────────────────────────┐
│ DOCUMENT TYPE REGISTRY (DB + YAML import)     │
│                                               │
│ ┌─────────────┐  ┌──────────────┐  ┌───────┐│
│ │ Szamla (v2) │  │ Szerzodes(v1)│  │ Custom ││
│ │ fields: 15  │  │ fields: 12   │  │ YAML   ││
│ │ rules: 8    │  │ rules: 5     │  │ import ││
│ └─────────────┘  └──────────────┘  └───────┘│
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│ EXTRACTION ENGINE                             │
│ 1. Parse (Docling/Unstructured/OCR)          │
│ 2. Classify document type (auto or manual)    │
│ 3. Extract fields (LLM, schema-guided)       │
│ 4. Validate (rules engine)                    │
│ 5. Confidence check → HITL or auto-approve   │
└──────────────────────────────────────────────┘
```

### 2.2 Dokumentum Tipus Definicio (bovitett)

```python
class DocumentTypeConfig(BaseModel):
    """Parameterezett dokumentumtipus konfiguracio."""
    name: str                          # "invoice", "contract", "report"
    display_name: str                  # "Szamla", "Szerzodes", "Jelentes"
    version: str = "1.0.0"
    
    # Mezo definiciok (mit kell kinyerni)
    fields: list[FieldDefinition]
    
    # Validacios szabalyok
    validation_rules: list[ValidationRule]
    
    # Extraction prompt (Jinja2 template)
    extraction_prompt: str | None = None  # Ha None, generic prompt
    
    # Konfidencia kuszobertekek
    auto_approve_threshold: float = 0.90  # E felett automatikusan elfogadva
    review_threshold: float = 0.70        # E felett emberi review
    reject_threshold: float = 0.50        # Ez alatt automatikusan elutasitva
    
    # Output konfiguracio
    output_formats: list[str] = ["json"]  # json, csv, xlsx
    output_dir_template: str = "data/extracted/{{ doc_type }}/{{ date }}"
    
    # Routing szabalyok
    routing_rules: list[RoutingRule] = []

class FieldDefinition(BaseModel):
    name: str                          # "vendor_name", "total_amount"
    display_name: str                  # "Szallito neve", "Vegosszeg"
    field_type: Literal["text", "number", "date", "currency", "boolean", "list", "table"]
    required: bool = False
    default: Any | None = None
    validation_regex: str | None = None  # pl. "\\d{4}-\\d{2}-\\d{2}" datum formatum
    llm_hint: str | None = None          # Segitseg az LLM-nek a kinyereshez
    category: str = "general"            # Csoportositas a UI-ban (vendor, buyer, totals, ...)

class ValidationRule(BaseModel):
    name: str
    expression: str                    # Python eval-safe kifejezés
    error_message: str
    severity: Literal["error", "warning"]
    # Pelda: "total_amount > 0", "due_date > invoice_date"

class RoutingRule(BaseModel):
    condition: str                     # Jinja2 condition: "{{ total_amount > 100000 }}"
    action: str                        # "notify", "move_to_dir", "create_review"
    config: dict                       # Action-specifikus config
```

### 2.3 Szabad Szoveges Kinyeres

A jelenlegi rendszer CSAK elore definialt mezoket tud kinyerni. Uj kepesseg:

```python
class FreeTextExtractionConfig(BaseModel):
    """Szabad szoveges tartalom kinyeres LLM-mel."""
    query: str                         # "Mi a szerzodes targya?"
    response_format: Literal["text", "list", "table", "structured"]
    max_length: int = 1000
    language: str = "hu"

# Hasznalat:
result = await extractor.extract_free_text(
    document_id="...",
    queries=[
        FreeTextExtractionConfig(query="Mi a szerzodes targya?", response_format="text"),
        FreeTextExtractionConfig(query="Sorod fel a kotelezetttsegeket", response_format="list"),
        FreeTextExtractionConfig(query="Osszegezd a fizetesi feltételeket", response_format="structured"),
    ]
)
```

---

## 3. Intent Identification Bovites

### 3.1 Jelenlegi intent rendszer

A `ClassifierService` hybrid ML+LLM klasszifikacioval mukodik:
- **sklearn ML** (TF-IDF + LinearSVC): <1ms, $0, gyors szures
- **LLM refinement** (gpt-4o-mini): ha ML confidence < threshold

### 3.2 Bovitett Intent Schema (pipeline-bol parameterezheeto)

```python
class IntentSchema(BaseModel):
    """Parameterezheeto intent definicio — YAML-bol betoltheto."""
    name: str                           # "invoice_processing"
    version: str = "1.0.0"
    
    intents: list[IntentDefinition]
    entity_types: list[EntityType]
    routing_matrix: list[RoutingEntry]

class IntentDefinition(BaseModel):
    id: str                             # "invoice", "contract", "inquiry"
    display_name: str                   # "Szamla", "Szerzodes", "Erdeklodes"
    description: str                    # LLM-nek: mikor valassza ezt
    examples: list[str]                 # Few-shot peldak
    keywords: list[str]                 # ML gyors szures
    priority: int = 0                   # Magasabb = fontosabb
    confidence_threshold: float = 0.7   # E felett fogadjuk el

class EntityType(BaseModel):
    name: str                           # "company_name", "amount", "date"
    extraction_type: Literal["regex", "llm", "both"]
    regex_pattern: str | None = None
    llm_hint: str | None = None
    required_for_intents: list[str] = []

class RoutingEntry(BaseModel):
    intent_id: str
    action: str                         # "extract_document", "notify", "create_task"
    pipeline: str | None = None         # Pipeline nev amit triggerel
    config: dict = {}
```

### 3.3 Intent → Pipeline Trigger

```yaml
# Intent schema YAML pelda
name: email_intent_schema
version: "1.0.0"
intents:
  - id: invoice
    display_name: "Szamla"
    description: "Email szamlat tartalmaz vagy szamlarol szol"
    examples:
      - "Mellekeljuk a szamlat"
      - "Kerem fizesse be az alabbiak szerint"
    keywords: ["szamla", "invoice", "fizetesi", "osszeg"]
    priority: 10

  - id: contract
    display_name: "Szerzodes"
    description: "Szerzodest tartalmaz vagy szerzodes keresrol szol"
    examples:
      - "Csatoljuk az alart szerzodest"
      - "Kerjuk az alabbi szerzodes visszaigazolasat"
    keywords: ["szerzodes", "contract", "megallpodas"]
    priority: 8

routing_matrix:
  - intent_id: invoice
    action: trigger_pipeline
    pipeline: invoice_automation     # A 48-as tervben definialt pipeline
    config:
      doc_type: invoice
      auto_process: true

  - intent_id: contract
    action: trigger_pipeline
    pipeline: contract_analysis
    config:
      doc_type: contract
      require_review: true
```

---

## 4. Email → Szamla Automatizacio Use Case

### 4.1 Teljes Pipeline

```yaml
name: invoice_automation
version: "1.0.0"
description: "Email → szamla azonositas → letoltes → adatkinyeres → mapparendezas → ertesites"
trigger:
  type: cron
  cron_expression: "0 */2 * * *"  # 2 orankent
input_schema:
  connector_id: { type: string, required: true }

steps:
  - name: fetch_emails
    service: email_connector
    method: fetch_emails
    config:
      connector_id: "{{ input.connector_id }}"
      days: 1
      limit: 50

  - name: classify_intent
    service: classifier
    method: classify
    depends_on: [fetch_emails]
    for_each: "{{ fetch_emails.output.emails }}"
    config:
      text: "{{ item.subject }} {{ item.body_text }}"
      schema: invoice_intent_schema  # Parameterezheeto intent schema

  - name: filter_invoices
    service: data_router
    method: filter
    depends_on: [classify_intent]
    config:
      condition: "intent_id == 'invoice' and confidence >= 0.7"
      extract_attachments: true
      filter_mime: ["application/pdf", "image/*"]

  - name: extract_data
    service: document_extractor
    method: extract
    depends_on: [filter_invoices]
    for_each: "{{ filter_invoices.output.attachments }}"
    config:
      config_name: invoice_v2     # Parameterezheeto dokumentumtipus
      parser: auto

  - name: validate_and_route
    service: document_extractor
    method: validate_and_route
    depends_on: [extract_data]
    for_each: "{{ extract_data.output.results }}"
    config:
      # Magas konfidencia → auto folder, alacsony → HITL review
      auto_approve_threshold: 0.90
      review_threshold: 0.70
      output_dir: "data/invoices/{{ item.extracted_fields.vendor_name }}/{{ now_month }}"

  - name: notify_accountant
    service: notification
    method: send
    depends_on: [validate_and_route]
    config:
      channel: email
      recipients: ["konyvelo@bestix.hu"]
      template: |
        Uj szamlak feldolgozva:
        {% for inv in validate_and_route.output.results %}
        - {{ inv.vendor_name }}: {{ inv.total_amount }} {{ inv.currency }} ({{ inv.status }})
        {% endfor %}
        Kozvetlen review: {{ admin_url }}/verification
```

### 4.2 Konfidencia Alapu Routing

```
Extraction confidence >= 0.90:
  → AUTO-APPROVE
  → Fajl masolas cel mappaba
  → Ertesites: "Szamla automatikusan feldolgozva"

0.70 <= confidence < 0.90:
  → HUMAN REVIEW queue-ba
  → Ertesites: "Szamla review-ra var"
  → Reviewer jovahagyas/elutasitas

confidence < 0.70:
  → AUTO-REJECT
  → Ertesites: "Szamla feldolgozas sikertelen, manualis bevitel szukseges"
```

---

## 5. Technologiai Komponensek

### 5.1 Uj fajlok

| Fajl | Leiras |
|------|--------|
| `src/aiflow/services/document_extractor/schemas/` | Dokumentumtipus YAML schemak |
| `src/aiflow/services/document_extractor/free_text.py` | Szabad szoveges kinyeres modul |
| `src/aiflow/services/classifier/intent_schema.py` | Parameterezheeto intent schema loader |
| `src/aiflow/pipeline/adapters/data_router_adapter.py` | Data router adapter (filter + route) |
| `prompts/extraction/invoice_v2.yaml` | Szamla kinyeres prompt |
| `prompts/extraction/contract_v1.yaml` | Szerzodes kinyeres prompt |
| `prompts/extraction/free_text.yaml` | Szabad szoveges kinyeres prompt |
| `prompts/intent/invoice_schema.yaml` | Szamla intent schema |

### 5.2 Modositando fajlok

| Fajl | Modositas |
|------|-----------|
| `src/aiflow/services/document_extractor/service.py` | + `extract_free_text()`, + `validate_and_route()` methodok |
| `src/aiflow/services/classifier/service.py` | + `classify_with_schema()` method (intent schema parameter) |

### 5.3 DB bovitesek

```sql
-- Intent schema-k tarolasa (Alembic 029)
CREATE TABLE intent_schemas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    yaml_source TEXT NOT NULL,
    definition JSONB NOT NULL,
    team_id UUID REFERENCES teams(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Extraction history (audit trail)
CREATE TABLE extraction_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID,
    doc_type_config VARCHAR(255),
    extracted_fields JSONB,
    confidence FLOAT,
    status VARCHAR(20),  -- auto_approved, review_pending, reviewed, rejected
    reviewer VARCHAR(255),
    reviewed_at TIMESTAMPTZ,
    pipeline_run_id UUID REFERENCES workflow_runs(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Fejlesztesi Fazisok

| Fazis | Feladat | Fuggoseg |
|-------|---------|----------|
| **1** | DocumentTypeConfig bovites (threshold-ok, routing rules, output template) | Onallo |
| **2** | Free text extraction module | Phase 1 |
| **3** | Intent schema parameterization (YAML → DB, classify_with_schema) | Onallo |
| **4** | Data router service (filter + file move + routing rules) | Onallo |
| **5** | Invoice automation pipeline YAML | Phase 1-4 mind kesz |
| **6** | E2E teszt valos email-ekkel es szamlakkal | Phase 5 |

---

## 7. Verifikacio

### Valos use case teszt:
1. Outlook-bol email fetch (valos szamlakkal)
2. Intent classification → "invoice" (confidence >= 0.7)
3. PDF csatolmany kinyeres → Docling parse
4. Szamla adatok extract (vendor, amount, date, items)
5. Validation rules check (amount > 0, date valid)
6. Confidence >= 0.90 → auto-approve → file move
7. Ertesites email kuldes konyvelo@-nak
8. UI-ban latszik a feldolgozott szamla
