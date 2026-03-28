# AIFlow - 3 Skill Valosagos Fejlesztesi Pelda

Ebben a dokumentumban 3 valos skill fejlesztesenek teljes eletciklusat mutatjuk be,
a tervezestol a production adasig. Mindharom kulon team altal, parhuzamosan fejlesztheto.

---

## Skill 1: Process Documentation (Diagram Generator)
**Team:** AI Platform Team
**Komplexitas:** Medium (7 lepes, 1 ciklus)
**Becsult fejlesztes:** 3 het
**Becsult koltseg/futtatas:** $0.05-0.08

### 1.1 TERVEZES (1-2 nap)

**Kiindulas:** Meglevo POC (Process Doc AI Agent v1.2.0) adaptacioja.

**Claude Code hasznalat:**
```
User: "Tervezd meg a process-documentation skill-t az AIFlow keretrendszerben.
       A meglevo POC-bol (src/workflows/process_doc/) indulunk ki.
       DAG-alapu, quality gate-tel, max 3 refine iteracioval."
```

**Claude Code eredmenye - Workflow DAG terv:**

```
classify_intent ──┬── [process] ──→ elaborate ──→ extract ──→ review ──┬── [score>=8] ──→ generate_diagram ──┐
                  │                                                    │                  generate_table ───┤
                  │                                                    │                                    ↓
                  │                                                    +── [score<8] ──→ refine ──→ review  assemble_output
                  │                                                                     (max 3x)
                  ├── [greeting] ──→ respond_greeting
                  └── [off_topic] ──→ reject
```

**Specialist Agent-ek (5 db - 2-szintu szabaly: max 6):**

| Agent | Feladat | Model | ~Koltseg |
|-------|---------|-------|----------|
| ClassifierAgent | Intent klasszifikacio | GPT-4o-mini | $0.002 |
| ElaboratorAgent | BPMN terminologia bovites | GPT-4o | $0.015 |
| ExtractorAgent | Strukturalt adat kinyeres | GPT-4o | $0.020 |
| ReviewerAgent | Minosegi ellenorzes + scoring | GPT-4o | $0.010 |
| DiagramAgent | Mermaid kod generalas | GPT-4o-mini | $0.003 |

**Quality Gate definicio:**
- Extract utan: `completeness >= 0.80` -> ha nem: refine (max 3x) -> ha meg mindig nem: human_review
- Review: `score >= 8/10` -> ha nem: refine

### 1.2 ADATELEMZES (2-3 nap)

**Cel:** 100+ teszt eset osszegyujtese es elemzese.

**Adatforrasok:**
1. Meglevo POC teszt adatok (`tests/promptfoo/cases/`) - 27+13+12 = 52 eset
2. Belso uzleti folyamatok dokumentacioja (HR, penzugy, beszerzes)
3. Valodi user inputok a POC Chainlit logokbol

**Claude Code hasznalat:**
```
User: "Elemezd a meglevo teszt eseteket es generald le a hianyzo
       edge case-eket. Kell: tobb donisi pontot tartalmazo folyamatok,
       parhuzamos agak, magyar es angol nyelvu inputok, rosszul
       strukturalt szovegek."
```

**Eredmeny - 120 teszt eset katalogia:**

| Kategoria | Db | Pelda |
|-----------|-----|-------|
| Egyszeru linearis | 25 | "Szabadsag igenyles: keres -> jovahagyas -> nyilvantartas" |
| Tobb donisi pont | 20 | "Szamla jovahagyas: 100k alatt auto, felett vezetoigazgato" |
| Parhuzamos agak | 15 | "Berszamfejtes: HR bovites es berfutas parhuzamosan" |
| Rosszul strukturalt | 15 | "Hat szoval a kollegak bejonnek es mondjak hogy..." |
| Angol nyelvu | 15 | "Employee onboarding: IT setup, badge, orientation" |
| Elutasitando | 15 | "Mi a fo varosa Magyarorszagnak?" (off_topic) |
| Udvozles | 10 | "Szia! Tudsz segiteni?" (greeting) |
| Adversarial | 5 | Prompt injection kiserlet |

