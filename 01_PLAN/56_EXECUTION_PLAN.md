# AIFlow v1.2.0 — Execution Plan

> **Szulo terv:** `48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md`
> **Cel:** Realisztikus, modularis, visszatesztelheto vegrehajtasi terv — ciklusokban.

---

## 1. Fejlesztesi Ciklus Modell

Minden ciklus (1-2 session) ugyanazt a 6 lepest koveti:

```
┌─────────────────────────────────────────────────────┐
│                  FEJLESZTESI CIKLUS                  │
│                                                      │
│  1. TERVEZES    — terv olvasas, scope pontositas     │
│       ↓                                              │
│  2. FEJLESZTES  — kod iras, adapter/service/API      │
│       ↓                                              │
│  3. TESZTELES   — unit + integracio + E2E (VALOS!)   │
│       ↓                                              │
│  4. DOKUMENTALAS — commit, terv frissites, CHANGELOG  │
│       ↓                                              │
│  5. FINOMHANGOLAS — review, bug fix, optimalizalas   │
│       ↓                                              │
│  6. SESSION PROMPT — kovetkezo session kontextus      │
│                                                      │
│  → KOVETKEZO CIKLUS                                  │
└─────────────────────────────────────────────────────┘
```

### Ciklus szabalyok:
- **Egy ciklus = 1 fazis** (vagy 1 al-fazis ha nagy)
- **Nem lepunk tovabb** amig a tesztek nem PASS-olnak
- **Minden ciklus vegen:** git commit + terv frissites + session prompt
- **Stablitas ellenorzes:** L0 smoke test MINDEN ciklus elejen es vegen

---

## 2. Vegrehajtasi Sorrend

### Tier 0: Elokeszites (1 session)

| Ciklus | Tartalom | Output |
|--------|----------|--------|
| **C0** | Smoke test script, CLAUDE.md frissitesek, Untitled UI init, session prompt | `scripts/smoke_test.sh`, frissitett CLAUDE.md, session prompt |

**C0 reszletes:**
1. Ird meg: `scripts/smoke_test.sh` (L0 smoke test — 30s alatt)
2. Frissitsd: root CLAUDE.md v1.2.0 szekcio
3. Frissitsd: `01_PLAN/CLAUDE.md` szamok (26 migracio, stb.)
4. Futtasd: `npx untitledui@latest init` (ha meg nincs)
5. Ird meg: session restart prompt v1.2.0
6. Commitold
7. **GATE:** smoke test PASS

---

### Tier 1: Core Orchestration (3-4 session, 5 ciklus)

| Ciklus | Fazis | Tartalom | Teszt | Output |
|--------|-------|----------|-------|--------|
| **C1** | P1 | Adapter base + 6 adapter | Unit: minden adapter | `src/aiflow/pipeline/` mappa, 9 fajl |
| **C2** | P2 | YAML schema + Jinja2 + compiler | Unit: parse, resolve, compile | 4 fajl (schema, template, compiler, parser) |
| **C3** | P3 | PipelineRunner + DB + Alembic 027 | Integration: YAML → DAG → run → DB | runner.py, repository.py, migration 027 |
| **C4** | P4 | API endpoints + triggers | curl: MINDEN endpoint 200 OK | pipelines.py router, triggers.py |
| **C5** | P5 | Admin UI (Pipelines + PipelineDetail) | Playwright E2E | 2 TSX, router, sidebar, i18n |

**C1 reszletes (Adapter Layer):**
```
1. TERVEZES: Olvasd 48 Phase 1 + 50 (service interfeszek)
2. FEJLESZTES:
   - src/aiflow/pipeline/__init__.py
   - src/aiflow/pipeline/adapter_base.py (ServiceAdapter + AdapterRegistry)
   - src/aiflow/pipeline/adapters/__init__.py (auto-discovery)
   - adapters/email_adapter.py
   - adapters/classifier_adapter.py
   - adapters/document_adapter.py
   - adapters/rag_adapter.py
   - adapters/media_adapter.py
   - adapters/diagram_adapter.py
3. TESZTELES:
   - tests/unit/pipeline/test_adapter_base.py (registry CRUD)
   - tests/unit/pipeline/test_adapters.py (minden adapter I/O mapping)
   - L0 smoke test PASS (meglevo rendszer nem romlott)
4. DOKUMENTALAS: git commit, 48 frissites (Phase 1 DONE jelzés)
5. FINOMHANGOLAS: code review, ruff lint, type check
6. SESSION PROMPT: "P1 KESZ, kovetkezo P2 (YAML schema)"
```

