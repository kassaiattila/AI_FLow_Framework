# AIFlow UI — Mock-to-Real Transformation Plan

## Context
A P0-P7 + Polish session soran felultunk 5 skill viewert, de a szamla feldolgozas kivetelevel
MINDEGYIK csupan **mock demo**: statikus adatok, nincs valodi input, nincs valodi feldolgozas.
A felhasznalo jogos kritikaja: "kirakati baba" — szep felulet, de nincs mogotte funkcionalitas.

**A fo problema:** Minden viewer ugyanazt a mintat koveti:
1. Probálja a FastAPI backendet (3s timeout) → mindig fail (nincs futva)
2. Visszaesik mock JSON-ra → felhasznalo nem tudja, hogy demo adatot lat
3. Nincs input mechanizmus (email, cubix) VAGY az input ignoralva (process docs)

**A cel:** Minden viewer legyen OSZINTE (mutassa ha demo) es FUNKCIONALIS (ha a backend elerheto).

## Fazis 1: Alapozas — Backend status + forras jelzes

### 1A. Health check API route
- **Uj fajl:** `aiflow-ui/src/app/api/health/route.ts`
- Pingeli a FastAPI `/health` endpointot `fetchBackend`-del
- Visszaadja: `{ status: "connected"|"offline", skills: { invoice: true, rag: false, ... } }`

### 1B. useBackendStatus hook
- **Uj fajl:** `aiflow-ui/src/hooks/use-backend-status.ts`
- 30 masodpercenkent polloz, `{ status, isDemo, skills }` visszaad
- `isDemo = status === "offline"`

### 1C. Connection Status Banner
- **Uj fajl:** `aiflow-ui/src/components/connection-status.tsx`
- Backend online: zold pont a sidebar fejlecben
- Backend offline: sarga "Demo mod" banner az oldal tetejen
- i18n: `backend.connected`, `backend.offline`, `backend.demoLabel`

### 1D. Source tag minden API valaszban
- **Modositando:** Minden API route ami `fetchBackend`-et hasznal → `source: "backend"|"demo"` field
- Erintett: `/api/emails`, `/api/rag/stream`, `/api/process-docs/generate`, `/api/cubix`

### 1E. i18n kulcsok
- ~20 uj kulcs hu/en: backend statusz, demo labelek, uj input/process labelek

## Fazis 2: Process Documentation — valos backend (legkonnyebb gyors gyozelem)

### 2A. Generate route atiras
- **Modositando:** `aiflow-ui/src/app/api/process-docs/generate/route.ts`
- 1. Probalja: `fetchBackend` (FastAPI workflow endpoint)
- 2. Probalja: `python -m skills.process_documentation --input "user text" --output <dir>` (subprocess)
- 3. Fallback: jelenlegi template clone + `source: "demo"`
- A subprocess minta a `documents/process/route.ts`-bol masolhato (mar mukodik invoice-nal)

### 2B. Valos output olvasas
- A skill `.mmd` (Mermaid), `.json` (extraction+review) fajlokat general
- Az API route beolvassa es ProcessDocResult-kent adja vissza
- A Mermaid client-side rendereles mar mukodik (mermaid@11)

### 2C. Page: demo/live badge
- **Modositando:** `process_documentation/page.tsx`
- `source === "demo"` → sarga "Demo" badge; `"backend"` → zold "Live"
- A "Production" badge csere dinamikusra

## Fazis 3: RAG Chat — valos backend

### 3A. Stream route atiras
- **Modositando:** `aiflow-ui/src/app/api/rag/stream/route.ts`
- 1. Probalja: `fetchBackend` POST `/v1/chat/completions` (mar letezik a FastAPI-ban!)
- 2. Ha sikerul: a valos valaszt tokenekre bontja es SSE-kent streameli (igazi adat, fake streaming)
- 3. Ha nem: mock + `{ type: "source", mode: "demo" }` SSE event az elejen

### 3B. Page: demo/live jelzes
- **Modositando:** `aszf_rag_chat/page.tsx`
- Parsolja a `source` SSE eventet
- Demo modban: "Demo mod" badge + "(demo)" suffix minden valaszon
- Live modban: "86% eval pass" badge + zold "Live"

## Fazis 4: Email Intent — input + feldolgozas