**Adattarolás:**
```
skills/process_documentation/tests/datasets/
    classification_120.json      # 120 teszt eset
    extraction_quality.json      # Elvart kimenet a minosegi ertekeleshez
```

### 1.3 FEJLESZTES (5-7 nap)

**Mappastruktura letrehozasa:**
```bash
aiflow skill new process_documentation --template medium_branching
```

**Generalt struktura:**
```
skills/process_documentation/
    skill.yaml
    __init__.py
    workflow.py
    agents/
        __init__.py
        classifier.py
        elaborator.py
        extractor.py
        reviewer.py
        diagram_generator.py
    models/
        __init__.py
        process.py           # ProcessExtraction, ProcessStep, StepType
    tools/
        diagram_renderer.py  # Kroki integracio
        table_generator.py   # MD/DOCX/XLSX
        drawio_exporter.py
    prompts/
        classifier.yaml
        elaborator.yaml
        extractor.yaml
        reviewer.yaml
        mermaid_flowchart.yaml
    tests/
        promptfooconfig.yaml
        test_classifier.py
        test_workflow.py
        datasets/
            classification_120.json
```

**Fejlesztesi sorrend:**

1. nap: Pydantic modellek (models/process.py) - POC-bol adaptacio
2. nap: Prompt YAML-ok irasa (prompts/) - POC-bol javitva
3. nap: Agent implementaciok (agents/) - @step decorator-ral
4. nap: Workflow DAG definicio (workflow.py) - elagazasok, quality gate
5. nap: Tools (diagram_renderer, table_generator) - POC-bol
6-7. nap: Tesztek es finomhangolas

**Claude Code hasznalat a fejlesztes kozben:**

```
# Nap 3 - Extractor Agent implementacioja
User: "Implementald az ExtractorAgent-et. Hasznalja a PromptManager-t
       a process-doc/extractor prompt betoltesere, instructor-ral
       strukturalt kimentet (ProcessExtraction modell), es szamolja
       ki a completeness score-t."

# Nap 4 - Workflow DAG
User: "Ird meg a workflow.py-t: classify -> branch -> elaborate ->
       extract -> review (quality gate 0.80) -> refine loop (max 3) ->
       parhuzamos generate_diagram + generate_table -> assemble_output"

# Nap 6 - Teszt generalas
User: "Generald le a Promptfoo config-ot a 120 teszt esetre.
       Assert-ek: is-json, contains, javascript assert a score-ra."
```

### 1.4 TESZTELES (3-5 nap)

**Szintek:**

**1. Unit tesztek (pytest)**
```bash
pytest skills/process_documentation/tests/test_classifier.py
# - ClassifierAgent helyes tipusokat ad vissza?
# - Greeting/off_topic helyesen szurve?
# - Edge case-ek kezelese (ures input, tul hosszu input)?
```

**2. Prompt tesztek (Promptfoo)**
```bash
aiflow prompt test --skill process_documentation
# Eredmeny:
#   classifier: 115/120 (95.8%)  <- CEL: >95%
#   elaborator: 18/20 (90%)      <- CEL: >85%
#   extractor:  85/100 (85%)     <- CEL: >80%
```

**3. Workflow integracio teszt**
```bash
aiflow eval run --skill process_documentation
# Teljes pipeline futtatas a 120 teszt eseten
# Eredmeny:
#   Overall pass rate: 92%
#   Avg latency: 11.2s
#   Avg cost: $0.062
#   Quality gate pass rate: 88%
#   Human review triggered: 4%
```

**4. Hiba esetek elemzese**
```
User: "Elemezd a 10 hibas teszt esetet. Mi a kozos minta?"

Claude Code:
- 4 eset: Tul rovid input -> extractor nem tud eleget kinyerni
  -> Javitas: elaborator prompt erosites rovid inputokra
- 3 eset: Nem magyarul irt -> classifier "off_topic"-nak veszi
  -> Javitas: classifier prompt bovites angol peldakkal
- 3 eset: Komplex elagazas -> extractor nem talalja az osszes donisi pontot
  -> Javitas: extractor prompt-ban tobb gateway pelda
```

