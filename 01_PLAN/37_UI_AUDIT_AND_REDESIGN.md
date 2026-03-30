# AIFlow UI — Full Audit + Redesign Plan

> **Datum:** 2026-03-30
> **Cel:** Oszinte audit a jelenlegi UI + framework allapotarol, majd egyseges, logikus UI ujratervezes.

---

## 1. ARCHITEKTURA — A VALOSAG

### 1.1 Mi mukodik tenylegesen

```
                        +-----------------+
                        |   Next.js UI    |   11 oldal, 52 komponens
                        |   (localhost:3000)|   shadcn/ui + Tailwind
                        +-------+---------+
                                |
                    +-----------+-----------+
                    |                       |
              fetchBackend()          subprocess
              (3s timeout)        (python -m skills.X)
                    |                       |
                    v                       v
            +-------+-------+     +---------+---------+
            |  FastAPI API  |     |  Skill CLI (__main__|
            |  (localhost:8000)   |   .py)             |
            |  TOBBNYIRE STUB|    |  4/6 MUKODIK       |
            +-------+-------+    +---------+---------+
                    |                       |
                    v                       v
            +-------+-------+     +---------+---------+
            |  SkillRunner  |     |  SkillRunner      |
            |  (szekvencialis)|   |  (szekvencialis)   |
            +-------+-------+    +---------+---------+
                    |                       |
          +---------+---------+   +---------+---------+
          | ModelClient       |   | PromptManager     |
          | (LiteLLM backend) |   | (YAML + Jinja2)   |
          +---------+---------+   +---------+---------+
                    |                       |
                    v                       v
            OpenAI / Claude          skills/X/prompts/
            (valos LLM hivasok)      (YAML fajlok)
```

### 1.2 Reteg-statusz (oszinte)

| Reteg | Allapot | Reszletek |
|-------|---------|-----------|
| **Engine (step, DAG, workflow)** | 100% KESZ | @step decorator, DAGExecutor, WorkflowBuilder, retry/timeout — mind implementalva |
| **SkillRunner** | MUKODIK, de korlatos | Szekvencialis vegrehajtás. NEM hasznalja a DAG-ot, NEM branch-el |
| **ModelClient + LiteLLM** | 100% KESZ | generate(), embed(), Instructor strukturalt output, koltseg-kovetes |
| **PromptManager** | 95% KESZ | YAML + Jinja2 + cache. Langfuse placeholder (nem bekotve) |
| **VectorStore (pgvector)** | 100% KESZ | Hybrid search: vektor HNSW + BM25 tsvector + RRF osszefuzes |
| **FastAPI API** | ~20% | Endpointok leteznek, de a /v1/chat/completions az egyetlen ami tenyleg skill-t hiv |
| **Execution (queue/worker)** | ~5% | InMemoryJobQueue skeleton. Nincs arq/Redis, nincs DAG runner |
| **Security** | DEV-ONLY | HMAC JWT (nem RS256), hardcoded secret, nincs production |
| **Next.js UI** | ~70% | 11 oldal mukodik, de inkonzisztens UX, kevert i18n |

### 1.3 Skill-statuszok (oszinte)

| Skill | Allapot | Mi mukodik | Mi nem |
|-------|---------|-----------|--------|
| **process_documentation** | PRODUCTION | Mind a 6 step (classify→elaborate→extract→review→generate→export), DrawIO, SVG, Mermaid | — |
| **aszf_rag_chat** | PRODUCTION | Query (7 step) + Ingest (6 step), pgvector hybrid search, 86% eval | — |
| **cubix_course_capture** | PRODUCTION | Transcript pipeline (ffmpeg→Whisper→LLM), RPA (Robot+Playwright) | Csak CLI-bol inditható |
| **email_intent_processor** | IN DEVELOPMENT | 7 step implementalva, sklearn+LLM hybrid, schema-driven | Nem tesztelt nagyban |
| **invoice_processor** | 10% KESZ | Csak parse_invoice step mukodik (Docling), tobbi STUB | extract/validate/store/export mind stub |
| **qbpp_test_automation** | STUB | Nincs __main__.py | Semmi |

---

## 2. UI AUDIT — JELENLEGI ALLAPOT

### 2.1 Oldalak osszefoglalasa