### 4A. Email upload zone
- **Uj fajl:** `aiflow-ui/src/components/email/email-upload-zone.tsx`
- Mintazat: `components/invoice/upload-zone.tsx` (drag-drop, file picker)
- Fogad: `.eml`, `.msg` fajlok

### 4B. Upload + Process API route-ok
- **Uj fajl:** `aiflow-ui/src/app/api/emails/upload/route.ts` — FormData → `data/uploads/emails/`
- **Uj fajl:** `aiflow-ui/src/app/api/emails/process/route.ts` — subprocess: `python -m skills.email_intent_processor classify --input <eml> --output <dir>`

### 4C. Page atiras
- **Modositando:** `email_intent_processor/page.tsx`
- Upload zone hozzaadasa a KPI-k fole
- "Feldolgozas" gomb a feltoltott de feldolgozatlan fajlokhoz
- Demo/Live badge

## Fazis 5: Cubix — oszinte cimkezes

### 5A. Page: oszinte badge
- **Modositando:** `cubix_course_capture/page.tsx`
- "Production" → `t("cubix.resultsViewer")` ("Eredmeny nezo" / "Results Viewer")
- Magyarazo szoveg: "Korabbi pipeline futasok eredmenyei. A pipeline futatasahoz Playwright + video fajlok szuksegesek."

### 5B. API: filesystem scan
- **Modositando:** `aiflow-ui/src/app/api/cubix/route.ts`
- Eloszor: keres `pipeline_state.json` fajlokat a `skills/cubix_course_capture/output/` konyvtarban
- Ha talal: valos adat + `source: "filesystem"`
- Ha nem: mock + `source: "demo"`

## Fazis 6: Invoice batch progress javitas

### 6A. Valos lepes-kovetese
- A jelenlegi `startBatch` fuggveny `setTimeout`-okkal szimulal lepeseket
- Javitas: a subprocess stdout-jat olvassa (PYTHONUNBUFFERED=1 mar be van allitva)
- A skill stdout-ra irja a lepes neveket → ezeket parsolja a progress update-hez

### 6B. Tobb dokumentum kezeles
- A progress bar jelenleg 1 dokumentumot mutat egyszerre
- Javitas: osszes dokumentum statusza latszik (kesz/fut/varakozik)
- Hasonlo a Cubix pipeline-progress mintahoz (tobb fajl parhuzamos megjelenitese)

## Fazis 7: Egysegesitest feldolgozasi UI

### 7A. Kozos ProcessingPipeline komponens
- **Uj fajl:** `aiflow-ui/src/components/processing-pipeline.tsx`
- Vizualis lepes-jelzo: `step name → status icon → duration`
- Hasznalva: invoice, process-docs, email, rag-chat feldolgozas kozben
- `source` badge: "Demo" vagy "Live"

## Vegrehajtasi sorrend es statusz (2026-03-30)

```
Fazis 1 (Alapozas)      → KESZ ✓ — health check, useBackendStatus, connection-status, source tag
Fazis 2 (Process Docs)   → KESZ ✓ — subprocess fallback, review.json export, source badge
Fazis 3 (RAG Chat)       → KESZ ✓ — fetchBackend 60s, SSE source event, dynamic badge
Fazis 4 (Email)           → KESZ ✓ — upload zone, /api/emails/upload+process, source badge
Fazis 5 (Cubix)           → KESZ ✓ — filesystem scan, "Results Viewer" badge + hint
Fazis 6 (Invoice batch)   → KESZ ✓ — fake step timer torolve, honest progress
Fazis 7 (Egysegesites)    → KESZ ✓ — ProcessingPipeline, PipelineBar, SkillViewerLayout
Fazis 8 (Szabalyok)       → RESZBEN — CLAUDE.md frissitve, command fajlok NINCS

EXTRA: i18n cleanup       → KESZ ✓ — 0 hardcoded Hungarian string
EXTRA: Honest statuszok   → KESZ ✓ — SkillStatus tipus, dashboard + sidebar frissitve
EXTRA: Layout redesign    → KESZ ✓ — egyseges Input→KPIs→PipelineBar→Tabs sorrend
```