**5. Iteracio: prompt javitas + ujrateszteles**
```bash
# Prompt frissites utan
aiflow prompt sync --skill process_documentation --label dev
aiflow eval run --skill process_documentation
# Uj eredmeny: 96% pass rate <- ELFOGADHATO
```

### 1.5 UAT es PROD ADAS (2-3 nap)

**UAT-ba leptetest:**
```bash
# Prompt-ok eloleptetese test -> staging
aiflow prompt promote --skill process_documentation --from dev --to staging

# Skill deploy a staging kornyezetbe
git tag v2.0.0-rc.1
git push origin v2.0.0-rc.1
# -> CI/CD pipeline deploy-ol staging K8s overlay-ra

# Stakeholder validacio: 5-10 valos folyamattal tesztelnek
# Feedback: "A HR folyamatoknal a donisi pont nev nem eleg leiro"
# -> Prompt javitas, rc.2
```

**Production adas:**
```bash
# Prompt-ok eloleptetese staging -> prod
aiflow prompt promote --skill process_documentation --from staging --to prod

# Release tag
git tag v2.0.0
git push origin v2.0.0
# -> CI/CD pipeline: blue-green deploy production K8s overlay-ra

# Monitoring (elso 24 ora):
# - Langfuse dashboard: latency, success rate, koltseg
# - Grafana: SLA compliance
# - Slack alert: ha success rate < 95%
```

---

## Skill 2: Vallalati ASZ Feldolgozo RAG Chat
**Team:** Legal Tech Team
**Komplexitas:** Large (12+ lepes, RAG pipeline, multi-turn)
**Becsult fejlesztes:** 5-6 het
**Becsult koltseg/futtatas:** $0.10-0.25 (RAG miatt tobb token)

### 2.1 TERVEZES (3-5 nap)

**Uzleti cel:** A vallalat ASZF-jeit (Altalanos Szerzodesi Feltetelek),
belso szabalyzatokat, jogszabalyokat tobb szaz oldalas dokumentumokbol
keresheto, kerdezheto formaban elerheto tenni RAG chat-en keresztul.

**Workflow DAG terv:**

```
receive_question ──→ classify_intent ──┬── [aszf_question] ──→ search_documents ──→ rerank ──→ generate_answer ──→ cite_sources ──→ quality_review ──┬── [pass] ──→ respond
                                       │                                                                                                             └── [fail] ──→ escalate_to_legal
                                       ├── [document_upload] ──→ ingest_document ──→ chunk ──→ embed ──→ store_vectors ──→ confirm_upload
                                       └── [off_topic] ──→ reject
```

**Specialist Agent-ek (6 db - max!):**

| Agent | Feladat | Model | Megjegyzes |
|-------|---------|-------|-----------|
| ClassifierAgent | Kerdes vs feltoltes vs off-topic | GPT-4o-mini | Gyors routing |
| SearchAgent | Vektor kereses + BM25 hybrid | Embedding model | Nem LLM, hanem embedding |
| RerankAgent | Talalatok ujrarangsrolasa | GPT-4o-mini | Cross-encoder |
| AnswerAgent | Valasz generalas RAG kontextussal | GPT-4o | Fo LLM hivas |
| CitationAgent | Forras hivatkozasok generalasa | GPT-4o-mini | Oldalszam, paragrafus |
| IngestAgent | Dokumentum feldolgozas + chunking | GPT-4o-mini | Szemantikus chunking |

**Kulonleges kovetelmeny: Multi-turn konverzacio**
- Az ExecutionContext.metadata-ban taroljuk a beszelgetes-tortenetet
- A SearchAgent figyelembe veszi a korabbi kerdeseket (conversational retrieval)

**Szukseges infrastruktura:**
- Vektor adatbazis: PostgreSQL + pgvector (vagy Qdrant/Weaviate)
- Embedding model: OpenAI text-embedding-3-small
- Dokumentum tarolás: S3 / lokalis fajlrendszer

### 2.2 ADATELEMZES (5-7 nap)

