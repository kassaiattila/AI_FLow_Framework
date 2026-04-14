# AIFlow Sprint B — Session 31 Prompt (B6: Portal Struktura Ujragondolas + 4 User Journey Tervezes)

> **Datum:** 2026-04-10
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `c7079c6`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S30 — B5 DONE (diagram hardening + spec_writer UJ skill + cost baseline, 4 commit: 11364cd + a77a912 + 41d3e60 + c7079c6, 1442 unit / 96 promptfoo / 105 E2E, 0 regresszio, diagram_generator 8/10 + spec_writer 9/10 PRODUCTION-READY)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B6 szekcio, sor 1313-1553)
> **Session tipus:** DESIGN-FIRST — NINCS kodvaltoztatas, csak tervezes + wireframe + dokumentacio
> **Workflow:** Terv elkeszites (LEPES 1-6) → VALIDACIO 1. kor (LEPES 7) → JAVITAS 1. kor (LEPES 8) → VALIDACIO 2. kor (LEPES 9) → JAVITAS 2. kor (LEPES 10) → Commit + KESZ jelentes (LEPES 11)

---

## KONTEXTUS

### S30 Eredmenyek (B5 — DONE, 4 commit)

**B5.1 — Diagram Generator Hardening (`11364cd`):**
- `DiagramGeneratorService.generate()` uj `diagram_type` param (flowchart | sequence | bpmn_swimlane)
- `SUPPORTED_DIAGRAM_TYPES` whitelist, unknown types fallback flowchart-ra
- 3 UJ service prompt: `diagram_planner.yaml` + `mermaid_generator.yaml` + `diagram_reviewer.yaml`
- `diagram_generator_v1.yaml` pipeline template (1 step, service=diagram_generator method=generate)
- `diagram_adapter.py` BUG-javitas: `getattr(result, "id", "")` (nem `diagram_id`!) + `svg_content` None→"" coerce
- 11 unit teszt (5 original + 6 uj: sequence, swimlane, adapter_passes_type, reviewer_auto_fix, invalid_type_fallback + SUPPORTED_DIAGRAM_TYPES whitelist)
- 3 uj E2E scenario EGY comprehensive test methoban (asyncpg multi-loop workaround!)
- 7/7 promptfoo test = **100%** (flowchart_basic/decision, sequence_auth/retry, swimlane_onboard/cross, invalid_fallback)
- Service-hardening **8/10 PRODUCTION-READY**

**B5.2 — Spec Writer UJ Skill (`a77a912`, 18 uj fajl!):**
- `skills/spec_writer/` — skill.yaml + skill_config.yaml + __init__.py + __main__.py CLI (argparse)
- `models/__init__.py` — 5 Pydantic: SpecInput, SpecField, SpecRequirement, SpecDraft, SpecReview, SpecOutput
- 3 prompt: `spec_analyzer.yaml` (raw → structured req JSON) + `spec_generator.yaml` (req → markdown) + `spec_reviewer.yaml` (markdown → 0-10 score)
- `workflows/spec_writing.py` — 5 step DAG (`@step analyze` → `select_template` → `generate_draft` → `review_draft` → `finalize`), module-level `_models` + `_prompts` singletonok (tesztelheto monkey-patch-csel)
- Pipeline: `spec_writer_v1.yaml` template + `spec_writer_adapter.py` (service=spec_writer method=write)
- DB: `alembic/versions/030_add_generated_specs.py` (id, input_text, spec_type, language, title, markdown_content, requirement JSONB, review JSONB, score, is_acceptable, sections_count, word_count, created_by, created_at, updated_at)
- API: `src/aiflow/api/v1/spec_writer.py` — POST /write + GET list/single + DELETE + GET export?fmt=markdown|html|json (python-markdown wrapped HTML)
- UI: `aiflow-admin/src/pages-new/SpecWriter.tsx` — textarea + spec_type dropdown + language dropdown + Generate button + markdown preview + download + saved specs DataTable, router route `/spec-writer`, HU + EN i18n keys
- 7 unit teszt (mock LLM via `monkeypatch.setattr(spec_writing, '_models', fake)`)
- 8/8 promptfoo (100%) — router prompt pattern `task=generate|review`, explicit per-spec_type heading enforcement

**B5.3 — Cost Baseline (`41d3e60`):**
- `scripts/cost_baseline.py` — async asyncpg aggregator (per-service + per-model + per-day) + threshold warnings + gpt-4o → gpt-4o-mini recommendations
- `01_PLAN/COST_BASELINE_REPORT.md` — generalt: 14 rekord, 11 run, $0.1931, gpt-4o 95% spend, bpmn_generation 62% per-service spend
- Langfuse cross-check dokumentalva

**B5 cleanup (`c7079c6`):**
- `spec_writer.py` asyncpg pool → shared `aiflow.api.deps.get_pool()` (TestClient multi-loop fix)
- `skills/spec_writer/guardrails.yaml` (PII allowlist email, injection detection on, max_length 20000, dangerous_patterns)
- `01_PLAN/58` + `01_PLAN/CLAUDE.md` + root `CLAUDE.md` kulcsszamok frissites
- 3 uj memory record: asyncpg_pool_event_loop + diagram_adapter_record_id + kroki_renderer_bytes

**Infrastruktura (v1.3.0 — S30 utan):**
- 27 service | 170 API endpoint (26 router) | 47 DB tabla | 30 migracio
- 22 pipeline adapter | 9 pipeline template | 7 skill | 23 UI oldal
- **1442 unit test** | 129 guardrail teszt | 97 security teszt | **105 E2E** | **96 promptfoo test** (6 skill 95%+, diagram_generator service 100%)

### Jelenlegi Allapot (B6 cel — Portal UJRATERVEZESE, NEM implementalas)

```
=== B6 KONTEXTUS: MI A PROBLEMA? ===

A portal JELENLEGI navigacio (aiflow-admin/src/layout/AppShell.tsx + router.tsx):
  Dashboard
  OPERATIONS: Runs | Costs | Monitoring | Quality
  DATA: Documents | Emails
  AI SERVICES: RAG | Process Docs | Media | RPA | Reviews | Cubix
  ORCHESTRATION: Services | Pipelines
  ADMIN: Admin | Audit
  AUTH: Login

23 oldal (SpecWriter a B5.2 utan!), TECHNIKAI csoportositas (service-orientalt). 
PROBLEMA: a felhasznalo NEM "szolgaltatasokat" vagy "operaciokat" akar latni,
hanem FELADATOT akar vegrehajtani: "szamlat akarok feldolgozni", "diagramot
generalok", "tudasbazisbol kerdezek", "megnezem mi megy a rendszerben".

A jelenlegi navigacioban:
  - A felhasznalo SOHA nem talalja meg egybol a funkciokat
  - /emails + /documents + /reviews + /verification KULON oldalak,
    pedig EGY journey reszei (invoice feldolgozas)
  - /services + /pipelines lathato felso nav-ban, pedig ezek INFRASTRUCTURE
    view-ok, nem felhasznaloi funkciok
  - A dashboard NEM mutat journey-t, csak altalanos KPI-kat
  - NINCS breadcrumb, nincs "hol vagyok a folyamatban?" jelzes
  - RPA + Cubix (demo) egyenrangu a Invoice-szel a navban — osszezavarja a usert

B6 CEL: NEM oldalak implementalasa, NEM kodvaltoztatas, hanem:
  1. Teljes 23 oldal AUDIT (mi mukodik, mi demo, mi halott)
  2. UJ Information Architecture (IA) — journey-based navigacio tervezes
  3. 4 fo user journey reszletes definicioja (entry → lepesek → expected kimenet)
  4. Holisztikus user journey map (EGY kep az egesz portalrol)
  5. Figma wireframe az uj sidebar navigaciorol + dashboard kartyakrol
  6. Demo → backend migracios priorizalt terv (mit B8-ban implementalni)

B6 KIMENET: EGY dokumentum — `01_PLAN/63_UI_USER_JOURNEYS.md`
  + Figma frame-ek (Dashboard + Sidebar wireframe)
  + PAGE_SPECS.md update (journey mapping hozzaadas)

B6 UTAN (B7 + B8):
  S32: B7 — Verification Page v2 (bounding box, confidence, diff) — egy oldal deep dive
  S33: B8 — UI Journey implementacio — az uj navigacio ELO, Journey 1 + 2 mukodik
  B6-B7-B8 EGYUTT a teljes UI modernizacio, de S31 CSAK a TERVEZES.

=== B6 ALREADY EXISTS CHECK (mit ne csinaljunk ujra!) ===

LETEZO design dokumentumok:
  aiflow-admin/figma-sync/PAGE_SPECS.md  (1222 sor — per-page Figma + spec)
  aiflow-admin/figma-sync/REDESIGN_PLAN.md  (283 sor — redesign strategy)
  aiflow-admin/figma-sync/PIPELINE.md  (figma-to-code pipeline)
  aiflow-admin/figma-sync/UNTITLED_UI_AGENT.md  (agent config)
  aiflow-admin/figma-sync/config.ts  (Figma API config)

LETEZO per-phase journey dokumentumok (legacy F1-F6 sprintbol):
  01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md
  01_PLAN/F2_EMAIL_CONNECTOR_JOURNEY.md
  01_PLAN/F3_RAG_ENGINE_JOURNEY.md
  01_PLAN/F4_RPA_MEDIA_DIAGRAM_JOURNEY.md
  01_PLAN/F5_MONITORING_GOVERNANCE_JOURNEY.md
  01_PLAN/F6_UI_RATIONALIZATION_JOURNEY.md
  01_PLAN/PIPELINE_UI_JOURNEY.md
  01_PLAN/QUALITY_DASHBOARD_JOURNEY.md
  01_PLAN/SERVICE_CATALOG_JOURNEY.md

Ezeket NE toroljuk, csak OLVASSUK referenciakent. B6 az F1-F6 munka
OSSZEVONASA egy koherens 4-journey IA-ba.

LETEZO UI implementacio (amit NE bantsunk B6-ban):
  aiflow-admin/src/pages-new/*.tsx  (23 oldal — SpecWriter.tsx B5.2 utan!)
  aiflow-admin/src/layout/AppShell.tsx  (jelenlegi sidebar)
  aiflow-admin/src/router.tsx  (jelenlegi routes)

NINCS meg:
  01_PLAN/63_UI_USER_JOURNEYS.md  ← EZ A B6 FO KIMENETE!
```