### MI NEM TORTENT MEG (valos backend)
A fazisok a UI OLDALT egysegesitettek es oszinteve tettek.
A VALOS FELDOLGOZAS meg mindig fugg:
1. API kulcsoktol (.env: OPENAI_API_KEY)
2. Docker servicektol (PostgreSQL, Redis, Kroki)
3. FastAPI backend futasatol

Reszletek: `01_PLAN/38_UI_REALITY_STATUS.md`

## Kritikus fajlok

| Fajl | Miert kritikus |
|------|----------------|
| `lib/backend.ts` | Minden backend kommunikacio ezen megy at |
| `api/documents/process/route.ts` | Referencia subprocess minta (invoice) |
| `api/rag/stream/route.ts` | A legkomplexebb mock (fake streaming) |
| `lib/i18n.ts` | Minden uj string ide kerul |
| `components/connection-status.tsx` | Az "oszinteseeg" komponens |

## Verifikacio

Minden fazis utan:
```bash
npx vitest run          # 64+ teszt pass
npx next build          # 0 hiba
npm run dev             # Manualis teszt:
                        #   1. Backend leallitva → "Demo mod" banner latszik
                        #   2. Backend elinditva → "Connected" zold pont
                        #   3. Skill oldal: demo adat jelolve, live adat jeloles nelkul
                        #   4. HU/EN toggle: MINDEN szoveg valtozik
```

## Fazis 8: Szabalyok rogzitese (CLAUDE.md + command fajlok)

### 8A. CLAUDE.md — uj "Mock vs Real" szekcio
- **Modositando:** `CLAUDE.md` — uj szekcio a "MANDATORY Next.js UI Development Rules" utan
- Tartalma:

```markdown
## MANDATORY: No Silent Mock Data (STRICT!)

### The Honesty Rule
> **A user MUST always know whether they see real or demo data.**
> Silent fallback to mock data is FORBIDDEN. Every mock must be visibly labeled.

### Backend Connection Rules
- Every API route that uses `fetchBackend()` MUST return a `source` field: `"backend"` or `"demo"`
- Every page MUST show "Demo mod" banner when `source === "demo"`
- NEVER pretend mock data is real (no fake streaming of hardcoded answers)
- Connection status (useBackendStatus hook) MUST be visible in the sidebar

### Viewer Completeness Rules
- A viewer is NOT complete unless it has: INPUT mechanism → REAL PROCESSING → REAL OUTPUT
- If a skill cannot process (backend down), show "Demo" label + mock data
- If a skill has no input mechanism, it's a "Results Viewer" not a "Viewer"
- Status badges must be honest: "Production" only if actually works, "Demo" if mock, "Results Viewer" if read-only

### Subprocess Pattern (for skill execution from UI)
- Reference implementation: `aiflow-ui/src/app/api/documents/process/route.ts`
- Pattern: `execFileAsync(PYTHON, ["-m", "skills.<name>", ...args])`
- ALWAYS try FastAPI first (fetchBackend), subprocess second, mock last
- ALWAYS tag output with source
```

### 8B. Command fajlok frissitese

#### `/ui-viewer.md` kiegeszites:
- Uj szekcio: "Backend Integration Checklist"
  - [ ] API route tries fetchBackend → subprocess → mock fallback
  - [ ] Response includes `source: "backend"|"demo"` field
  - [ ] Page shows Demo/Live badge based on source
  - [ ] Input mechanism exists (upload, text form, etc.)
  - [ ] Real processing callable (subprocess or API)
  - [ ] Mock data clearly labeled — NEVER silent fallback

#### `/ui-page.md` kiegeszites:
- Template-be beepiteni: `source` field kezelese
- Demo banner megjelenites minta

#### `/dev-step.md` kiegeszites:
- Uj checkpoint: "Mock vs Real audit"
  - Ellenorizni: van-e input? Van-e valos feldolgozas? Jelolve van-e a demo adat?

### 8C. Memory frissites
- `feedback_ui_depth.md` kiegeszites: "No silent mock" szabaly
- Uj memory: `feedback_no_silent_mock.md` — a tanulsag rogzitese

### 8D. 01_PLAN/ terv dokumentum
- Uj fajl: `01_PLAN/36_MOCK_TO_REAL_PLAN.md` — a teljes terv masolata archivalasra
  (a `.claude/plans/` efemer, a 01_PLAN/ vegleges)