**Adatforrasok:**
1. Vallalati ASZF dokumentumok (PDF, DOCX) - 10-50 dokumentum
2. Belso szabalyzatok (HR, IT, penzugy)
3. Releváns jogszabalyok
4. Korabbi jogi kerdesek es valaszok (ha vannak)

**Claude Code hasznalat:**
```
User: "Elemezd az ASZF dokumentumok strukturajat. Milyen chunk meretet
       es overlap-et javasolsz? Milyen metadata-t kell kinyerni
       (fejezet szam, paragrafus, datum, hatalyossag)?"
```

**Dokumentum elemzes eredmeny:**

```
Dokumentum statisztikak:
- Osszes dokumentum: 35
- Osszes oldal: 2,400
- Atlagos dokumentum: 68 oldal
- Nyelv: 90% magyar, 10% angol

Javasolt chunking strategia:
- Chunk meret: 500-800 token (szemantikus chunk hatarak)
- Overlap: 100 token
- Metadata per chunk: {
    document_id, document_title, chapter, section,
    page_number, effective_date, language
  }
- Becsult chunk szam: ~12,000
- Embedding koltseg: ~$0.50 (egyszer, ingest soran)
```

**Teszt adatok - 150 kerdes-valasz par:**

| Kategoria | Db | Pelda |
|-----------|-----|-------|
| Egyszeru tenymegallpitas | 40 | "Mi a felmondasi ido a probaidoaban?" |
| Osszehasonlitas | 25 | "Mi a kulonbseg a rendes es a rendkivuli felmondas kozott?" |
| Szamitas / hataridok | 20 | "Mennyi szabadsag jar 10 ev munkavisszony utan?" |
| Multi-dokumentum | 20 | "Hogyan viszonyul a belso szabalyzat a Munka Torvenykonyvehez?" |
| Nincs valasz a dok-ban | 15 | "Mi a CEO telefonszama?" (-> "Nem talaltam a dokumentumokban") |
| Kovetkezo kerdes (multi-turn) | 20 | "Es mi van ha hatarozott ideju a szerzodes?" |
| Off-topic | 10 | "Mi lesz holnap az idojaras?" |

### 2.3 FEJLESZTES (10-15 nap)

**Mappastruktura:**
```
skills/aszf_rag_chat/
    skill.yaml
    __init__.py
    workflow.py                  # Fo kerdes-megvalszolas workflow
    ingest_workflow.py           # Dokumentum feldolgozo workflow (kulon!)
    agents/
        classifier.py
        search.py               # Hybrid search (vektor + BM25)
        rerank.py
        answer_generator.py
        citation.py
        ingest.py               # Dokumentum chunking + embedding
    models/
        document.py             # Document, Chunk, SearchResult
        conversation.py         # ConversationHistory, Turn
    tools/
        vector_store.py         # pgvector interface
        document_parser.py      # PDF/DOCX -> text
        embedder.py             # Embedding model wrapper
    prompts/
        classifier.yaml
        answer_generator.yaml   # RAG answer prompt (kontextus + kerdes)
        citation.yaml
        quality_reviewer.yaml
    tests/
        promptfooconfig.yaml
        test_search.py
        test_answer_quality.py
        test_workflow.py
        datasets/
            qa_150.json          # 150 kerdes-valasz par
            documents/           # Teszt dokumentumok
```

**Fejlesztesi sorrend:**

1-2. nap: Modellek (Document, Chunk, SearchResult, ConversationHistory)
3-4. nap: Ingest pipeline (PDF parser -> chunker -> embedder -> pgvector)
5-6. nap: Search + Rerank agent-ek (hybrid retrieval)
7-8. nap: Answer Generator + Citation agent-ek (RAG prompt)
9-10. nap: Classifier + Workflow DAG + multi-turn kontextus
11-12. nap: Quality review + escalation logic
13-15. nap: Tesztek + iteracio

**Kritikus fejlesztesi pont - RAG Answer Prompt:**