| Oldal | Tipus | Adat forras | Funkcionalis? | UX minoseg |
|-------|-------|-------------|---------------|------------|
| **/** (Dashboard) | Osszesito | runs.json | Igen | Jo — tiszta, egyszeru |
| **/costs** | Riport | runs.json (aggregalt) | Igen | Jo — jol strukturalt |
| **/runs** | Lista + SSE | runs.json + stream | Igen | Jo — live toggle |
| **/runs/[id]** | Reszletes | runs.json (szurt) | Igen | Jo — timeline + detail |
| **/skills/process_documentation** | Viewer + Input | subprocess/mock | Igen | Kozepes — kevert |
| **/skills/aszf_rag_chat** | Chat + Trace | backend/mock SSE | Igen | Kozepes — szuk mobil |
| **/skills/email_intent_processor** | Viewer + Upload | mock + subprocess | Reszben | Gyenge — zavaros UX |
| **/skills/invoice_processor** | Upload + Batch | subprocess + mock | Igen | Gyenge — i18n hianyzik |
| **/skills/cubix_course_capture** | Read-only viewer | filesystem/mock | Igen | Kozepes — nincs empty state |

### 2.2 Kritikus UI problemak

#### A) Inkonzisztens layout-ok
Minden viewer mas elrendezesu:
- **Process Docs:** Input felul → KPIs → Tabs (Diagram/Review/Pipeline/Gallery)
- **RAG Chat:** Chat bal oldalon (3/5) + Tabs jobb (2/5)
- **Email:** KPIs felul → Filters → Table bal (1/2) + Detail jobb (1/2)
- **Invoice:** Upload → KPIs → Batch banner → Filters + Table
- **Cubix:** KPIs → Tabs (Pipeline/Structure/Results)

> **Problema:** A felhasznalo minden oldalon mas mentalitast tanul. Nincs egyseges minta.

#### B) Hardcoded Hungarian stringek (i18n serules)
**Sulyos serulesek (ossz: ~25 hardcoded string):**

| Fajl | Serules szama | Pelda |
|------|--------------|-------|
| `invoice/upload-zone.tsx` | 6 | "Feltoltes folyamatban...", "Huzd ide a PDF fajlokat" |
| `invoice/document-detail.tsx` | 15+ | "SZALLITO", "VEVO", "Szamlaszam", "Tetelek" |
| `invoice_processor/page.tsx` | 8 | "Dokumentumok", "Batch feldolgozas", "Osszes ido" |
| `page-state.tsx` | 3 | "Betoltes...", "Ujraprobalkozas", "Nincs adat" |
| API route-ok | 4 | "Backend nem elerheto", "A RAG backend jelenleg..." |

#### C) Zavaros viewer statuszok
- **Invoice:** A "legkeszebb" UI, de a mogotte levo skill 10%-os → szep felulet, stub backend
- **Email:** Van upload zone, van process gomb, de a skill in-development → nem tudjuk mi tortenik
- **Cubix:** "Results Viewer" — helyes, de a felhasznalo nem erti miert nem tud inputot adni
- **Process Docs:** A legosszeszedettebb (subprocess mukodik), de a badge rendszer uj es nem konzisztens

#### D) Hianyzo allapotok
- Nincs **empty state** ha nincs adat (Cubix, Email)
- Nincs **onboarding** — uj felhasznalo nem erti mit csinaljon
- Nincs **skill status overview** — melyik skill mukodik es melyik demo?
- A **Pipeline tab** uj, de az adatai szintetikusak (nem valos duration/cost)

---

## 3. AI WORKFLOW BELSO MUKODESE

### 3.1 A Step → SkillRunner lánc

```
User Input (szoveg/fajl)
    |
    v
__main__.py (CLI)
    |
    v
SkillRunner.from_env(model, prompt_dirs)
    |   - Letrehozza: ModelClient (LiteLLM), PromptManager (YAML)
    v
runner.run_steps([step1, step2, ...], initial_data)
    |
    |   Minden step-re:
    |   1. data = await step_fn(data)     ← @step decorator kezeli retry/timeout
    |   2. Az output dict merged az inputtal → kovetkezo step inputja
    |   3. structlog naploz
    v
Vegso result dict (minden step outputja osszegyujtve)
```

### 3.2 Egy konkret pelda: Process Documentation