---

## B6 FELADAT: 11 lepes — Portal IA ujratervezes + 4 journey + wireframe + 2x validacio

> **Gate:** `01_PLAN/63_UI_USER_JOURNEYS.md` letezik 6 szekcioval (audit + IA + map + 4 journey + wireframe + migrations), KETSZER validalva a `plan-validator` subagenttel.
> `aiflow-admin/figma-sync/PAGE_SPECS.md`-ben minden 23 oldalhoz hozzarendelt journey.
> Figma MCP-vel 2 uj wireframe frame (uj sidebar + dashboard 4-kartya).
> **Workflow:** LEPES 1-6 (terv elkeszites) → LEPES 7 (validacio 1) → LEPES 8 (javitas 1) → LEPES 9 (validacio 2) → LEPES 10 (javitas 2) → LEPES 11 (commit + kesz jelentes)
> **Eszkozok:** `/ui-journey`, Figma MCP (generate_diagram + create_frame + create_text), Agent(subagent_type=plan-validator), Read, Edit, Write
> **TILOS:** `.tsx` fajl szerkesztese, `router.tsx` modositasa, UI oldalak kodvaltoztatasa. Ez a session CSAK TERVEZES.

---

### LEPES 1: B6.1 — Portal Struktura Audit (23 oldal, jelenlegi allapot)

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (UJ fajl, elso szekcio)
     Olvasnivalok: aiflow-admin/src/pages-new/*.tsx (mind a 22!)
                   aiflow-admin/src/router.tsx
                   aiflow-admin/src/layout/AppShell.tsx
                   aiflow-admin/figma-sync/PAGE_SPECS.md
                   01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md (sor 1320-1362)

Cel: Minden 23 oldalhoz egy audit sor, 8 oszloppal.

KONKRET TEENDOK:

1. Olvasd be a 23 oldal forrasat EGYMAS UTAN (Glob + Read):
   - Dashboard.tsx, Documents.tsx, DocumentDetail.tsx, Verification.tsx,
     Emails.tsx, Runs.tsx, Costs.tsx, Monitoring.tsx, Quality.tsx,
     Rag.tsx, RagDetail.tsx, ProcessDocs.tsx, Media.tsx, Rpa.tsx,
     Reviews.tsx, Cubix.tsx, Services.tsx, Pipelines.tsx, PipelineDetail.tsx,
     Admin.tsx, Audit.tsx, Login.tsx
     + SpecWriter.tsx (B5.2-bol UJ! = 23 oldal!)

2. Minden oldalhoz hatarozd meg:
   - **Mit mutat:** fo feature-ok (pl. "diagram lista + generator form + preview")
   - **Mi mukodik:** valos backend hivas (useApi + source badge "Backend")
   - **Mi NEM mukodik:** hianyzo akciok, placeholder, demo data
   - **Kategoria (A/B/C):**
     A = mukodik end-to-end, nincs tennivalo
     B = UI van + backend reszleges → B8-ban javitando
     C = UI van + backend stub/demo → Sprint C-re halasztva
   - **Journey:** melyik user journey-be tartozik (1/2/3/4/admin/-)

3. Allitsd ossze a 23-soros audit tablat ebben a formatumban:

| # | Oldal | Route | Cel | Mi mukodik | Mi NEM mukodik | Kategoria | Journey |
|---|-------|-------|-----|-----------|----------------|-----------|---------|
| 1 | Dashboard | / | KPI attekintes | Placeholder KPI kartyak | Valos metrikak, pipeline trigger | B | 2-Monitoring |
| ... | ... | ... | ... | ... | ... | ... | ... |
| 23 | SpecWriter | /spec-writer | Spec generalas | POST /api/v1/specs/write + preview + download | Streaming, history kereses | B | 4-Generation |

4. Audit vege summary: hany A / B / C kategoria van. Per-journey count.
   Pl. "A: 3 | B: 17 | C: 3 | Journey 1: 5 | Journey 2: 6 | Journey 3: 3 | Journey 4: 3 | Admin: 2 | — : 4"

Gate: 23-soros tabla a 63_UI_USER_JOURNEYS.md-ben, minden oldal audit-olva,
      kategoria es journey cimke hozzarendelve.
```

### LEPES 2: B6.2 — Portal Information Architecture Ujratervezes (journey-based sidebar)

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (masodik szekcio)
     Referencia: 01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md (sor 1364-1407)
                aiflow-admin/figma-sync/REDESIGN_PLAN.md

Cel: UJ navigacios struktura — 6 felhasznaloi cel csoport.

KONKRET TEENDOK:

1. Dokumentald a JELENLEGI navigaciot (technikai csoportositas):
   DASHBOARD
   OPERATIONS:   Runs | Costs | Monitoring | Quality
   DATA:         Documents | Emails
   AI SERVICES:  RAG | Process Docs | Media | RPA | Reviews | Cubix
   ORCHESTRATION: Services | Pipelines
   ADMIN:        Admin | Audit

2. Dokumentald a UJ navigaciot (felhasznaloi cel alapu):
   
   DASHBOARD (fo attekintes, 4 journey kartyaval)
   
   DOKUMENTUM FELDOLGOZAS (Journey 1 — invoice scan → extract → verify → report)
     - Szamla Kereso (Invoice Finder trigger — /pipelines/invoice_finder_v1 trigger)
     - Dokumentum Upload + Extrakció (Documents /documents + upload button)
     - Verifikacio (Verification Page /documents/:id/verify + Reviews /reviews merge)
     - Email Scan (Emails /emails csak mint journey step, nem kulon nav)
     - Mentett Dokumentumok (Documents lista)
   
   TUDASBAZIS (Journey 3 — RAG)
     - Kollekcio Kezeles (Rag /rag)
     - Kollekcio Detail + Ingest + Chat (RagDetail /rag/:id tabbelt)
     - Visszajelzes + Statisztika (RagDetail stats tab)
   
   GENERALAS (Journey 4 — AI output)
     - Diagram Generalas (ProcessDocs /process-docs — flowchart + sequence + swimlane!)
     - Specifikacio Iras (SpecWriter /spec-writer — B5.2-bol UJ!)
     - Media Feldolgozas (Media /media — STT + video)
   
   MONITORING (Journey 2 — governance)
     - Pipeline Futasok (Runs /runs)
     - Koltsegek (Costs /costs + /api/v1/costs/breakdown)
     - Szolgaltatas Egeszseg (Monitoring /monitoring + /api/v1/services)
     - LLM Minoseg (Quality /quality)
     - Audit Naplo (Audit /audit)
   
   BEALLITASOK (Admin)
     - Felhasznalok + API Kulcsok (Admin /admin)
     - Pipeline Sablonok (Pipelines /pipelines — ide koltozik, NEM fo nav!)
     - Szolgaltatas Katalogus (Services /services — ide koltozik, infra view)
     - Email Connector Beallitasok (integralt az Emails-be, kulon almenu)
   
   (almenu) ESEMENYEK
     - RPA Browser (RPA /rpa — almenu, NEM fo nav)
     - Cubix Kurzus (Cubix /cubix — almenu, NEM fo nav)

3. Indoklas tabla: MIT mozgatunk, MIERT:

| Mozgatas | Honnan | Hova | Indoklas |
|----------|--------|------|----------|
| /emails | DATA fo csoport | Dokumentum Feldolgozas/Email Scan step | Nem kulon nav — journey resze |
| /reviews | AI SERVICES fo csoport | Dokumentum Feldolgozas/Verifikacio | Verification page merge |
| /services | ORCHESTRATION fo csoport | BEALLITASOK/Szolgaltatas Katalogus | Infra view, ritkabban hasznalt |
| /pipelines | ORCHESTRATION fo csoport | BEALLITASOK/Pipeline Sablonok | Nem user action, konfiguracio |
| /rpa | AI SERVICES fo csoport | ESEMENYEK almenu | Ritkan hasznalt, nem journey |
| /cubix | AI SERVICES fo csoport | ESEMENYEK almenu | Demo, nem napi hasznalat |

Gate: 6 csoport + 4 journey mapping dokumentalva, minden 23 oldal hozzarendelve,
      indoklasi tabla 6 mozgatassal.
```

### LEPES 3: B6.3 — Holisztikus User Journey Terkep (ASCII art + tablazat)

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (harmadik szekcio)

Cel: EGY kep ami mutatja a 4 journey-t es a kozottuk levo kapcsolatot.

KONKRET TEENDOK:

1. Rajzold fel az ASCII arban a "journey map"-et a plan 58 terv 1409-1432. sorok alapjan.
   Ez a forras, ezt csak masolnod kell + a SpecWriter B5.2-bol hozzaadni a Journey 4-hez:

   DASHBOARD (4 journey kartya)
   +----------------+  +----------------+  +----------------+  +----------------+
   | Szamla         |  | Monitoring     |  | Tudasbazis     |  | Generalas      |
   | Feldolgozas    |  | & Governance   |  | (RAG)          |  | (AI Output)    |
   | (3 aktiv)      |  | (OK)           |  | (2 kollekcio)  |  | (1 fut)        |
   +--------+-------+  +--------+-------+  +--------+-------+  +--------+-------+
            |                   |                   |                   |
            v                   v                   v                   v
       JOURNEY 1           JOURNEY 2           JOURNEY 3           JOURNEY 4
       (Invoice)         (Monitoring)            (RAG)            (Generation)
   
   Journey 1:                Journey 2:                Journey 3:            Journey 4:
     Email scan                Dashboard KPI             Collection            Input leiras
         |                         |                         |                    |
     Detektalas                Drill-down                 Dok feltoltes        Tipus valasztas
     (classifier)              /runs /costs                    |              (diag/seq/bpmn/spec)
         |                     /monitoring                  Ingest                |
     Extrakció                 /quality                         |              LLM generalas
         |                         |                         Chat                  |
     Konfidencia               Beavatkozas                      |               Preview + Edit
         |                     (pipeline restart)           Feedback                |
     Verifikacio                    |                                            Export
         |                     Audit naplo                                      (SVG/MD/JSON)
     Jelentes kuldes

2. Kotelezo kereszt-referencia tabla: melyik journey MELYIK oldalt hasznalja:

| Oldal | J1 Invoice | J2 Monitoring | J3 RAG | J4 Generation | Megjegyzes |
|-------|:---:|:---:|:---:|:---:|-----------|
| Dashboard | belepes | belepes | belepes | belepes | 4 kartya |
| Emails | STEP 1 | — | — | — | csak J1 |
| Documents | STEP 2 | — | — | — | filtered view! |
| Verification | STEP 3 | — | — | — | |
| Reviews | STEP 3 merge | — | — | — | |
| Runs | — | STEP 2 | — | — | |
| Costs | — | STEP 2 | — | — | |
| Monitoring | — | STEP 2 | — | — | |
| Quality | — | STEP 2 | — | — | |
| Audit | — | STEP 3 | — | — | |
| Rag | — | — | STEP 1 | — | |
| RagDetail | — | — | STEP 2-4 | — | tabbelt |
| ProcessDocs | — | — | — | STEP 1-3 | 3 diagram tipus |
| SpecWriter | — | — | — | STEP 1-3 | B5.2 uj |
| Media | — | — | — | STEP 1-3 | STT+video |
| Services | config | config | config | config | BEALLITASOK |
| Pipelines | config | — | — | — | BEALLITASOK |
| Admin | — | — | — | — | users/keys |
| Rpa | — | — | — | — | almenu |
| Cubix | — | — | — | — | almenu |

Gate: ASCII map + kereszt-ref tabla kesz.
```

### LEPES 4: B6.4 — 4 Reszletes User Journey Definicio

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (negyedik szekcio — a LEGNAGYOBB!)

Cel: Mindegyik journey-t reszletesen definialni (entry point → lepesek → backend → oldalak).

KONKRET TEENDOK:

Mindegyik journey-hez a KOVETKEZO strukturat kovesd (4 × ~50 sor):

### JOURNEY X: {Nev}
**Cel:** {egy mondat}
**Felhasznalo:** {role}
**Entry point:** {Dashboard X kartya → /oldal VAGY kozvetlen URL}
**Varhato kimenet:** {mit kap a user a vegen}

**Lepesek:**

**Lepes 1: {Nev} ({/oldal})**
- User {akcio}
- Rendszer {mit csinal a backenden} → {endpoint}
- UI visszajelzes: {progress bar / badge / alert}
- Eredmeny: {mit lat}

**Lepes 2: {Nev} ({/oldal})**
...

**Backend osszeallitas (amit a journey vegigzong):**
- {service 1} → {service 2} → {service 3} → ...

**Oldalak (navigacio a felhasznalo szempontjabol):**
- /oldal1 (entry)
- /oldal2 (filtered/context)
- /oldal3 (detail)
- /oldal4 (result)

**Hianyzo funkciok (B8-ban implementalando!):**
- [ ] {hianyzo UI akcio}
- [ ] {hianyzo endpoint}
- [ ] {hianyzo badge vagy filter}

---

### JOURNEY 1: Szamla Feldolgozas (Invoice Finder)
  Referencia: plan sor 1436-1466.
  4 lepes: Email scan → Szamla lista → Verifikacio → Jelentes
  Backend: email_connector → classifier → document_extractor → invoice_processor
           → confidence_router → human_review → notification
  Oldalak: /emails → /documents (filtered) → /documents/:id/verify → /reports
  KRITIKUS: Verification Page v2 (B7 következik! — bounding box + diff)

### JOURNEY 2: Monitoring & Governance
  Referencia: plan sor 1468-1490.
  3 lepes: Dashboard → Drill-down → Beavatkozas
  Backend: health_monitor + quality + audit + Langfuse + cost_records
  Oldalak: / → /runs | /costs | /monitoring | /quality → /audit

### JOURNEY 3: Tudasbazis (RAG Chat)
  Referencia: plan sor 1492-1516.
  4 lepes: Kollekcio → Upload → Chat → Visszajelzes
  Backend: rag_engine + vector_ops + reranker + advanced_chunker
  Oldalak: /rag → /rag/:id (tabbed: ingest / chat / stats)

### JOURNEY 4: Generalas (Diagram + Spec + Media)  ← B5.2 SpecWriter miatt BOVITETT!
  Referencia: plan sor 1518-1537. DE + SpecWriter (B5.2 UJ) + diagram sequence/bpmn_swimlane (B5.1)!
  3 lepes: Input → Generalas → Export
  Tipus valasztas: flowchart | sequence | bpmn_swimlane | spec_feature | spec_api | spec_db | spec_user_story | media_stt
  Backend: diagram_generator (3 prompt B5.1!) + spec_writer (5-step B5.2!) + media_processor
  Oldalak: /process-docs (diagram tab) → /spec-writer → /media → export

FIGYELEM: Journey 4-hez HOZZAADANDO a SpecWriter flow ami az S30-ban kesz lett!
A plan 58 meg a REGI Journey 4-et tartalmazza — irasi kozben bovitsed ki a
B5 eredmenyekkel (B5.1 + B5.2):

Journey 4 Lepes 1 (Input): diagram type selector bovult 3-ra:
  "flowchart" / "sequence" / "bpmn_swimlane" / "spec_feature" / "spec_api"
  / "spec_db" / "spec_user_story" / "media_stt"

Journey 4 Lepes 2 (Generalas): 
  - Ha diagram → DiagramGeneratorService.generate(diagram_type=...) 
    (flowchart = process_documentation skill, sequence/swimlane = 3 uj prompt)
  - Ha spec → skills.spec_writer.workflows.spec_writing.run_spec_writing()
    (5 step: analyze → select_template → generate → review → finalize)
  - Ha media → media_processor.process_media()

Journey 4 Lepes 3 (Export):
  - Diagram: SVG (Kroki), Mermaid forras, DrawIO XML
  - Spec: Markdown, HTML, JSON (mar mukodik /api/v1/specs/{id}/export)
  - Media: transcript txt/srt + summary

Gate: 4 teljes journey dokumentum a 63_UI_USER_JOURNEYS.md-ben, mind
      "hianyzo funkciok" checklist-tel B8-nak.
```

### LEPES 5: B6.5 — Navigacios Wireframe (Figma MCP)

```
Hol: Figma MCP (mcp__figma__create_new_file vagy meglevo file bovites)
     Output: 2 uj Figma frame + frame ID-k 01_PLAN/63_UI_USER_JOURNEYS.md-ben

Cel: Ket kulcs wireframe — UJ sidebar + UJ dashboard.

KONKRET TEENDOK:

1. Ellenorizd a Figma MCP elerhetoseget:
   Figma MCP server: mcp__figma__*
   Ha elerheto: folytatas. Ha nem: skip Figma, csak ASCII wireframe a doksiban.

2. Figma Sidebar Wireframe (mcp__figma__generate_figma_design vagy generate_diagram):
   - Content: 6 csoportos sidebar tree
     DASHBOARD
     DOKUMENTUM FELDOLGOZAS (expanded: 5 aloldal)
     TUDASBAZIS (expanded: 2 aloldal + kollekciok lista)
     GENERALAS (expanded: 3 aloldal)
     MONITORING (expanded: 5 aloldal)
     BEALLITASOK (expanded: 4 aloldal)
     (bottom: MEG tovabbi — RPA, Cubix)
   - Stilus: Untitled UI design tokenek (dark + light theme)
   - Size: 260px width x 900px height
   - Allapotok: active item highlight + hover state + collapsed state

3. Figma Dashboard Wireframe (kartya-alapu, 4 journey):
   - 4 nagy kartya (360x200 px mindegyik) egy 2x2 grid-ben
     - Szamla Feldolgozas kartya: ikon + cim + "3 aktiv journey" + utolso 3 pipeline badge
     - Monitoring kartya: ikon + cim + 4 KPI mini (runs/costs/health/quality) + alert banner
     - Tudasbazis kartya: ikon + cim + "2 kollekcio, 120 dokumentum" + kereso
     - Generalas kartya: ikon + cim + 3 akcio gomb (diagram / spec / media)
   - Under: "Legutobbi aktivitas" panel (utolso 10 pipeline run)
   - Stilus: Untitled UI Card componens, Tailwind v4 design tokenek
   - Size: 1440x900 desktop + 375x800 mobile

4. Mentsd el a frame ID-kat a 63_UI_USER_JOURNEYS.md-ben:

   ## B6.5 Wireframe Frame-ek (Figma)
   - Sidebar: frame_id `XXXX:YYYY` — https://figma.com/design/{file}?node-id={id}
   - Dashboard: frame_id `XXXX:YYYY` — https://figma.com/design/{file}?node-id={id}

5. Frissitsd a PAGE_SPECS.md-ben levo "Figma Page & Frame Registry"-t a 2 uj frame-mel.

Ha Figma MCP NEM ERHETO EL:
  - Kesz egy reszletes ASCII wireframe-et a Markdown fajlba (mindket kepernyore)
  - A PAGE_SPECS.md update kozvetlenul a code, nem design
  - Ezt dokumentald a 63_UI_USER_JOURNEYS.md tetejen ("Figma MCP not available,
    ASCII wireframes only — converting to Figma frames is a B8 step")

Gate: 2 wireframe (Figma VAGY ASCII), mindegyikhez link/referenci a 63_UI_USER_JOURNEYS.md-ben.
```

### LEPES 6: B6.6 — Demo → Backend Migracios Terv

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (utolso szekcio)

Cel: Kategorizalni melyik oldalt kell Sprint B-ben (B8) mukodove tenni
     es melyik Sprint C-re halasztva.

KONKRET TEENDOK:

1. Az audit (B6.1) alapjan hozd letre a PRIORITASSORT:

**SPRINT B8 (PRIORITAS — Journey 1 + 2 mindenkeppen):**
| # | Oldal | Journey | Mi hianyzik | Becsult munka |
|---|-------|---------|-------------|---------------|
| 1 | Documents (filter) | J1 | Invoice-only filter + confidence szures | 1 ora (front-end only) |
| 2 | Verification | J1 | Bounding box + per-field confidence szin (B7!) | 1 session (B7) |
| 3 | Reviews | J1 | Merge a Verification-ba | 2 ora |
| 4 | Dashboard | J2 | Valos KPI (costs / runs / quality API hivas) | 3 ora |
| 5 | Monitoring | J2 | Valos service health (/api/v1/services/{name}/health) | 2 ora |
| ... | ... | ... | ... | ... |

**SPRINT B8 (opcionalis — ha marad ido):**
| # | Oldal | Journey | Mi hianyzik |
|---|-------|---------|-------------|
| 1 | ProcessDocs | J4 | diagram_type dropdown (sequence / bpmn_swimlane — B5.1-bol!) |
| 2 | SpecWriter | J4 | History kereso + recent specs widget |
| ... | ... | ... | ... |

**SPRINT C (halasztva):**
| # | Oldal | Indoklas |
|---|-------|----------|
| 1 | RPA | Nem kritikus journey, meg nincs backend workflow |
| 2 | Cubix | Demo skill, backend STT pipeline mukodik de UI viewer limitalt |
| 3 | Media | STT mukodik, video kevesse teszt |
| ... | ... | ... |

2. Kulon szekciok:
   - **ELKERULENDO anti-pattern-ek** (pl. "NE mock-olj demo adatot a /dashboard-on")
   - **7 HARD GATE tobbeti sorrend B8-hoz** (Journey definicio → API audit → API impl →
     Figma → UI → Playwright → Figma sync)
   - **Sprint kontext:** melyik journey lesz E2E Playwright-tal tesztelve B8-ban?
     (legalabb Journey 1 + Journey 2 kotelezo!)

Gate: Priorizalt migrations tabla 3 kategoriaval (B8 kotelezo + B8 opcionalis +
      Sprint C halasztott), minden oldalhoz hianyzo feature lista.
```

### LEPES 7: VALIDACIO 1. KOR — Plan Audit (plan-validator agent)

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (elkeszult terv)
Eszkoz: Agent(subagent_type=plan-validator) VAGY manualis check

Cel: Az 1. piszkozat konzisztencia ellenorzese — szamok, hivatkozasok,
     cross-reference, hianyzo szekciok felderitese.

KONKRET TEENDOK:

1. Indits el egy plan-validator subagent-et. A prompt minimum tartalmazza:

   "Validald az 01_PLAN/63_UI_USER_JOURNEYS.md dokumentumot a kovetkezokre:
   
   (A) SZAMOK KONZISZTENCIAJA:
   - Minden 23 oldal jelen van-e a B6.1 audit tablaban? (Dashboard .. SpecWriter)
   - A summary soszam (A+B+C) egyenlo-e 23-mal?
   - A per-journey count osszege 23 (+fortehet: admin + —)?
   - A B6.2 uj IA 23 oldalt lefed-e?
   - A B6.3 kereszt-ref tabla 23 sort tartalmaz-e?
   - A B6.6 migracios tabla teljes-e (B8 kotelezo + opcionalis + Sprint C halasztott)?

   (B) HIVATKOZASOK:
   - Minden `/route` cimnek van-e letezo .tsx fajlja? (`aiflow-admin/src/pages-new/`)
   - Minden emlitett API endpoint (pl. /api/v1/specs/write) letezik-e?
     (grep `src/aiflow/api/v1/*.py`)
   - Minden emlitett pipeline template letezik-e?
     (ls `src/aiflow/pipeline/builtin_templates/`)
   - Minden skill/service referencia valos-e?

   (C) JOURNEY CONSISTENCY:
   - A 4 journey reszletes definicioja (B6.4) konzisztens-e a B6.2 IA
     csoportositassal? Pl. ha Journey 1 tartalmaz 'Emails' oldalt, akkor
     B6.2-ben is a Dokumentum Feldolgozas csoportban kell lennie.
   - Minden journey step-je hasznal letezo backend szolgaltatast?
   - A B6.4 'hianyzo funkciok' list tukrozi a B6.6 'B8 kotelezo' taablat?

   (D) B5.1 + B5.2 INTEGRACIO:
   - A Journey 4 tartalmazza-e a 3 diagram tipust (flowchart/sequence/bpmn_swimlane)?
   - A Journey 4 tartalmazza-e a 4 spec tipust (feature/api/db/user_story)?
   - A /spec-writer oldal az audit tablaban szerepel (a 23. sor)?
   - A diagram_generator_v1.yaml + spec_writer_v1.yaml pipeline template
     hivatkozva a Journey 4-ben?

   (E) HIANYZO SZEKCIO DETEKCIO:
   - Minden B6.x szekcio (B6.1 .. B6.6) jelen van?
   - A wireframe szekcio Figma frame ID-t VAGY ASCII content-et tartalmaz?
   - A dokumentum > 600 sor (gate checklist minimum)?

   (F) FIGMA + PAGE_SPECS SZINKRON:
   - Ha PAGE_SPECS.md-ben uj Figma frame ID van, akkor az 63_UI_USER_JOURNEYS.md-ben
     is szerepel?
   - Minden 23 oldalhoz rendelt journey cimke PAGE_SPECS.md-ben?

   Adj vissza egy STRUKTURALT audit riportot ebben a formatumban:
   
   ## Validacio 1. Kor
   ### PASS (X pont)
   - {konzisztens resz 1}
   - {konzisztens resz 2}
   ...
   
   ### FAIL / WARNING (Y pont)
   1. [KRITIKUS/MAJOR/MINOR] {hiba leiras} — Javaslat: {megoldas}
   2. ...
   
   ### MISSING (Z pont)
   1. {hianyzo szekcio / tabla / hivatkozas}
   
   ### Osszpontszam: X/Y/Z = {verdict}"

2. A subagent visszaadja a riportot. Mentsd el:
   out/b6_validation_round1.md

3. Ha NINCS subagent elerheto / plan-validator nem letezik:
   manualisan vegigmegy a (A)-(F) ellenorzeseken, bemenetkent hasznaljuk:
   - Glob + grep aiflow-admin/src/pages-new/*.tsx
   - Grep "/api/v1/" src/aiflow/api/v1/*.py
   - Ls src/aiflow/pipeline/builtin_templates/
   - Read 63_UI_USER_JOURNEYS.md szekcionkent

Gate: out/b6_validation_round1.md letezik, strukturalt riport vissza az
      audit / validation tabla-val. MINIMUM 5 ellenorzott pont.
```

### LEPES 8: JAVITAS 1. KOR — Validacios hibak feldolgozasa

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (javitas a validacio alapjan)

Cel: Az 1. validacios kor minden KRITIKUS es MAJOR hibajat javitani.
     MINOR hibakbol annyit ameennyit idohatekonyan lehet.

KONKRET TEENDOK:

1. Olvasd be: out/b6_validation_round1.md
2. Minden KRITIKUS hibahoz: azonnal Edit a 63_UI_USER_JOURNEYS.md-ben.
3. Minden MAJOR hibahoz: Edit vagy indokold meg miert hagytuk (TODO comment).
4. MINOR hibakhoz: ha 5+ MINOR van, mentsd meg mind-et. Ha csak par,
   a gyorsabbakat javitsd.
5. Ha HIANYZO szekcio derult ki: pottold.
6. Ha cross-reference hibas (pl. /oldal nem letezik): vagy
   (a) kijavitod az oldalt a valos .tsx fajlra, vagy
   (b) torlod a nem letezo hivatkozast a doksibol.

7. Jelold a javitas vegen minden savan javitott pontot egy kommentar-blokkban:

   <!-- B6 VALIDATION ROUND 1 FIXES -->
   - FIXED: {leiras 1}
   - FIXED: {leiras 2}
   - DEFERRED: {leiras 3, oka}
   - SKIPPED: {leiras 4, oka (minor)}
   <!-- END B6 VALIDATION ROUND 1 FIXES -->

8. Ellenorizd a fajlmeretet: legalabb 600 sor. Ha kevesebb, bovitsd a
   hianyossagot.

Gate: Minden KRITIKUS + MAJOR hiba javitva, javitas-lista kommentar-
      blokkban, fajl >= 600 sor.
```

### LEPES 9: VALIDACIO 2. KOR — Masodik ellenorzes

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (javitott terv)
Eszkoz: Agent(subagent_type=plan-validator) ujra VAGY manualis re-check

Cel: A javitas utan masodik, FRISS szemmel valo ellenorzes.
     Ugy keszit egy masodik subagent-et mintha elsore latna a dokumentumot,
     es ellenorzi:
     - Az 1. kor hibak tenyleg javitva lettek-e (regression check)?
     - Van-e uj hiba amit az 1. kor javitas okozott (pl. uj cross-ref torlott)?
     - Van-e olyan regressziv hiba amit az 1. kor nem vett eszre?

KONKRET TEENDOK:

1. Uj plan-validator subagent a 63_UI_USER_JOURNEYS.md-hez, prompt:

   "MASODIK validacios kor az 01_PLAN/63_UI_USER_JOURNEYS.md-re.
   
   Az elozo kor audit riport itt van: out/b6_validation_round1.md
   
   ELLENORIZD:
   (1) Az elozo kor MINDEN 'KRITIKUS' + 'MAJOR' hibaja tenyleg javitva van-e
       a dokumentumban. Grep-pel ellenorizd. Ha nem → REGRESSION WARNING.
   (2) A javitasok utan VAN-e uj kovetkezmenyes hiba (pl. a / nav-t modositottak
       es most egy mas szekcio hivatkozasa torott)?
   (3) Olvasd ujra a dokumentumot ELSORE VALO szemmel. Van-e ertelem:
       - Egy uj olvasso megertene-e a 4 journey-t?
       - Tud-e dolgozni belole a B8 implementacio?
       - Vilagos-e a navigacio IA?
   (4) Tartalmaz-e implementalhato reszleteket vagy csak magas szintu?
   (5) A B8 migracios tabla actionable-e (becsult ido + assigned step)?
   (6) Minden 4 journey-nek van-e vilagos 'entry point' (honnan indul a user)?
   (7) A wireframe (Figma/ASCII) reszletes-e eleg hogy B8-ban kod lehessen belole?

   Adj vissza ugyanolyan strukturalt riportot mint az 1. korban:
   
   ## Validacio 2. Kor
   ### REGRESSION CHECK (1. kor javitasok)
   - [OK/FAIL] {1. kor javitas ellenorzese}
   ...
   
   ### UJ HIBA (2. korben talalt)
   1. [KRITIKUS/MAJOR/MINOR] {leiras} — Javaslat
   
   ### MINOSEG + OLVASOSZEMPONT
   - Erthetoseg: {score 1-10}
   - Implementalhatosag B8-ban: {score 1-10}
   - Wireframe kereszthez elegendo-e: {igen/nem}
   
   ### Verdict: DONE / NEEDS FIX"

2. Mentsd el: out/b6_validation_round2.md

Gate: out/b6_validation_round2.md letezik, masodik kor audit elvegezve.
      A 2. kor egyaltalan TALALT-e uj hibat? Dokumentald.
```

### LEPES 10: JAVITAS 2. KOR — Vegso polish

```
Hol: 01_PLAN/63_UI_USER_JOURNEYS.md (vegso javitas)

Cel: 2. kor validacio hibainak javitasa + dokumentum polirozas.

KONKRET TEENDOK:

1. Olvasd be: out/b6_validation_round2.md
2. Minden UJ hiba (kritikus/major) javitva → Edit.
3. REGRESSION hibak (ha az 1. kor javitas uj problemat okozott) → Edit.
4. MINOR hibak: igen/nem alapon — ha 2 percnel rovidebb, javitsd.
5. Frissitsd a javitasok kommentar-blokkot:

   <!-- B6 VALIDATION ROUND 2 FIXES -->
   - FIXED: {2. kor leiras 1}
   - FIXED: {2. kor leiras 2}
   - NO CHANGE: 1. kor javitasok all OK (regression check PASS)
   <!-- END B6 VALIDATION ROUND 2 FIXES -->

6. Ha a 2. kor validacio NAGY hibat talalt amit nem lehet gyorsan javitani:
   - Ne torld ki a doksi fo tartalmat
   - Jelold a szekciot `<!-- TODO B8: {javaslat} -->` kommentarral
   - Commit uzenetben emelje ki

7. Ellenorizd a fajlmeretet: meg mindig >= 600 sor (ne csonkoljunk).

8. Vegso minosegcheck (manualis):
   - Minden `[ ]` (nyitott checkbox) szandekkal nyitott-e?
   - Kepernyokon lathato, olvashato (a Markdown renderel)?
   - A 4 journey szekcio kozott terjedelem konzisztens-e
     (nincs 500 soros Journey 1 es 50 soros Journey 2)?

Gate: 63_UI_USER_JOURNEYS.md ketszer validalva + ketszer javitva,
      0 nyitott KRITIKUS hiba, MAJOR hibak javitva vagy dokumentaltan deferred.
```

### LEPES 11: Plan + Commit (EGY commit, mert csak dokumentacio)

```
/update-plan → 58 B6 row DONE + datum + commit
              CLAUDE.md + 01_PLAN/CLAUDE.md NINCS kulcsszam valtoztatas (csak doksi!)

Commit:
  docs(sprint-b): B6 portal struktura audit + 4 user journey + wireframe (2x validated)

  Body:
    - 01_PLAN/63_UI_USER_JOURNEYS.md UJ (6 szekcio: audit + IA + map + 4 journey +
      wireframe + migrations) — 23 oldal audit, 6-csoportos journey-based sidebar IA,
      4 reszletes journey definicio (Invoice + Monitoring + RAG + Generation).
      Journey 4 (Generation) bovitve a B5.1 diagram sequence/swimlane + B5.2 spec_writer
      + media_stt flow-kkal.
    - aiflow-admin/figma-sync/PAGE_SPECS.md frissites: minden 23 oldal hozzarendelt
      journey + kategoria (A/B/C). 2 uj Figma frame (uj sidebar + uj dashboard).
    - B8 migracios priorizalt terv: J1 Invoice (5 oldal kotelezo) + J2 Monitoring
      (5 oldal kotelezo) prioritasa, ProcessDocs diagram_type dropdown opcionalis.
    - 2-KORBEN VALIDALT: out/b6_validation_round1.md + out/b6_validation_round2.md
      plan-validator subagent riportok, minden KRITIKUS + MAJOR hiba javitva,
      regression check PASS a 2. korben.
    - NINCS kodvaltoztatas (design-first session).

    Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

**KESZ JELENTES:** a LEPES 11 commit utan explicit "B6 DONE" jelzest kell kiadni a
usernek a kovetkezo tartalomal:
- Kimeneti artefaktumok listaja (63_UI_USER_JOURNEYS.md sor szam, B6.1-B6.6 szekcio check)
- Validacio eredmeny (1. kor hibaszam → javitott, 2. kor hibaszam → javitott)
- Minosegscore (erhetoseg + implementalhatosag)
- Commit SHA
- Kovetkezo session: S32 = B7 (Verification Page v2)

### Kimenet Fajl Struktura (B6 vege)

```
01_PLAN/63_UI_USER_JOURNEYS.md                           — UJ, ~600-800 sor, 6 szekcio
                                                           + 2 validacios kommentar-blokk
                                                           (B6 VALIDATION ROUND 1/2 FIXES)
01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md                 — B6 row DONE marker

aiflow-admin/figma-sync/PAGE_SPECS.md                    — journey mapping hozzaadva
                                                           + 2 uj Figma frame ID

out/b6_validation_round1.md                              — plan-validator 1. kor riport (NEM committed)
out/b6_validation_round2.md                              — plan-validator 2. kor riport (NEM committed)

(Opcionalis, ha Figma MCP elerheto):
Figma file: uj sidebar frame + uj dashboard frame

Osszesen:
  1 UJ nagy doksi (63_UI_USER_JOURNEYS.md, ~600 sor, 2 validacios korben atesve)
  2 MODOSITOTT fajl (58 plan + PAGE_SPECS.md)
  2 validacios riport (out/ — gitignore-olt, csak auditra)
  0 modositott kod
  0 teszt valtozas
  0 DB migracio
  0 uj promptfoo
```

---

## VEGREHAJTAS SORRENDJE

```
=== FAZIS A: TERV ELKESZITESE (LEPES 1-6) ===

--- LEPES 1: Audit ---
/ui-journey portal audit 23 oldal
(vagy direkt: Glob aiflow-admin/src/pages-new/*.tsx + Read mindegyiket + tabla osszeallitas)

--- LEPES 2: Uj IA ---
Write 01_PLAN/63_UI_USER_JOURNEYS.md (elso 2 szekcio: audit + IA)

--- LEPES 3: Journey map ---
Edit 01_PLAN/63_UI_USER_JOURNEYS.md (harmadik szekcio: ASCII map + kereszt-ref)

--- LEPES 4: 4 journey detail ---
Edit 01_PLAN/63_UI_USER_JOURNEYS.md (negyedik szekcio: 4 journey reszletes)

--- LEPES 5: Wireframe ---
(ha Figma MCP elerheto)
mcp__figma__create_new_file VAGY mcp__figma__get_design_context
mcp__figma__generate_figma_design "AIFlow uj sidebar navigacio — journey-based"
mcp__figma__generate_figma_design "AIFlow dashboard — 4 journey kartya"
Edit PAGE_SPECS.md (frame ID-k)
Edit 63_UI_USER_JOURNEYS.md (wireframe szekcio + link)

(vagy ASCII wireframe a doksiba)

--- LEPES 6: Migracios terv ---
Edit 01_PLAN/63_UI_USER_JOURNEYS.md (utolso szekcio: B8 priorizacio)

>>> Elso piszkozat KESZ — 63_UI_USER_JOURNEYS.md ~600+ sor, 6 szekcio.
    DE: NEM mehetunk commit-ra amig 2 kor validacio meg nem tortent!


=== FAZIS B: 2-KOROS VALIDACIO (LEPES 7-10) ===

--- LEPES 7: VALIDACIO 1. KOR ---
Agent(subagent_type=plan-validator) with explicit checklist (A-F):
  (A) szamok konzisztencia (23 oldal)
  (B) hivatkozasok valos (/route, /api, pipeline template, skill)
  (C) journey consistency (B6.2 IA vs B6.4 detail)
  (D) B5.1 + B5.2 integracio (3 diagram tipus + spec_writer + /spec-writer oldal)
  (E) hianyzo szekcio detekcio
  (F) Figma + PAGE_SPECS szinkron
Mentsd ki: out/b6_validation_round1.md

--- LEPES 8: JAVITAS 1. KOR ---
Read out/b6_validation_round1.md
Edit 01_PLAN/63_UI_USER_JOURNEYS.md minden KRITIKUS + MAJOR hibaert
Add hozza a <!-- B6 VALIDATION ROUND 1 FIXES --> kommentar blokkot
(FIXED / DEFERRED / SKIPPED list-tel)
Ellenorizd a fajlmeretet (>= 600 sor)

--- LEPES 9: VALIDACIO 2. KOR ---
Agent(subagent_type=plan-validator) ujra — FRISS szemmel!
Ellenorzes:
  (1) regression check: 1. kor javitasok tenyleg benne vannak?
  (2) javitasok okoztak-e uj hibat?
  (3) elso-olvaso perspektiva: B8 implementacio tudja-e hasznalni?
  (4) wireframe reszletes-e eleg?
  (5) 4 journey entry point vilagos-e?
Mentsd ki: out/b6_validation_round2.md

--- LEPES 10: JAVITAS 2. KOR ---
Read out/b6_validation_round2.md
Edit 01_PLAN/63_UI_USER_JOURNEYS.md:
  - 2. kor UJ hibak (kritikus/major) javitas
  - Regression hibak javitasa
  - Vegleges polish (terjedelem konzisztencia per journey)
Add hozza a <!-- B6 VALIDATION ROUND 2 FIXES --> kommentar blokkot
Ha 2. korben kritikus hiba megoldhatatlan gyorsan: `<!-- TODO B8: ... -->` inline

>>> Terv ketszer validalva + ketszer javitva. 0 nyitott KRITIKUS hiba.


=== FAZIS C: LEZARAS (LEPES 11) ===

--- LEPES 11: Plan + commit + KESZ jelentes ---
Edit 01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md (B6 row DONE)
git add 01_PLAN/63_UI_USER_JOURNEYS.md 01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md \
        aiflow-admin/figma-sync/PAGE_SPECS.md
(NE add-old az out/b6_validation_round{1,2}.md fajlokat — gitignore!)
git commit docs(sprint-b): B6 portal struktura audit + 4 user journey + wireframe (2x validated)

Explicit KESZ JELENTES a felhasznalonak:
  - 63_UI_USER_JOURNEYS.md sor szam + 6 szekcio PASS
  - 1. kor hibaszam / javitott
  - 2. kor hibaszam / javitott (regression PASS?)
  - Minoseg score (erhetoseg + implementalhatosag B8-ra)
  - Commit SHA
  - Kovetkezo session: S32 = B7 Verification Page v2
```

---

## KORNYEZET ELLENORZES

```bash
# Branch + HEAD
git branch --show-current                                        # → feature/v1.3.0-service-excellence
git log --oneline -3                                             # → c7079c6, 41d3e60, a77a912

# UI forras felterkepezes:
ls aiflow-admin/src/pages-new/*.tsx | wc -l                      # → 23 (B5.2 SpecWriter uj!)
grep -c "^  {" aiflow-admin/src/router.tsx                       # routes szamosztas

# Meglevo design dokumentumok:
ls 01_PLAN/ | grep -i journey                                    # 9 legacy F1-F6 + feature journey
wc -l aiflow-admin/figma-sync/PAGE_SPECS.md                      # → 1222 sor
wc -l aiflow-admin/figma-sync/REDESIGN_PLAN.md                   # → 283 sor

# NINCS mar B6 kimenet:
ls 01_PLAN/63_UI_USER_JOURNEYS.md 2>&1                           # → No such file — helyes!

# Figma MCP elerhetoseg (opcionalis):
# (a szimula listanel lasd melyik mcp__figma__* tool elerheto)

# Docker nem szukseges B6-hoz (design-only session!)
# Teszt futtatas nem szukseges (0 kodvaltoztatas)
# ruff / tsc nem szukseges (0 kodvaltoztatas)
```

---

## S30 TANULSAGAI (NEM kozvetlenul B6-hoz, de memoriaba rogzitve)

1. **asyncpg pool + event loop trap** — asyncpg pool-ok egy event loop-hoz kotve. pytest-asyncio per-function fixturok + FastAPI TestClient MINDKETTO kulon loopon kreal. Megoldas: shared `aiflow.api.deps.get_pool()`, es multi-step E2E teszt → EGY comprehensive method-ba merge. Memoria: `feedback_asyncpg_pool_event_loop.md`.

2. **DiagramRecord.id nem diagram_id** — A `DiagramGeneratorService` `DiagramRecord` Pydantic modellje `id` mezot tartalmaz, NEM `diagram_id`-t. A regi adapter `getattr(result, "diagram_id", "")` MINDIG uresen tert vissza — a bug csak az E2E teszteken derult ki. **Fake*Record-ok a teszteben MINDIG kovessek a valos Pydantic mezoneveket**. Memoria: `feedback_diagram_adapter_record_id.md`.

3. **KrokiRenderer.render() bytes-t ad vissza** — A `KrokiRenderer.render(code, "svg")` `bytes`-t ad vissza (HTTP body). DB `TEXT` columba VAGY Pydantic `str` mezoba tortenoc irashoz `.decode("utf-8", errors="replace")` kotelezo. Memoria: `feedback_kroki_renderer_bytes.md`.

4. **Promptfoo multi-line `value: |` JS assert `return` kotelezo** — B5.1-ben masodszor buktuk el ezt. A one-liner `return X;` **tovabbra is** a hiba forrasa multi-line `value: |` blokkban → `SyntaxError: Unexpected token 'return'`. Megoldas: keszits 2+ soros JS blokkot kulon statement-ekkel, vagy `const x = ...; return x;`. Memoria: `feedback_promptfoo_js_assertions.md` (S28-bol).

5. **B6 TANULSAG (elolegezve):** 7 HARD GATE betartasa (journey → API → design → UI → teszt). **NE KERULD MEG.** B6 az GATE 1 (journey definicio). B8 az GATE 2-7 implementacio. Enelkul a Sprint B cel nem teljesul.

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# Aktualis UI forras (B6.1 audit-hoz KOTELEZO):
aiflow-admin/src/pages-new/                                  — 23 .tsx fajl
aiflow-admin/src/layout/AppShell.tsx                         — jelenlegi sidebar
aiflow-admin/src/router.tsx                                  — jelenlegi routes (23 oldal)
aiflow-admin/src/lib/i18n.tsx                                — i18n rendszer
aiflow-admin/src/locales/hu.json + en.json                   — fordito szotar
aiflow-admin/src/components-new/                              — DataTable, ErrorState, etc.

# Figma / design referenciak (B6.5 wireframe-hez):
aiflow-admin/figma-sync/PAGE_SPECS.md                        — 1222 sor, per-oldal Figma mapping
aiflow-admin/figma-sync/REDESIGN_PLAN.md                     — 283 sor, korabbi redesign strategia
aiflow-admin/figma-sync/PIPELINE.md                          — Figma-to-code pipeline leiras
aiflow-admin/figma-sync/UNTITLED_UI_AGENT.md                 — agent config
aiflow-admin/figma-sync/config.ts                            — Figma API key + channel

# Legacy F1-F6 journey fajlok (olvasd referenciakent, ne toroljuk):
01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md
01_PLAN/F2_EMAIL_CONNECTOR_JOURNEY.md
01_PLAN/F3_RAG_ENGINE_JOURNEY.md
01_PLAN/F4_RPA_MEDIA_DIAGRAM_JOURNEY.md
01_PLAN/F5_MONITORING_GOVERNANCE_JOURNEY.md
01_PLAN/F6_UI_RATIONALIZATION_JOURNEY.md
01_PLAN/PIPELINE_UI_JOURNEY.md
01_PLAN/QUALITY_DASHBOARD_JOURNEY.md
01_PLAN/SERVICE_CATALOG_JOURNEY.md

# Sprint B + terv:
01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md                     — B6 szekcio sor 1313-1553
01_PLAN/CLAUDE.md                                            — key numbers + sprint status

# Slash commands:
.claude/commands/ui-journey.md                               — GATE 1: journey definicio
.claude/commands/ui-design.md                                — GATE 4: Figma design
.claude/commands/ui-page.md                                  — GATE 5: UI oldal (B8-ban)
.claude/commands/ui-component.md                             — (B8-ban)
.claude/commands/update-plan.md                              — plan update
.claude/skills/aiflow-ui-pipeline/SKILL.md                   — 7 HARD GATE leiras

# Backend referencia a journey-hez (milyen API-k LETEZNEK?):
src/aiflow/api/v1/                                           — 26 router (170 endpoint)
src/aiflow/pipeline/builtin_templates/                        — 9 pipeline template
  invoice_finder_v3.yaml                                     — Journey 1 backbone
  diagram_generator_v1.yaml                                  — Journey 4 (B5.1)
  spec_writer_v1.yaml                                        — Journey 4 (B5.2)

# Memory files (S30 utan):
memory/feedback_asyncpg_pool_event_loop.md
memory/feedback_diagram_adapter_record_id.md
memory/feedback_kroki_renderer_bytes.md
memory/feedback_ui_depth.md                                  — 7 HARD GATE emlekeztet!
memory/feedback_figma_quality.md                             — NO placeholder wireframes!
memory/feedback_no_silent_mock.md                            — Demo/Live badge kotelezo!
```

---

## SPRINT B UTEMTERV (S30 utan, frissitett)

```
S19: B0      — DONE (4b09aad) — 5-layer arch + qbpp + prompt API + OpenAPI
S20: B1.1    — DONE (f6670a1) — 4 LLM guardrail prompt + llm_guards.py + 27 promptfoo
S21: B1.2    — DONE (7cec90b) — 5 guardrails.yaml + PIIMaskingMode + 31 teszt
S22: B2.1    — DONE (51ce1bf) — Core infra service tesztek (65 test, Tier 1)
S23: B2.2    — DONE (62e829b) — v1.2.0 service tesztek (65 test, Tier 2)
S24: B3.1    — DONE (372e08b) — Invoice Finder pipeline + email search + doc acquire (29 test)
S25: B3.2    — DONE (aecce10) — Invoice Finder extract + payment + report + notify (16 test)
S26a: B3.E2E.P0 — DONE (0b5e542) — Outlook COM multi-account fetch + email intent
S26a: B3.E2E.P1 — DONE (f1f0029) — offline invoice finder pipeline (20/20 PASS)
S27a: B3.E2E.P2 — DONE (8b10fd6) — PipelineRunner DB persistence integration
S27a: B3.E2E.P3 — DONE (70f505f) — full 8-step pipeline on 3 Outlook accounts
S27b: B3.5   — DONE (4579cd2) — confidence scoring hardening + review routing (36 test)
S28: B4.1    — DONE (9eb2769) — Skill hardening: aszf_rag 12/12 + email_intent 16/16, +9 promptfoo
S29: B4.2    — DONE (e4f322e) — Skill hardening: process_docs + invoice + cubix split + invoice_finder new, +26 promptfoo (80 total)
S30: B5      — DONE (11364cd + a77a912 + 41d3e60 + c7079c6) — Diagram hardening + spec_writer UJ skill + cost baseline, +18 unit, +16 promptfoo (96), +3 E2E, +1 migracio, +2 pipeline template, +1 UJ skill, +1 UI oldal, 2 service-hardening 8+/10 PRODUCTION-READY
S31: B6      ← KOVETKEZO SESSION — Portal struktura audit + 4 journey tervezes + wireframe (DESIGN-ONLY!)
S32: B7      — Verification Page v2 (bounding box, confidence, diff)
S33: B8      — UI Journey implementacio (navigacio + Journey 1 + Journey 2 E2E)
S34: B9      — Docker deploy + UI pipeline trigger
S35: B10     — POST-AUDIT + javitasok
S36: B11     — v1.3.0 tag + merge
```

---

## FONTOS SZABALYOK (DESIGN-ONLY session emlekeztetok)

- **NE IRJ KODOT.** `aiflow-admin/src/` alatt SEMMIT nem szerkeszteunk. Sem `.tsx`, sem `router.tsx`, sem `AppShell.tsx`. A kovetkezo session (B8) az implementacio.
- **NE IRJ TESZTET.** Nincs unit teszt, nincs promptfoo, nincs E2E. Ez TERVEZES.
- **NE MOZGASS FAJLT.** A legacy F1-F6 journey fajlok a helyukon maradnak, csak referenciakent olvassuk.
- **1 commit a vegen** — mert ez DOKUMENTACIO, NEM 3 feature. A B5-ben kulon commit-ok voltak kulon feature-ok miatt; itt egy nagy doksi van.
- **Figma MCP opcionalis** — ha a `mcp__figma__*` tool-ok elerhetok, hasznald. Ha nem, ASCII wireframe-et ragasztunk a Markdown fajlba + dokumentaljuk hogy B8-ra kell konvertalni.
- **Figma minoseg:** ha Figma-t hasznalsz, valos Untitled UI design token-ekkel, NEM placeholder rectangle-ok. (Memoria: `feedback_figma_quality.md`)
- **`.code-workspace`, `document_pipeline.md`, `100_*.md`, `101_*.md`, `CrewAI_*.md` NE commitold** — ezek lokalis / kulso tervek.
- **`out/` directory NE commitold** — ez a S30 smoke teszt artifact-jai.
- **23 oldal, NEM 22** — a SpecWriter B5.2-ben hozzaadva! Mindig 23-mal szamolj.
- **Journey 4 a legnagyobb valtozas** a 58 tervhez kepest: B5.1 diagram sequence/swimlane + B5.2 spec_writer + media_stt EGYUTT egy journey (Generalas). A 58 plan MEG a kis Journey 4 leirast tartalmazza — bovitsed!
- **7 HARD GATE sorrend:** journey → API → design → UI → teszt → Figma sync. B6 az ELSO gate. A kovetkezo (B7 Verification + B8 implementacio) csak akkor indulhat HA a 63_UI_USER_JOURNEYS.md KESZ es minden oldalhoz hozzarendelt journey van.

---

## B6 GATE CHECKLIST

```
FAZIS A — TERV ELKESZITESE (LEPES 1-6):

B6.1 — 23 oldal audit:
[ ] 01_PLAN/63_UI_USER_JOURNEYS.md letezik
[ ] Audit tabla: 23 sor, 8 oszlop
[ ] Minden oldalhoz kategoria (A/B/C)
[ ] Minden oldalhoz journey cimke (1/2/3/4/admin/-)
[ ] Summary: A/B/C osszeg + per-journey count

B6.2 — Uj IA dokumentalva:
[ ] Jelenlegi navigacio (5 technikai csoport) dokumentalva
[ ] Uj navigacio (6 journey-based csoport) dokumentalva
[ ] Minden 23 oldal hozzarendelt az uj csoporthoz
[ ] Indoklasi tabla: legalabb 6 mozgatas + "miert"

B6.3 — Journey map:
[ ] ASCII art journey map (4 journey egyszerre lathato)
[ ] Kereszt-referencia tabla: melyik oldal melyik journey-ben melyik step

B6.4 — 4 Reszletes journey definicio:
[ ] Journey 1: Invoice (4 step + backend + oldalak + hianyzo lista)
[ ] Journey 2: Monitoring (3 step + backend + oldalak + hianyzo lista)
[ ] Journey 3: RAG (4 step + backend + oldalak + hianyzo lista)
[ ] Journey 4: Generation (3 step + BOVITETT: diagram sequence/swimlane + spec_writer + media)

B6.5 — Wireframe:
[ ] Sidebar wireframe (Figma frame VAGY ASCII)
[ ] Dashboard wireframe (Figma frame VAGY ASCII, 4 kartya)
[ ] Frame ID-k / ASCII content a 63_UI_USER_JOURNEYS.md-ben

B6.6 — Migracios terv:
[ ] B8 kotelezo tabla (Journey 1 + Journey 2 prioritas)
[ ] B8 opcionalis tabla
[ ] Sprint C halasztott tabla

PAGE_SPECS.md:
[ ] Minden 23 oldalhoz hozzarendelt journey
[ ] 2 uj Figma frame ID (ha Figma MCP elerheto)

FAZIS B — 2-KOROS VALIDACIO (LEPES 7-10):

Validacio 1. kor (LEPES 7):
[ ] out/b6_validation_round1.md letezik
[ ] plan-validator subagent riport 6 check-kel (A-F)
[ ] Strukturalt: PASS / FAIL / MISSING szekciok
[ ] Minden hiba severity-vel jelolve (KRITIKUS/MAJOR/MINOR)

Javitas 1. kor (LEPES 8):
[ ] Minden KRITIKUS hiba javitva a 63_UI_USER_JOURNEYS.md-ben
[ ] Minden MAJOR hiba javitva VAGY dokumentaltan deferred
[ ] <!-- B6 VALIDATION ROUND 1 FIXES --> kommentar-blokk a dokumentumban
[ ] Fajl meg mindig >= 600 sor (nem csonkolt)

Validacio 2. kor (LEPES 9):
[ ] out/b6_validation_round2.md letezik
[ ] 2. kor subagent frissen olvasta a javitott dokumentumot
[ ] Regression check: 1. kor javitasok mind a dokumentumban vannak
[ ] Olvasoszempont: erthetoseg + implementalhatosag score 1-10
[ ] Verdict: DONE vagy NEEDS FIX

Javitas 2. kor (LEPES 10):
[ ] Minden 2. kor UJ hiba (kritikus/major) javitva
[ ] Regression hibak javitva
[ ] <!-- B6 VALIDATION ROUND 2 FIXES --> kommentar-blokk
[ ] 0 nyitott KRITIKUS hiba a dokumentumban
[ ] MAJOR hibak javitva vagy `<!-- TODO B8: ... -->` inline

FAZIS C — LEZARAS (LEPES 11):

[ ] 0 kodvaltoztatas (sem .tsx, sem .py)
[ ] 0 teszt valtoztatas (sem unit, sem promptfoo, sem E2E)
[ ] 1 UJ fajl committed: 01_PLAN/63_UI_USER_JOURNEYS.md
[ ] 2 MODOSITOTT fajl committed: 58_POST_SPRINT_HARDENING_PLAN.md + PAGE_SPECS.md
[ ] 2 validacios riport CSAK out/ directory-ban (NEM committed)
[ ] /update-plan → 58 B6 DONE + datum + commit SHA
[ ] git commit: docs(sprint-b): B6 portal struktura audit + 4 user journey + wireframe (2x validated)
[ ] git status sima — semmilyen lokalis state staged
[ ] 63_UI_USER_JOURNEYS.md minimum 600 sor
[ ] Explicit "B6 DONE" jelentes a felhasznalonak (validacios eredmeny + minosegscore + commit SHA)
```

---

## BECSULT SCOPE

- **1 UJ nagy dokumentum** (`01_PLAN/63_UI_USER_JOURNEYS.md`, ~600-800 sor, 6 szekcio, 2 validacios kommentar-blokk)
- **2 MODOSITOTT fajl** (58 plan + PAGE_SPECS.md)
- **2 validacios riport** (`out/b6_validation_round1.md` + `out/b6_validation_round2.md`, NEM committed)
- **0 kodvaltoztatas** (sem aiflow-admin, sem src/aiflow)
- **0 uj teszt** (design-only session)
- **0 DB migracio**
- **2 uj Figma frame** (opcionalis — ha Figma MCP elerheto)

**Ez egy DESIGN-FIRST session** 2-KOROS VALIDACIOVAL — a legfontosabb hogy a 63_UI_USER_JOURNEYS.md alapos legyen, mert a KOVETKEZO 2 session (B7 Verification + B8 UI implementacio) ebbol dolgozik. Ha a 4 journey nem tisztazott, a B8 kaosz lesz. A 2-koros validacio a minoseg zalog — EGY kor nem eleg mert az elso javitas uj hibakat okozhat.

**Becsult hossz:** 1 teljes session (3-4 ora, a validacio miatt +1 ora). A legnagyobb idoigeny:

FAZIS A — Terv elkeszitese (~2 ora):
1. 23 oldal audit (~30-45 perc, Glob + Read mindegyiket)
2. IA ujratervezes + journey map (~30 perc)
3. 4 journey reszletes definicio (~45-60 perc, mert mindegyik ~50 sor + backend chain)
4. Figma wireframe (~30 perc, ha MCP elerheto; ~10 perc ha ASCII)
5. Migracios terv (~15 perc)

FAZIS B — 2-koros validacio (~1 ora):
6. Validacio 1. kor (plan-validator subagent, ~10-15 perc)
7. Javitas 1. kor (~15-20 perc, KRITIKUS + MAJOR hibak)
8. Validacio 2. kor (uj subagent friss szemmel, ~10-15 perc)
9. Javitas 2. kor (~10 perc, polish + regression)

FAZIS C — Lezaras (~15 perc):
10. Plan update 58 + commit + KESZ jelentes

**Ha a 2. kor validacio BLOKKOLO hibat talal** (pl. hianyzo fo szekcio, nem konzisztens journey map): a LEPES 10 javitas hosszabb lesz, es NEM commit-olunk amig nem teljes. Szuksegszeru eseten 3. kor validacio + javitas is inditando (a terv flexibilisen kezeli).

---

## KIMENETI ARTEFAKTUMOK (B6 vege)

### Committed (git-be kerul)

1. **`01_PLAN/63_UI_USER_JOURNEYS.md`** (UJ) — A fo kimenet, 6 szekcio + 2 validacios kommentar-blokk:
   - § 1 Portal Audit (23 oldal)
   - § 2 Uj Information Architecture (6 csoport, indoklas)
   - § 3 Holisztikus Journey Map (ASCII + kereszt-ref)
   - § 4 4 Reszletes Journey Definicio (J1-J4, Journey 4 bovitve B5.1 + B5.2 tartalommal)
   - § 5 Wireframe Referenciak (Figma frame-ek VAGY ASCII)
   - § 6 B8 Migracios Priorizalt Terv
   - `<!-- B6 VALIDATION ROUND 1 FIXES -->` kommentar-blokk
   - `<!-- B6 VALIDATION ROUND 2 FIXES -->` kommentar-blokk

2. **`01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md`** (MODOSITOTT) — B6 row DONE marker + S31 timestamp + commit SHA

3. **`aiflow-admin/figma-sync/PAGE_SPECS.md`** (MODOSITOTT) — minden 23 oldalhoz journey cimke + 2 uj Figma frame entry

### Validacios riportok (NEM committed, csak audit trail)

4. **`out/b6_validation_round1.md`** — plan-validator 1. kor strukturalt riport (PASS / FAIL / MISSING / verdict)
5. **`out/b6_validation_round2.md`** — plan-validator 2. kor strukturalt riport (regression check + uj hiba + minosegszcore)

### Figma (opcionalis)

6. **Figma wireframe frame-ek** — 2 uj frame a fo Figma fileban (ha Figma MCP elerheto):
   - Sidebar navigacio (journey-based, 6 csoport)
   - Dashboard (4 kartya + aktivitas panel)

---

## KESZ JELENTES FORMATUM (LEPES 11 utan)

A session vege EXPLICIT "B6 DONE" jelentessel zarjon a felhasznalonak:

```
# S31 — B6 Portal Struktura + 4 User Journey DONE

## Kimenet
- 01_PLAN/63_UI_USER_JOURNEYS.md: {X} sor, 6 szekcio + 2 validacios kommentar-blokk
- aiflow-admin/figma-sync/PAGE_SPECS.md: 23 oldal journey mapping + {N} uj Figma frame ID

## Validacio Eredmeny

### 1. kor (out/b6_validation_round1.md)
- Osszes hiba: {A} (KRITIKUS: {X}, MAJOR: {Y}, MINOR: {Z})
- Javitott: {X + Y + (lehetoseg szerint Z)}
- Deferred: {lista}

### 2. kor (out/b6_validation_round2.md)
- Regression check: {PASS/FAIL} — 1. kor javitasok mind benne vannak
- UJ hiba a 2. korben: {B} (KRITIKUS: {X}, MAJOR: {Y}, MINOR: {Z})
- Javitott: {X + Y + (lehetoseg szerint Z)}
- Erthetoseg score: {1-10}
- Implementalhatosag score (B8): {1-10}
- Verdict: DONE

## Commit
{SHA} docs(sprint-b): B6 portal struktura audit + 4 user journey + wireframe (2x validated)

## Kovetkezo session
S32 = B7 — Verification Page v2 (bounding box + per-field confidence szin + diff perzisztencia)
```

---

*Kovetkezo ervenyben: S31 = B6 (Portal audit + 4 journey + wireframe + 2x validacio) → S32 = B7 (Verification Page v2, bounding box + diff) → S33 = B8 (UI Journey implementacio, Journey 1 + 2 E2E)*