```yaml
# prompts/answer_generator.yaml
name: aszf/answer_generator
version: 1
description: "RAG valasz generalas ASZF dokumentumokbol"

system: |
  Vallalati jogi asszisztens vagy. KIZAROLAG az alabb megadott
  dokumentum-reszletek alapjan valaszolsz. Ha a valasz nem talalhato
  a megadott kontextusban, MONDD MEG hogy "A rendelkezesre allo
  dokumentumok alapjan erre a kerdesre nem tudok valaszolni."

  SOHA ne talald ki a valaszt! MINDIG hivatkozz a forrasra.

user: |
  ## Dokumentum kontextus:
  {% for chunk in context_chunks %}
  [Forras: {{ chunk.document_title }}, {{ chunk.chapter }}, {{ chunk.page_number }}. oldal]
  {{ chunk.text }}
  ---
  {% endfor %}

  ## Korabbi beszelgetes:
  {% for turn in conversation_history %}
  {{ turn.role }}: {{ turn.content }}
  {% endfor %}

  ## Aktualis kerdes:
  {{ question }}

config:
  model: openai/gpt-4o
  temperature: 0.1       # Alacsony - factual valasz kell
  max_tokens: 2000
```

### 2.4 TESZTELES (5-7 nap)

**Specialis RAG tesztek:**

```bash
# 1. Retrieval minoseg (nem LLM - gyorsabb, olcsobb)
aiflow eval run --skill aszf_rag_chat --suite retrieval
# Metriak:
#   Recall@5: 0.82 (a top 5 talalat kozott ott van a helyes forras?)
#   Recall@10: 0.91
#   MRR: 0.74 (atlagos reciprocal rank)

# 2. Valasz minoseg (LLM-alapu)
aiflow eval run --skill aszf_rag_chat --suite answer_quality
# Metriak:
#   Faithfulness: 0.93 (a valasz megfelel a kontextusnak?)
#   Relevance: 0.89 (a valasz relevans a kerdesre?)
#   Completeness: 0.85 (a valasz teljes?)
#   Citation accuracy: 0.91 (a hivatkozasok helyesek?)

# 3. "Nem tudom" esetek
aiflow eval run --skill aszf_rag_chat --suite no_answer
# Metrika: A rendszer helyesen mondja-e hogy "nem talaltam"
#   Precision: 0.95 (ha azt mondja "nem tudom", tenyleg nincs valasz?)
#   Recall: 0.80 (ha nincs valasz, felismeri-e?)

# 4. Multi-turn konverzacio
aiflow eval run --skill aszf_rag_chat --suite multiturn
# 20 konverzacio, 3-5 kerdes mindegyikben
# Metrika: A kovetkezo kerdesek helyes kontextusba helyezese
```

**Iteracios ciklus:**

```
1. kör: Retrieval recall@5 = 0.72 <- ALACSONY
   -> Javitas: chunk meret csokkentese 800 -> 500 token
   -> Javitas: hybrid search sulyzoas (vektor 0.6 + BM25 0.4)
   -> Eredmeny: recall@5 = 0.82

2. kör: Faithfulness = 0.85 <- ELFOGADHATO, DE JAVITHATO
   -> Javitas: answer prompt erosites ("KIZAROLAG a megadott kontextus alapjan")
   -> Javitas: temperature 0.2 -> 0.1
   -> Eredmeny: faithfulness = 0.93

3. kör: "Nem tudom" recall = 0.65 <- ALACSONY
   -> Javitas: confidence score hozzaadasa a valaszhoz
   -> Javitas: quality gate: ha confidence < 0.5 -> "nem talaltam"
   -> Eredmeny: recall = 0.80
```

### 2.5 UAT es PROD ADAS (3-5 nap)

**UAT:**
- 5 jogi kolleganak hozzaferes a staging rendszerhez
- 50 valos kerdessel tesztelnek
- Feedback: "A szerzodesi feltetelek szakaszat nem mindig talalja meg"
  -> Chunk metadata bovites szerzodestipussal
- Feedback: "Neha tul hosszu a valasz"
  -> Answer prompt: "Valaszolj tomoren, max 3-4 mondatban. Reszletekert hivatkozz a forrasra."