```
User: "Szabadsag igenyeles folyamata"
        |
        v
  classify_intent(data)
  ├── Prompt: process-doc/classifier.yaml
  ├── LLM: gpt-4o-mini → ClassifyOutput {category: "process", confidence: 0.95}
  └── Output: {category: "process", confidence: 0.95}
        |
        v
  elaborate(data)
  ├── Prompt: process-doc/elaborator.yaml
  ├── LLM: gpt-4o-mini → bovitett szoveg
  └── Output: {elaborated_input: "A szabadsag igenyeles reszletes..."}
        |
        v
  extract(data)
  ├── Prompt: process-doc/extractor.yaml
  ├── LLM: gpt-4o-mini → ProcessExtraction (structured)
  └── Output: {extraction: {title, actors[], steps[], start_step_id}}
        |
        v
  review(data)
  ├── Prompt: process-doc/reviewer.yaml
  ├── LLM: gpt-4o-mini → ReviewOutput (structured)
  └── Output: {review: {score: 8, is_acceptable: true, ...}}
        |
        v
  generate_diagram(data)
  ├── Prompt: process-doc/mermaid_flowchart.yaml
  ├── LLM: gpt-4o-mini → Mermaid forráskod
  └── Output: {mermaid_code: "graph TD\n  A[Start]-->B[...]"}
        |
        v
  export_all(data)
  ├── Menti: diagram.mmd, extraction.json, review.json
  ├── DrawioExporter → diagram.drawio + diagram_bpmn.drawio
  ├── KrokiRenderer → diagram.svg (ha Kroki elerheto)
  └── Output: {saved_files: [...], export_dir: "output/szabadsag_igenyeles/"}
```

### 3.3 Hogyan csatlakozik a UI

```
Next.js UI Page
    |
    | POST /api/process-docs/generate {user_input: "..."}
    v
API Route (route.ts)
    |
    ├── 1. fetchBackend() → FastAPI /api/v1/workflows/... (3s timeout, altalaban FAIL)
    |
    ├── 2. execFileAsync(python, ["-m", "skills.process_documentation", "--input", ...])
    |       → 120s timeout
    |       → Olvas: diagram.mmd, extraction.json, review.json
    |       → source: "subprocess"
    |
    └── 3. Mock: template clone → source: "demo"

    v
Response: ProcessDocResult + source tag
    |
    v
Page: DiagramPreview (Mermaid render) + ReviewScores + Badge (Live/Demo)
```

### 3.4 Skill fejlesztes menedzselese

**Jelenlegi fejlesztesi ciklus:**
1. **Prompt irasa** — `skills/X/prompts/*.yaml` (Jinja2 template + config)
2. **Step implementalas** — `skills/X/workflows/*.py` (@step decorator)
3. **CLI teszteles** — `python -m skills.X --input "..." --output ./out`
4. **Prompt teszteles** — `npx promptfoo eval -c skills/X/tests/promptfooconfig.yaml`
5. **Unit tesztek** — `pytest tests/unit/skills/test_X.py`
6. **UI bekotes** — API route + page komponens

**Hianyzo fejlesztesi eszkozok:**
- Nincs automatikus skill-status riport (melyik step mukodik, melyik stub)
- Nincs prompt verzio-kovetes (Langfuse placeholder)
- Nincs end-to-end teszt a UI → subprocess → skill lancon
- Nincs koltseg-monitoring a fejlesztes soran (Langfuse kellene)

---

## 4. UJRATERVEZESI JAVASLAt

### 4.1 Design elvek

1. **Egy elrendezes, minden viewer-nek** — kozos layout minta
2. **Oszinte statusz mindig** — skill card mutatja: Production / In Development / Demo
3. **Input elol, eredmeny utana** — logikus flow felulrol lefele
4. **Pipeline mindig lathato** — nem rejtett tab-ban, hanem a feldolgozas resze
5. **i18n 100%** — nulla hardcoded string

### 4.2 Javasolt egyseges viewer layout

```
+------------------------------------------------------------------+
| [Skill neve]                                    [Status badge]    |
| [Rovid leiras]                                  [Source: Live/Demo]|
+------------------------------------------------------------------+
|                                                                    |
| +-- INPUT ZONA ---------------------------------------------------+|
| | [Skill-specifikus input: text area / file upload / chat]        ||
| | [Generate / Process / Send gomb]                                ||
| +----------------------------------------------------------------+|
|                                                                    |
| +-- KPIs (max 4-5) -----------------------------------------------+|
| | [Metric 1] [Metric 2] [Metric 3] [Metric 4]                   ||
| +----------------------------------------------------------------+|
|                                                                    |
| +-- PIPELINE TRACE (egyseges ProcessingPipeline) -----------------+|
| | step1 ✓ → step2 ✓ → step3 ▶ → step4 ○ → step5 ○              ||
| | [source badge] [duration] [cost] [tokens]                      ||
| +----------------------------------------------------------------+|
|                                                                    |
| +-- RESULT TABS --------------------------------------------------+|
| | [Primary Output] [Details] [History/Gallery]                    ||
| |                                                                 ||
| | (Skill-specifikus tartalom a tabokban)                          ||
| +----------------------------------------------------------------+|
+------------------------------------------------------------------+
```

