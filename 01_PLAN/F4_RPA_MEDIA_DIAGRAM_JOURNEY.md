# F4 RPA + Media + Diagram — User Journey

> **Fazis:** F4 (RPA + Media + Diagram)
> **Forras skillek:** `process_documentation` (production), `cubix_course_capture` (75% complete)
> **Uj szolgaltatasok:** DiagramGeneratorService, MediaProcessorService, RPABrowserService, HumanReviewService
> **Tag:** `v0.12.0-complete-services`

---

## F4a: Diagram Generator Journey

### Actor
**Uzleti elemzo** — uzleti folyamatokat ir le termeszetes nyelven, es vizualis BPMN diagramokat general beloluk. Menti es ujrahasznositja a generalt diagramokat.

### Goal
Termeszetes nyelvi leirasbol BPMN diagram generalas, mentes, listazes, export (SVG/DrawIO/BPMN) — egyetlen admin feluletrol.

### Preconditions
- FastAPI backend fut (`localhost:8100`), Alembic 019 lefutott (generated_diagrams tabla)
- `process_documentation` skill elerheto (LLM konfiguralt)
- Vite frontend fut (`localhost:5174`)

### Steps

#### 1. Process Docs oldal megnyitasa
**URL:** `/process-docs`
- Latja a meglevo Process Documentation nezo oldalt
- **UJ:** "Saved Diagrams" szekció a generated diagramok listajaval
- **API:** `GET /api/v1/diagrams` (lista)

#### 2. Diagram generalas
- Beirja a folyamat leírast a textarea-ba (vagy valaszt presetbol)
- "Generate" gombra kattint
- Pipeline fut: classify → elaborate → extract → review → generate → export
- **API:** `POST /api/v1/diagrams/generate`
- **Eredmeny:** Mermaid diagram megjelenik + review score + automatikusan mentve

#### 3. Generalt diagram megtekintese
- A generalt diagram azonnal latszik a result panelen
- Review score + issues + suggestions lathatoak
- Mermaid kod szerkesztheto (opcionalis)

#### 4. Diagram export
- Export gombok: SVG, DrawIO, BPMN
- **API:** `GET /api/v1/diagrams/{id}/export/{fmt}`
- Letoltes indul a kivalasztott formatumban

#### 5. Mentett diagramok listazasa
- "Saved Diagrams" tabla: user_input (rovid), datum, review score, actions
- **API:** `GET /api/v1/diagrams`
- Kattintasra betolti a diagramot a nezoben

#### 6. Diagram torlese
- Delete gomb → megerosito dialog → torles
- **API:** `DELETE /api/v1/diagrams/{id}`

### API Endpoints (F4a)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | POST | `/api/v1/diagrams/generate` | Diagram generalas + mentes |
| 2 | GET | `/api/v1/diagrams` | Mentett diagramok listazasa |
| 3 | GET | `/api/v1/diagrams/{id}` | Diagram reszletezio |
| 4 | DELETE | `/api/v1/diagrams/{id}` | Diagram torles |
| 5 | GET | `/api/v1/diagrams/{id}/export/{fmt}` | Export (mermaid/svg/drawio/bpmn) |

### UI Pages (F4a)
| Oldal | Route | Komponens | Fo funkcio |
|-------|-------|-----------|------------|
| Process Docs (redesign) | `/process-docs` | `ProcessDocViewer.tsx` (ATALAKITAS) | Generate + Saved list + Export |

### Success Criteria (F4a)
1. Diagram generalas valos LLM-mel (`source: "backend"`)
2. Diagram mentve DB-be (generated_diagrams tabla)
3. Lista oldal mutatja a mentett diagramokat
4. Export SVG/DrawIO/BPMN formatumban mukodik
5. Torles mukodik (confirm dialog)
6. Regi ProcessDocViewer backward kompatibilis
7. HU/EN nyelv valtas MINDEN stringet frissit
8. 0 JavaScript konzol hiba
9. Playwright E2E: describe → generate → save → reload → view → export → delete

---

## F4b: Media Processor Journey

### Actor
**Tudasmenedzser** — video/audio fajlokat tolt fel, amibol strukturalt szoveges atiratot kap (STT pipeline).

### Goal
Video/audio feltoltes → STT (Whisper/Azure) → strukturalt atirat — admin feluletrol.

### Steps
1. Media Upload oldal megnyitasa (`/media`)
2. Video/audio fajl feltoltese (drag-drop)
3. STT pipeline futtatas (Whisper vagy Azure Speech)
4. Atirat megtekintese (strukturalt szekciokkal)
5. Atirat export (TXT/JSON)

### API Endpoints (F4b)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | POST | `/api/v1/media/upload` | Media feltoltes |
| 2 | POST | `/api/v1/media/transcribe` | STT pipeline inditas |
| 3 | GET | `/api/v1/media/results` | Eredmenyek listazasa |
| 4 | GET | `/api/v1/media/results/{id}` | Egy eredmeny reszletezio |

---

## F4c: RPA Browser Journey

### Actor
**Automatizalasi mernok** — YAML-alapu bongeszo automatizaciokat konfigural es futtat.

### Goal
YAML config → bongeszo automatizalas (navigacio, kattintas, kepernyokep) → eredmeny log.

### Steps
1. RPA Config oldal megnyitasa (`/rpa`)
2. YAML config feltoltese vagy szerkesztese
3. RPA vegrehajtás inditasa
4. Execution log megtekintese (lepesenkent)
5. Eredmenyek (kepernyokepek, kinyert adatok) megtekintese

### API Endpoints (F4c)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | POST | `/api/v1/rpa/configs` | Config CRUD |
| 2 | POST | `/api/v1/rpa/execute` | Vegrehajtás inditasa |
| 3 | GET | `/api/v1/rpa/logs` | Execution log listazasa |
| 4 | GET | `/api/v1/rpa/logs/{id}` | Egy log reszletezio |

---

## F4d: Human Review Journey

### Actor
**Vezeto / Jovahagyo** — AI altal generalt eredmenyeket ellenorzi es jovahagyja vagy elutasitja.

### Goal
Review queue → eredmeny megtekintes → approve/reject → workflow folytatodik.

### Steps
1. Review Queue oldal megnyitasa (`/reviews`)
2. Fuggoben levo tetelek megtekintese
3. Tetel reszleteinek ellenorzese
4. Jovahagyas vagy elutasitas (commenttel)
5. Elozmeny megtekintese

### API Endpoints (F4d)
| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/reviews/pending` | Fuggoben levo tetelek |
| 2 | POST | `/api/v1/reviews/{id}/approve` | Jovahagyas |
| 3 | POST | `/api/v1/reviews/{id}/reject` | Elutasitas |
| 4 | GET | `/api/v1/reviews/history` | Elozmeny |

---

## Error Scenarios (F4 osszes)

| Hiba | UI viselkedes |
|------|--------------|
| LLM timeout (diagram) | "Diagram generalas idotullepes. Probald ujra." |
| Skill not available | "process_documentation skill nem elerheto" banner |
| STT provider offline | "Whisper/Azure STT nem elerheto" |
| RPA execution fail | Step-by-step hiba log, utolso sikeres lepes kiemelve |
| File too large | "Fajl tul nagy (max 100MB)" |
| Export format unavailable | "Ez a format nem elerheto ehhez a diagramhoz" |