**Dokumentum ingest prod-ba:**
```bash
# 35 dokumentum feltoltese a production vektor adatbazisba
aiflow workflow run document-ingest --input '{"source_dir": "/docs/aszf/"}'
# Eredmeny: 12,340 chunk, ~$0.50 embedding koltseg
```

**Production monitoring specialis metriak:**
- Atlagos kontextus token count (RAG koltseg!)
- "Nem tudom" arany (tul magas = rossz retrieval, tul alacsony = hallucinacio)
- Felhasznaloi elegedettseg (thumbs up/down a chat-ben)

---

## Skill 3: Email Intent Feldolgozo
**Team:** Customer Service Team
**Komplexitas:** Small-Medium (5-8 lepes, elagazas, integracio)
**Becsult fejlesztes:** 2-3 het
**Becsult koltseg/futtatas:** $0.02-0.05

### 3.1 TERVEZES (1-2 nap)

**Uzleti cel:** Bejovo email-ek automatikus feldolgozasa:
szandek felismeres, kategorializalas, igenyfeldolgozashoz routing,
automatikus valasz draft keszitese.

**Workflow DAG terv:**

```
receive_email ──→ parse_email ──→ classify_intent ──┬── [complaint] ──→ extract_complaint_details ──→ create_ticket ──→ draft_response ──→ send_to_review_queue
                                                    ├── [inquiry] ──→ search_faq ──→ draft_response ──→ auto_respond (if confidence > 0.9)
                                                    ├── [order] ──→ extract_order_details ──→ validate_order ──→ forward_to_erp
                                                    ├── [invoice] ──→ extract_invoice_data ──→ forward_to_finance
                                                    └── [spam/irrelevant] ──→ archive
```

**Specialist Agent-ek (5 db):**

| Agent | Feladat | Model | ~Koltseg |
|-------|---------|-------|----------|
| EmailParserAgent | Email metaadat + body kinyeres | - (nem LLM) | $0.000 |
| IntentClassifierAgent | Szandek felismeres (5 kategoria) | GPT-4o-mini | $0.001 |
| DetailExtractorAgent | Reklamacio/rendeles reszletek | GPT-4o | $0.010 |
| FAQSearchAgent | FAQ adatbazis kereses | Embedding | $0.001 |
| ResponseDrafterAgent | Valasz tervezet keszitese | GPT-4o | $0.015 |

**Integracio pontok:**
- Bejovo email: Kafka topic `emails.incoming` VAGY webhook
- Kimeno: Kafka topic `tickets.created`, `orders.new`, `invoices.received`
- FAQ: pgvector adatbazis (hasonlo az ASZF RAG-hoz)
- ERP: REST API hivas (rendeles tovabbitas)

### 3.2 ADATELEMZES (3-4 nap)

**Adatforrasok:**
1. 3 honapnyi bejovo email (anonimizalva) - ~5,000 email
2. Meglevo kategorializas (ha van) - manualis cimkek
3. FAQ adatbazis
4. Reklamacios sablonok

**Claude Code hasznalat:**
```
User: "Elemezd az 5000 email mintat. Milyen intent kategoriak vannak?
       Milyen az eloszlas? Vannak tobbertelmű esetek?"
```

**Elemzes eredmeny:**

```
Email intent eloszlas (5000 email minta):
  complaint:    1,250 (25%) - Reklamacio, panasz
  inquiry:      1,750 (35%) - Altalanos erdeklodes, FAQ
  order:          750 (15%) - Rendeles, modositas, lemondas
  invoice:        500 (10%) - Szamlaval kapcsolatos
  spam/other:     750 (15%) - Spam, irrelevans

Specialis esetek:
  - Tobbertelmű (complaint + order): 150 (3%) -> elsodleges intent alapjan routing
  - Tobb nyelvu: 200 (4%) angol -> nyelv detektalas lepes kell?
  - Mellekklettel: 800 (16%) -> melleklet feldolgozas (v2-ben)
```

**Teszt adatok - 200 email:**