### 4.3 Teendo lista

#### A) i18n cleanup (1 session)
- [ ] `invoice/upload-zone.tsx` — 6 string → i18n
- [ ] `invoice/document-detail.tsx` — 15+ string → i18n
- [ ] `invoice_processor/page.tsx` — 8 string → i18n
- [ ] `page-state.tsx` — 3 string → i18n
- [ ] API route error messages → angol, UI fordit
- [ ] Vitest i18n coverage teszt bovites

#### B) Egyseges viewer layout (2-3 session)
- [ ] Kozos `SkillViewerLayout` wrapper komponens
- [ ] Minden viewer atiras az egységes layoutra:
  - Input zona (felul)
  - KPIs (alatta)
  - Pipeline trace (kozepen) — mar van ProcessingPipeline
  - Result tabs (alul)
- [ ] Source badge + skill status egyseges elhelyezese

#### C) Oszinte skill statusz (1 session)
- [ ] Dashboard skill card-ok: valos statusz badge
- [ ] Sidebar: szinjeloles (zold=Production, kek=InDev, szurke=Stub)
- [ ] Skills oldal: mi mukodik, mi nem, mit var a felhasznalo

#### D) Pipeline trace valos adatokkal (1-2 session)
- [ ] SkillRunner: step timing + cost logging stdout-ra
- [ ] API route-ok: stdout parsing → valos step idok
- [ ] ProcessingPipeline: valos duration/cost/tokens megjelenites

#### E) Hianyzo allapotok (1 session)
- [ ] Empty state minden oldalon
- [ ] Onboarding hint uj felhasznalonak
- [ ] Error state egysegesites
- [ ] Loading skeleton (nem csak spinner)

#### F) Mobil / responsive (1 session)
- [ ] RAG Chat: single-column mobil nezet
- [ ] Email: stacked layout mobil
- [ ] Invoice: responsive table

### 4.4 Vegrehajtasi sorrend

```
Session 1: i18n cleanup (A) — minden hardcoded string → i18n
Session 2: SkillViewerLayout komponens + Process Docs atiras (B)
Session 3: Tobbi viewer atiras az egységes layoutra (B)
Session 4: Oszinte skill statusz + Pipeline valos adatok (C+D)
Session 5: Empty state + onboarding + responsive (E+F)
```

---

## 5. VIZUALIS REFERENCIA MINTAK

### 5.1 Hasonlo rendszerek UX mintai

**Langfuse Dashboard** — prompt monitoring
- Bal sidebar: navigacio
- Fo terulet: metric cards felul, table alul
- Detail: idovonal + metadata

**Retool / Superblocks** — internal tools
- Header: title + action buttons
- Body: form → results → table

**Vercel Dashboard** — deployment monitoring
- Status badges mindenhol
- Egyseges card design
- Pipeline: build → deploy → live (horizontal)

**Javasolt irany:** A Vercel-fele minimalista pipeline + a Langfuse-fele metrikus dashboard kevereke. Tiszta, egyseges, minden helyen ugyanaz a visual language.

---

## 6. OSSZEFOGLALAS

### Mi van keszen es jo?
- 4/6 skill **tenylegesen mukodik** (nem demo)
- A subprocess minta **megbizhato** (Process Docs, Invoice, Email)
- A source badge rendszer **oszinte** (Demo/Live/Subprocess)
- Az engine reteg **teljes** (@step, DAG, WorkflowBuilder)

### Mi a fo problema?
1. **Vizualis inkonzisztencia** — minden viewer mas
2. **Kevert i18n** — ~25 hardcoded Hungarian string
3. **Hamis benyomas** — az Invoice UI "kesz" tun, de a skill 10%-os
4. **Pipeline trace szintetikus** — nincs valos timing/cost adat
5. **Nincs egyseges skill-status kommunikacio**

### Mi a cel?
> Egy felhasznalo aki eloszor latja az appot, 10 masodperc alatt ertse:
> - Melyik skill mukodik (zold), melyik fejlesztes alatt all (kek), melyik demo (sarga)
> - Mit tud csinalni az adott oldalon (input → process → output)
> - Honnan jon az adat (backend/subprocess/demo)
