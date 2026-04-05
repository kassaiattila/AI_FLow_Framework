# Pipeline Orchestrator — User Journey

> **Ciklus:** C5 (Tier 1 — Pipeline UI)
> **Service:** `src/aiflow/pipeline/`
> **API:** `src/aiflow/api/v1/pipelines.py`
> **UI:** `aiflow-admin/src/pages-new/Pipelines.tsx`, `PipelineDetail.tsx`
> **Branch:** `feature/v1.2.0-tier1-pipeline-orchestrator`

---

## Actor

**DevOps / AI Platform Admin** — YAML-alapu pipeline-okat kezel: letrehoz, szerkeszt, futtat, monitoroz. Ismeri a service-eket (email_connector, classifier, document_extractor, stb.) es a YAML szintaxist. Napi szinten 2-5 pipeline-t kezel, futtat.

## Goal

YAML pipeline definiciokat kezelni (CRUD), validalni, futtatni es monitorozni — egyetlen admin feluletrol, valos backend adatokkal.

## Preconditions

- FastAPI backend fut (`localhost:8102`), PostgreSQL + Redis Docker-ben
- Alembic migracio 027 lefutott (`pipeline_definitions` tabla)
- Legalabb 7 adapter regisztralva (email, classifier, document, rag ingest/query, media, diagram)
- Vite frontend fut (`localhost:5173`)

---

## Pages

### Page 1: Pipelines (lista oldal)

**URL:** `/pipelines`
**Cel:** Osszes pipeline attekintese, uj letrehozasa, gyors muveletek.

### Page 2: PipelineDetail (reszletek oldal)

**URL:** `/pipelines/:id`
**Cel:** Pipeline reszletek, YAML megjelenes, validacio, futatas, futasi elozmeny.

---

## Steps (User Journey)

### 1. Pipeline lista megtekintese (Pipelines oldal)

**URL:** `/pipelines`
**Felhasznalo:** Megnyitja a "Pipelines" oldalt a sidebar-bol.

- DataTable: name, version, steps szam, trigger tipus, enabled statusz, created_at
- Szurok: enabled/all toggle
- Ures allapot: "No pipelines yet — create your first pipeline"
- **API:** `GET /api/v1/pipelines`
- **Eredmeny:** Paginalt lista, source=backend badge

### 2. Uj pipeline letrehozas

**Felhasznalo:** "New Pipeline" gombra kattint.

- Modal nyilik: YAML szovegeditor (textarea)
- Peldapipeline eloretoltes (placeholder)
- "Validate" gomb: `POST /api/v1/pipelines/{id}/validate` — zold pipa vagy piros hiba
- "Create" gomb: `POST /api/v1/pipelines`
- **Eredmeny:** Pipeline letrejott, redirect a detail oldalra

### 3. Pipeline reszletek (PipelineDetail oldal)

**URL:** `/pipelines/:id`
**Felhasznalo:** Sor-kattintas vagy "View" gomb a listabol.

- **Header:** Pipeline nev + version + enabled badge
- **Info kartya:** description, trigger type, step count, created/updated at
- **Steps vizualizacio:** vertikalis timeline/lista (step name → service.method, depends_on nyilak)
- **YAML panel:** syntax-highlighted YAML megjelenes (readonly)
- **API:** `GET /api/v1/pipelines/{id}`

### 4. Pipeline validacio

**Felhasznalo:** "Validate" gombra kattint a detail oldalon.

- **API:** `POST /api/v1/pipelines/{id}/validate`
- **Eredmeny:** Valid/invalid badge, adapter availability tablazat
  - Zold: minden adapter elerheto
  - Piros: hianyzo adapterek listazva

### 5. Pipeline szerkesztes

**Felhasznalo:** "Edit" gombra kattint.

- YAML editor (textarea) megjelenik a meglevo yaml_source tartalommal
- Szerkesztes utan "Save" gomb: `PUT /api/v1/pipelines/{id}`
- Enable/disable toggle: `PUT /api/v1/pipelines/{id}` (enabled field)

### 6. Pipeline futtatasa

**Felhasznalo:** "Run" gombra kattint.

- Modal: input parameters megadasa (JSON textarea)
- "Execute" gomb: `POST /api/v1/pipelines/{id}/run` (POST meg nem implementalt — C5-ben placeholder, C6-ban valos futatas)
- **Jegyzet:** A tényleges run endpoint nem reszee C4-nek, UI-ban "Coming soon" felirat

### 7. Futasi elozmeny

**Felhasznalo:** "Runs" tab-ra kattint a detail oldalon.

- DataTable: run_id, status, started_at, duration, error
- Sor-kattintas: `GET /api/v1/pipelines/{id}/runs/{run_id}` — step-level reszletek
- Ures allapot: "No runs yet"
- **API:** `GET /api/v1/pipelines/{id}/runs`

### 8. Pipeline torles

**Felhasznalo:** "Delete" gombra kattint.

- Megerosito dialog: "Are you sure?"
- `DELETE /api/v1/pipelines/{id}`
- Redirect a lista oldalra

### 9. Adapters attekintes

**Felhasznalo:** "Adapters" info megjelenik a detail oldalon vagy kulon szekciokent.

- **API:** `GET /api/v1/pipelines/adapters`
- Tablazat: service_name, method_name, input/output schema nevek

---

## API Endpoints (GATE 2-3 — mind tesztelve C4-ben)

| Method | Path | Tesztelve | Eredmeny |
|--------|------|-----------|----------|
| GET | `/api/v1/pipelines` | PASS | lista, source=backend |
| POST | `/api/v1/pipelines` | PASS | 201, YAML parse + store |
| GET | `/api/v1/pipelines/{id}` | PASS | detail |
| PUT | `/api/v1/pipelines/{id}` | PASS | update |
| DELETE | `/api/v1/pipelines/{id}` | PASS | 204 |
| POST | `/api/v1/pipelines/{id}/validate` | PASS | valid + adapters |
| GET | `/api/v1/pipelines/{id}/runs` | PASS | run lista |
| GET | `/api/v1/pipelines/{id}/runs/{run_id}` | PASS | run detail |
| GET | `/api/v1/pipelines/{id}/yaml` | PASS | yaml export |
| GET | `/api/v1/pipelines/adapters` | PASS | 7 adapter |

---

## UI Components

| Komponens | Tipus | Leiras |
|-----------|-------|--------|
| Pipelines.tsx | Page | Lista oldal, DataTable, "New Pipeline" gomb |
| PipelineDetail.tsx | Page | Tabs: Overview / YAML / Runs |
| StepTimeline | Existing component | Step vizualizacio (mar letezik: `src/components/StepTimeline.tsx`) |

---

## Acceptance Criteria

- [ ] Pipelines lista oldal mutatja a valos pipeline-okat (source=backend)
- [ ] "New Pipeline" modal: YAML bevitel + create
- [ ] PipelineDetail: info kartya + steps lista + YAML panel
- [ ] Validate gomb mukodik (adapter availability)
- [ ] Runs tab mutatja a futasi elozmenyt
- [ ] Enable/disable toggle mukodik
- [ ] Delete megerositessel mukodik
- [ ] i18n: HU/EN toggle MINDEN szovegre
- [ ] Loading, error, empty state kezelve
- [ ] Playwright E2E: navigate → list → create → detail → validate → delete