| Kategoria | Db | Megjegyzes |
|-----------|-----|-----------|
| Complaint - egyszeru | 30 | "A termek hibas volt..." |
| Complaint - komplex | 15 | Tobb problema, erzelmi toltes |
| Inquiry - FAQ | 35 | Szallitasi ido, garancia feltetelek |
| Inquiry - egyedi | 15 | Nem FAQ-ban levo kerdes |
| Order - uj | 20 | Rendeles leadasa email-ben |
| Order - modositas | 10 | Meglevo rendeles modositasa |
| Invoice - reklamacio | 15 | Hibas szamla |
| Invoice - kerdes | 10 | Fizetesi hataridok |
| Spam | 20 | Spam email-ek |
| Tobbertelmű | 15 | Complaint + inquiry egyben |
| Angol nyelvu | 15 | Angol nyelvu email-ek |

### 3.3 FEJLESZTES (5-8 nap)

```
skills/email_intent_processor/
    skill.yaml
    __init__.py
    workflow.py                # Fo email feldolgozo workflow
    agents/
        email_parser.py        # Nem LLM - regex + email lib
        intent_classifier.py   # GPT-4o-mini
        detail_extractor.py    # GPT-4o (complaint/order details)
        faq_search.py          # Embedding + vektor kereses
        response_drafter.py    # GPT-4o (valasz draft)
    models/
        email.py               # EmailMessage, ParsedEmail
        intent.py              # IntentClassification, Confidence
        ticket.py              # SupportTicket, OrderDetails
    prompts/
        intent_classifier.yaml
        detail_extractor.yaml
        response_drafter.yaml
    tests/
        datasets/
            emails_200.json
```

**Kulcsfontossagu prompt - Intent Classifier:**

```yaml
# prompts/intent_classifier.yaml
name: email/intent_classifier
version: 1

system: |
  Email intent klasszifikalo rendszer. Kategorizald a bejovo emailt.

  Kategoriak:
  - complaint: Reklamacio, panasz, termek/szolgaltatas hiba
  - inquiry: Kerdes, erdeklodes, informacio keres
  - order: Rendeles, modositas, lemondas
  - invoice: Szamlaval kapcsolatos (fizetesi kerdes, hibas szamla)
  - spam: Spam, irrelevans, automatikus valasz

  Ha az email tobb kategoriat is erint, az ELSODLEGES szandekot add meg,
  de jelold a masodlagos szandekot is.

user: |
  From: {{ sender }}
  Subject: {{ subject }}
  Body:
  {{ body }}

  Valasz JSON formatumban:
  {
    "primary_intent": "complaint|inquiry|order|invoice|spam",
    "secondary_intent": null | "...",
    "confidence": 0.0-1.0,
    "language": "hu|en",
    "urgency": "low|medium|high|critical",
    "summary": "1 mondatos osszefoglalas"
  }

config:
  model: openai/gpt-4o-mini
  temperature: 0.1
  response_format: {"type": "json_object"}
```

**Kafka integracio (trigger + publish):**

```python
# workflow.py
@workflow(
    name="email-intent-processing",
    version="1.0.0",
    skill="email_intent_processor",
    triggers=[
        EventTrigger(
            source="kafka",
            topic="emails.incoming",
            group_id="aiflow-email-consumer",
        ),
    ],
    publishes=[
        "tickets.created",      # Complaint -> ticket
        "orders.new",           # Order -> ERP
        "invoices.received",    # Invoice -> penzugy
    ],
)
def email_processing(wf: WorkflowBuilder):
    wf.step(parse_email)
    wf.step(classify_intent, depends_on=["parse_email"])
    wf.branch(
        on="classify_intent",
        when={
            "output.primary_intent == 'complaint'": ["extract_complaint"],
            "output.primary_intent == 'inquiry'": ["search_faq"],
            "output.primary_intent == 'order'": ["extract_order"],
            "output.primary_intent == 'invoice'": ["extract_invoice"],
        },
        otherwise="archive",
    )
    # Complaint ag
    wf.step(extract_complaint, depends_on=["classify_intent"])
    wf.step(create_ticket, depends_on=["extract_complaint"])
    wf.step(draft_response_complaint, depends_on=["create_ticket"])
    wf.step(publish_ticket, depends_on=["draft_response_complaint"])
    # Kafka: tickets.created

    # Inquiry ag
    wf.step(search_faq, depends_on=["classify_intent"])
    wf.step(draft_response_inquiry, depends_on=["search_faq"])
    wf.branch(
        on="draft_response_inquiry",
        when={"output.confidence >= 0.9": ["auto_respond"]},
        otherwise="send_to_review_queue",
    )
    wf.step(auto_respond, terminal=True)
    wf.step(send_to_review_queue, terminal=True)

    # Order ag
    wf.step(extract_order, depends_on=["classify_intent"])
    wf.step(validate_order, depends_on=["extract_order"])
    wf.step(publish_order, depends_on=["validate_order"])
    # Kafka: orders.new
```