**C3 reszletes (Runner + DB):**
```
1. TERVEZES: Olvasd 48 Phase 3 + migration 027 spec
2. FEJLESZTES:
   - alembic/versions/027_add_pipeline_definitions.py
   - src/aiflow/pipeline/repository.py (CRUD)
   - src/aiflow/pipeline/runner.py (PipelineRunner)
   - src/aiflow/state/models.py (pipeline_id FK)
3. TESZTELES:
   - alembic upgrade head && alembic downgrade -1 && alembic upgrade head
   - Integration test: YAML → compile → run → check workflow_runs + step_runs
   - L0 smoke test PASS
4. DOKUMENTALAS: commit, 48 frissites
5. FINOMHANGOLAS: —
6. SESSION PROMPT: "P3 KESZ, kovetkezo P4 (API)"
```

**C5 reszletes (UI) — 7 HARD GATE kotelezoen:**
```
GATE 1: /ui-journey → 01_PLAN/PIPELINE_UI_JOURNEY.md
GATE 2-3: curl minden pipeline API endpoint → 200 OK + source: backend
GATE 4: /ui-design (Figma MCP) → PAGE_SPECS.md entry
GATE 5: /ui-page (Pipelines.tsx + PipelineDetail.tsx) → tsc --noEmit PASS
GATE 6: Playwright E2E → 0 console error, HU/EN toggle
GATE 7: PAGE_SPECS.md ↔ TSX konzisztens
```

---

### Tier 1.5: Elso Valos Use Case (1 session)

| Ciklus | Tartalom | Teszt |
|--------|----------|-------|
| **C6** | Invoice automation pipeline (meglevo service-ekbol!) | E2E: email → classify → extract → review |

**FONTOS:** Ez NEM uj service fejlesztes — a meglevo service-eket (email_connector, classifier, document_extractor) lancoljuk ossze az uj pipeline orchestrator-ral.

```yaml
# Ezt a pipeline YAML-t hozzuk letre es futtatjuk:
name: invoice_automation_v1
steps:
  - fetch_emails (meglevo EmailConnectorService)
  - classify_intent (meglevo ClassifierService)
  - extract_documents (meglevo DocumentExtractorService)
  # notification es data_router meg nincs — ezek P6-ban jonnek
  # Egyelore: extract → eredmeny a DB-ben, UI-ban lathato
```

**Cel:** Bizonyitani, hogy a pipeline orchestrator MUKODIK valos adatokkal.

---

### Tier 2: Supporting Services (2-3 session, 4 ciklus)

| Ciklus | Fazis | Tartalom | Teszt |
|--------|-------|----------|-------|
| **C7** | P6A | NotificationService (email + Slack) | Valos email kuldes |
| **C8** | P6D | DataRouterService (filter + file route) | Valos fajl mozgatas |
| **C9** | P6A+D | Invoice pipeline V2 (+ notify + route) | E2E: teljes lanc |
| **C10** | P6C | ServiceManagerService | API: service health + metrics |

**C7 utan:** Invoice pipeline bovitheto notification-nel.
**C8 utan:** Invoice pipeline bovitheto fajl renderezessel.
**C9:** Teljes invoice use case (email → classify → extract → route → notify).

> **P6B (Kafka):** Expliciten HALASZTVA post-v1.2.0-ra. A jelenlegi in-memory MessageBroker elegseges a fejlesztes soran. Kafka integracio kesobbi fazisban, ha production scaling szuksegesse teszi.

---

### Tier 3: Advanced RAG (3-4 session, valaszthato sorrend)

| Ciklus | Fazis | Tartalom | Prioritas |
|--------|-------|----------|-----------|
| **C11** | P7D | RerankerService (bge-m3 + FlashRank) | MAGAS — RAG minoseg javitas |
| **C12** | P7B | AdvancedChunkerService (6 strategia) | MAGAS — RAG ingestion javitas |
| **C13** | P7A+C | DataCleaner + MetadataEnricher | KOZEP — adat minoseg |
| **C14** | P7F | VectorOpsService (HNSW tuning) | KOZEP — teljesitmeny |
| **C15** | P7G | Parser Factory (Unstructured + Tesseract) | ALACSONY — fallback |
| **C16** | P7E | GraphRAGService (MS GraphRAG) | ALACSONY — opcionalis |

**Sorrend rugalmas** — barmely ciklus atugrhato vagy kesobbbre tolhato.

---

### Tier 4: Polish (1-2 session)

| Ciklus | Tartalom |
|--------|----------|
| **C17** | LLM quality: Promptfoo CI/CD, rubric scoring, cost dashboard |
| **C18** | Chat UI modernizacio (markdown, Shiki, keyboard shortcuts) |
| **C19** | Pipeline templates + /new-pipeline command |
| **C20** | Frontend komponens konyvtar (Untitled UI) + PWA setup (vite-plugin-pwa) |