### 3.4 TESZTELES (3-4 nap)

```bash
# Intent klasszifikacio
aiflow prompt test --skill email_intent_processor
# classifier: 188/200 (94%)

# Teljes pipeline
aiflow eval run --skill email_intent_processor
# Overall: 91%
# Per-intent:
#   complaint routing: 96%
#   inquiry + FAQ match: 85%  <- A FAQ kereses meg javithato
#   order extraction: 92%
#   invoice extraction: 90%
#   spam detection: 98%
# Avg latency: 3.2s
# Avg cost: $0.032
```

**Iteracio:**
- FAQ kereses javitasa (85% -> 90%): FAQ embedding ujrageneralas jobb chunk-olassal
- Tobb nyelvu tamogatas teszteles: angol email-ek 88% -> elfogadhato

### 3.5 UAT es PROD ADAS (2-3 nap)

**UAT:**
- Customer Service csapat 1 hetes tesztelese
- 100 valos email manualis athuzasa a rendszeren
- Feedback: "Az urgency mezo hasznos, de neha tulertekeli a surgesseget"
  -> Prompt javitas: urgency peldak pontositasa
- Feedback: "A valasz draft hangulata tul hivatalos"
  -> response_drafter prompt: "Baratságos, de szakszeru hangvetel"

**Production:**
```bash
# Kafka consumer inditasa
# emails.incoming topic-rol automatikusan olvassa az email-eket
# Feldolgozas: ~3 mp/email, ~$0.03/email

# Napi 200 email eseten:
# Napi koltseg: ~$6
# Havi koltseg: ~$180
# Megtakaritas: ~80 ora/ho emberi kategorializas
```

---

## Parhuzamos Fejlesztes Osszefoglalo

```
Het 1-2:   [Skill 1: Tervezes+Adat]  [Skill 2: Tervezes]        [Skill 3: Tervezes]
Het 3-4:   [Skill 1: Fejlesztes]     [Skill 2: Adat+Fejlesztes]  [Skill 3: Adat]
Het 5-6:   [Skill 1: Teszt+UAT]      [Skill 2: Fejlesztes]       [Skill 3: Fejlesztes]
Het 7-8:   [Skill 1: PROD]           [Skill 2: Fejlesztes+Teszt]  [Skill 3: Teszt]
Het 9-10:                             [Skill 2: UAT+PROD]          [Skill 3: UAT+PROD]
```

**Fuggossegek a skill-ek kozott:** NINCS! Mindharom teljesen fuggetlenul fejlesztheto,
kulonbozo team-ek altal, sajat CI/CD pipeline-nal.

**Kozos infrastruktura:** AIFlow framework + PostgreSQL + Redis + Langfuse
- Skill 2 es 3 kozos: pgvector (de kulon collection-ok)
- Skill 3: Kafka (ha a vallalatnl van Kafka infrastruktura)

**Osszes koltseg a 3 skill production-ben:**
| Skill | Napi futtatas | Koltseg/db | Napi koltseg | Havi koltseg |
|-------|---------------|------------|--------------|--------------|
| Process Doc | ~50 | $0.06 | $3 | $90 |
| ASZF RAG | ~200 | $0.15 | $30 | $900 |
| Email Intent | ~200 | $0.03 | $6 | $180 |
| **Osszes** | **~450** | | **$39** | **$1,170** |