> **UI ciklusok HARD GATE-tel:** C5, C17 (Quality dashboard), C18 (Chat UI), C20 (komponensek + PWA) — mindegyikre a 7 HARD GATE UI pipeline kotelezoen vonatkozik.

---

## 3. Session Prompt Sablon

Minden session vegen generalt prompt a kovetkezo session-hoz:

```markdown
# AIFlow v1.2.0 — Session [N+1] Prompt

> **Datum:** [datum]
> **Elozo session:** Ciklus C[X] — [mit csinalunk]
> **Branch:** main
> **Port:** API 8102, Frontend 5173

## Allapot
- **Tier 1 Core:** [P1 KESZ | P2 KESZ | P3 IN PROGRESS | ...]
- **Tier 2 Support:** [P6A KESZ | ...]
- **Tier 3 RAG:** [P7D KESZ | ...]
- **Utolso commit:** [hash] [message]

## Kovetkezo Ciklus: C[X+1]
**Fazis:** [Phase ID]
**Terv:** [01_PLAN/XX.md hivatkozas]
**Cel:** [1 mondat]

## Elso Teendo
1. L0 smoke test (meglevo rendszer OK?)
2. [Konkret elso feladat]
3. [Konkret masodik feladat]

## Fajl Referencia
| Kategoria | Fajlok |
|-----------|--------|
| Fo terv | `01_PLAN/48_ORCHESTRABLE_SERVICE_ARCHITECTURE.md` |
| Ciklus terv | `01_PLAN/[XX].md` |
| Session doksi | `01_PLAN/[XX]_SESSION[N]_DOCUMENTATION.md` |
```

---

## 4. Minoseg Kapuk (MINDEN ciklusra)

### Ciklus inditas elott:
```bash
./scripts/smoke_test.sh              # L0: meglevo rendszer OK?
cd aiflow-admin && npx tsc --noEmit  # Frontend HIBA NELKUL
```

### Ciklus lezaras elott:
```bash
pytest tests/unit/<affected>/ -v     # Uj + erintett tesztek PASS
./scripts/smoke_test.sh              # L0: regresszio ellenorzes
ruff check src/ skills/              # Lint CLEAN
cd aiflow-admin && npx tsc --noEmit  # Frontend HIBA NELKUL
```

### Ha UI ciklus (C5, C20):
```
7 HARD GATE pipeline (Journey → API → Figma → UI → E2E → Regression → Tag)
```

---

## 5. Kockazatkezeles

| Kockazat | Valoszinuseg | Hatas | Megoldas |
|----------|-------------|-------|---------|
| Meglevo API torik | Alacsony | Magas | L0 smoke test MINDEN ciklus elejen/vegen |
| WorkflowRunner nem tamogatja a for_each-et | Kozep | Kozep | Adapter-szinten kezeljuk (C1-ben teszteljuk) |
| HITL create_and_wait blokkol | Kozep | Kozep | Checkpoint+resume pattern (C7-ben tervezzuk) |
| Untitled UI CLI valtozik | Alacsony | Alacsony | Komponensek a mi reponkba masolodnak |
| LLM koltseg megugrik | Kozep | Kozep | Model tier system (gpt-4o-mini default) |

---

## 6. Osszefoglalas Idovonal

```
C0:  Elokeszites ─────────────────── 1 session
C1-C5: Tier 1 Core ─────────────── 3-4 session
C6:  Elso Use Case (invoice v1) ── 1 session
C7-C10: Tier 2 Support ─────────── 2-3 session
         Invoice pipeline V2 ←──── C9
C11-C16: Tier 3 RAG (valaszthato) ─ 3-4 session
C17-C20: Tier 4 Polish ──────────── 1-2 session
                                    ─────────────
                                    ~12-15 session osszesen
```

**Realisztikus becslés:** 12-15 session a teljes v1.2.0-hoz, de a rendszer MAR HASZNALHATO C6 (Tier 1 + elso use case) utan.

---

## 7. Progress Tracking

Minden ciklus vegén frissitjuk:

```markdown
## Progress (utolso frissites: [datum])

| Ciklus | Fazis | Allapot | Datum | Commit |
|--------|-------|---------|-------|--------|
| C0 | Elokeszites | ⬜ TODO | — | — |
| C1 | P1 Adapter | ⬜ TODO | — | — |
| C2 | P2 Schema | ⬜ TODO | — | — |
| C3 | P3 Runner+DB | ⬜ TODO | — | — |
| C4 | P4 API | ⬜ TODO | — | — |
| C5 | P5 UI | ⬜ TODO | — | — |
| C6 | Invoice v1 | ⬜ TODO | — | — |
| ... | ... | ... | ... | ... |
```
