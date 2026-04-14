# AIFlow Sprint B — Session 32 Prompt (B7: Verification Page v2 — Bounding Box + Diff + Persistence)

> **Datum:** 2026-04-11
> **Branch:** `feature/v1.3.0-service-excellence` | **HEAD:** `8261e88`
> **Port:** API 8102, Frontend 5174
> **Elozo session:** S31 — B6 DONE (portal audit + 4 journey + wireframe, 1 commit: 8261e88, design-only session, 63_UI_USER_JOURNEYS.md 1059 sor, 2x validalva 0 open CRITICAL)
> **Terv:** `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` (B7 szekcio, sor 1557-1611)
> **Session tipus:** CODE — Verification.tsx v2 deep dive: bounding box + diff + DB persistence + E2E
> **Workflow:** Backend (DB + API) → Frontend (UI v2) → E2E teszt → Commit(ok)

---

## KONTEXTUS

### S31 Eredmenyek (B6 — DONE, 1 commit)

**B6 — Portal Struktura Audit + 4 User Journey (`8261e88`):**
- `01_PLAN/63_UI_USER_JOURNEYS.md` UJ (1059 sor, 6 szekcio: audit + IA + journey map + 4 journey + wireframe + migrations)
- 23 oldal audit: A=1 | B=15 | C=7
- 6-csoportos journey-based sidebar IA tervezve (B8-ban implementacio)
- 4 reszletes journey: J1 Invoice + J2 Monitoring + J3 RAG + J4 Generation
- J1 Journey Verification step = B7 deep dive: bounding box + per-field confidence + diff persistence
- 2-korben validalva (plan-validator subagent): R1: 4 MAJOR fixed, R2: 1 MAJOR regression fixed
- NINCS kodvaltoztatas (design-only session)

**Infrastruktura (v1.3.0 — S31 utan):**
- 27 service | 170 API endpoint (26 router) | 47 DB tabla | 30 migracio
- 22 pipeline adapter | 10 pipeline template | 7 skill | 23 UI oldal
- **1442 unit test** | 129 guardrail teszt | 97 security teszt | **105 E2E** | **96 promptfoo test**

### Jelenlegi Allapot (B7 cel — Verification Page v2)

```
=== B7 KONTEXTUS: MI A JELENLEGI HELYZET? ===

VERIFICATION.TSX jelenlegi allapot (925 sor):
  aiflow-admin/src/pages-new/Verification.tsx
  aiflow-admin/src/verification/
    types.ts                  — 65 sor, DataPoint + DataPointCategory + confidence helpers
    document-layout.ts        — 85 sor, getAllFields() + fieldToBBox() + resolvePath() + PAGE konst
    use-verification-state.ts — 158 sor, useVerificationState() hook (selection, editing, undo/redo)
    MockDocumentSvg.tsx       — 82 sor, fallback SVG ha nincs valos kep

  Jelenlegi Verification.tsx felosztas:
  +---------------------------------------------------+
  |                   TopBar                            |
  +---------------------------+-------------------------+
  |   DocumentCanvas (55%)    | DataPointEditor (45%)   |
  |                            |                         |
  |  Valos kep VAGY Mock SVG  | Mezolista csoportonkent |
  |  Zoom: 50-200%             | (document_meta, vendor, |
  |  Overlay modk:             |  buyer, header,         |
  |    all / low-only / off   |  line_item, totals)     |
  |  Bounding box overlay     |                         |
  |  (PONTATLAN real image-en)| Keyboard: Tab/Enter/E   |
  |                            | Undo/Redo: Ctrl+Z/Y    |
  |                            | Status: Auto/Corrected  |
  +---------------------------+-------------------------+
  |                  BottomBar                          |
  |  Save | Reset | Confirm All | Progress bar          |
  +---------------------------------------------------+

  MI MUKODIK:
  - DocumentCanvas: mock SVG VAGY valos kep (toggle) — de bounding box PONTATLAN valos kepen!
  - DataPointEditor: csoportok, inline edit, confirm, keyboard nav, undo/redo
  - Confidence szin: high (green) / medium (amber) / low (red) per mezo
  - localStorage backup: aiflow_verification_{id}
  - POST /api/v1/documents/{id}/verify → server-re kuldes (de NEM diff table!)
  - Overlay modok: all/low-only/off

  MI NEM MUKODIK / HIANYZO:
  - Bounding box valos PDF-en PONTATLAN (sor 148: "Hide overlays in real image mode
    (bounding boxes are inaccurate on the photo)") — generateVerificationData() 
    hardcoded confidence 0.8 line item-ekhez
  - NINCS verification_edits DB tabla — az edit diff CSAK localStorage-ben el
  - NINCS GET /api/v1/documents/{id}/verifications audit trail endpoint
  - NINCS valodi diff megjelentes (eredeti vs modositott)
  - NINCS approve/reject workflow (a gomb nem persistal)
  - NINCS Reviews.tsx merge (kulon oldal, kulon flow)
  - NINCS Playwright E2E teszt a verification flow-ra
  - NINCS field-type validation (osszeg → szam, datum → datum format)

REVIEWS.TSX jelenlegi allapot (68 sor):
  Kulon oldal (/reviews), pending + history DataTable.
  API: GET /reviews/pending + /reviews/history + POST /reviews/{id}/approve|reject
  B6 terv: merge a Verification-ba, /reviews route backward compat redirect.

DOCUMENTDETAIL.TSX (249 sor):
  Read-only detail, "Verify" gomb → /documents/{id}/verify navigacio.
  Confidence display: 0-100%, szin (>=90% zold, 70-89 amber, <70 piros).

CONFIDENCE ROUTER (192 sor):
  src/aiflow/engine/confidence_router.py
  Auto-approve: >= 0.90 | Review: 0.70-0.89 | Reject: < 0.50
  RoutingDecision enum: AUTO_APPROVED / SENT_TO_REVIEW / REJECTED_FOR_REVIEW

HUMAN REVIEW SERVICE (290 sor):
  src/aiflow/services/human_review/service.py
  HumanReviewItem pydantic, asyncpg pool, create_review(), list_pending(), list_history()
  DB: human_reviews tabla (mar letezik!)

ALEMBIC STATUS: 30 migracio (utolso: 030_add_generated_specs.py)
  NINCS verification_edits tabla meg!

E2E TESZTEK:
  tests/e2e/test_documents.py (63 sor) — alap document lista
  tests/e2e/test_journey_document.py (131 sor) — dashboard → documents → detail nav
  NINCS test_verification.py vagy test_journey_verification.py!

=== B7 CEL: SHOWCASE feluletet csinalni! ===

A Verification Page v2 az AIFlow "showcase" felulete — a legprofibb megoldas kell.
A felhasznalo (penztaros/konyvelo) ITT lat bele a rendszer mukodeseebe:
  - Latja az EREDETI dokumentumot, rajta bounding box-okkal
  - Latja a kinyert adatokat, konfidencia szinnel
  - Javithat, es a javitast a rendszer megjegyzi (diff + audit trail)
  - Elfogadhatja vagy elutasithatja (ami pipeline-ben tovabbmegy)

B7 UTAN a Verification Page:
  - Valos PDF bounding box (react-pdf VAGY canvas overlay)
  - Per-field confidence szin (zold/sarga/piros) ✓ (mar mukodik!)
  - Diff persisztiencia: verification_edits DB tabla + GET audit trail
  - Approve/reject workflow (human_review service integracio)
  - Reviews panel merge (pending queue a Verification oldalon)
  - Playwright E2E: upload → extract → verify → edit → save → retrieve
```

---

## B7 FELADAT: 7 lepes — Backend (DB + API) → Frontend (UI v2) → E2E → Commit

> **Gate:** Verification Page v2 valos szamlaval mukodik: bounding box, edit diff, DB perzisztencia, audit trail, approve/reject, Playwright E2E PASS.
> **Eszkozok:** `/dev-step`, `/regression`, `/lint-check`, Playwright, Alembic
> **Docker:** PostgreSQL (5433), Redis (6379) — KELL! (DB migracio + integracio)

---

### LEPES 1: B7.1 — Alembic migracio: verification_edits tabla

```
Hol: alembic/versions/031_add_verification_edits.py (UJ fajl)
     src/aiflow/models/ (ha kell Pydantic model)

Cel: verification_edits tabla letrehozasa a diff perzisztenciahoz.

KONKRET TEENDOK:

1. Uj Alembic migracio: alembic/versions/031_add_verification_edits.py

   CREATE TABLE verification_edits (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       document_id UUID NOT NULL REFERENCES documents(id),
       field_name VARCHAR(255) NOT NULL,
       field_category VARCHAR(100),  -- document_meta, vendor, buyer, header, line_item, totals
       original_value TEXT,
       edited_value TEXT,
       confidence_score FLOAT,       -- az eredeti LLM confidence erteke
       editor_user_id UUID REFERENCES users(id),
       status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, approved, rejected
       comment TEXT,
       created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
       updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
   );
   CREATE INDEX idx_verification_edits_document ON verification_edits(document_id);
   CREATE INDEX idx_verification_edits_status ON verification_edits(status);

   FONTOS: nullable=True minden uj oszlopra (CLAUDE.md szabaly)!
   FONTOS: DOWN migracio = DROP TABLE verification_edits

2. Pydantic modell (ha meg nincs):
   src/aiflow/models/verification.py (UJ fajl VAGY bovites)
   
   class VerificationEdit(BaseModel):
       id: UUID
       document_id: UUID
       field_name: str
       field_category: str | None = None
       original_value: str | None = None
       edited_value: str | None = None
       confidence_score: float | None = None
       editor_user_id: UUID | None = None
       status: str = "pending"
       comment: str | None = None
       created_at: datetime
       updated_at: datetime

   class VerificationEditCreate(BaseModel):
       field_name: str
       field_category: str | None = None
       original_value: str | None = None
       edited_value: str | None = None
       confidence_score: float | None = None
       comment: str | None = None

   class VerificationEditResponse(BaseModel):
       edits: list[VerificationEdit]
       total: int
       document_id: UUID
       source: str = "backend"

3. Futtasd: alembic upgrade head → tabla letrejott
   Ellenorizd: psql → \dt verification_edits

Gate: verification_edits tabla letezik, Alembic migracio PASS, Pydantic model kész.
```

### LEPES 2: B7.2 — API endpoint-ok (CRUD verification edits)

```
Hol: src/aiflow/api/v1/documents.py (bovites) VAGY uj src/aiflow/api/v1/verifications.py

Cel: 3 uj endpoint a verification edit CRUD-hoz.

KONKRET TEENDOK:

1. POST /api/v1/documents/{document_id}/verifications — Batch save edits
   Body: { edits: VerificationEditCreate[], editor_user_id?: UUID }
   Logic:
     - Torli a meglevo pending editeket a document_id-hoz (UPSERT logic)
     - Inserteli az uj editeket
     - Return: { edits: VerificationEdit[], total: int }
   
   FONTOS: Ez az endpoint valtja ki a jelenlegi POST /documents/{id}/verify-t!
   Az eredeti endpoint NEM toroljuk (backward compat), de az UJ a preferalt.

2. GET /api/v1/documents/{document_id}/verifications — Get all edits for document
   Query params: status (optional), field_name (optional)
   Return: VerificationEditResponse

3. PATCH /api/v1/documents/{document_id}/verifications/approve — Approve all pending
   Body: { reviewer_id: UUID, comment?: str }
   Logic:
     - UPDATE verification_edits SET status='approved', updated_at=now()
       WHERE document_id=X AND status='pending'
     - Ha human_review rekord letezik a dokumentumhoz:
       POST /api/v1/reviews/{review_id}/approve (delegacio a meglevo human_review-hoz)
     - Return: { approved_count: int, document_id: UUID }

4. PATCH /api/v1/documents/{document_id}/verifications/reject — Reject 
   Body: { reviewer_id: UUID, comment: str }  (comment KOTELEZO reject-hez!)
   Logic: hasonlo, status='rejected'

5. GET /api/v1/verifications/history — Global audit trail
   Query params: user_id?, document_id?, status?, limit=50, offset=0
   Return: { edits: VerificationEdit[], total: int }

6. Unit tesztek: tests/unit/test_verification_api.py (UJ)
   - test_save_edits_creates_records
   - test_save_edits_replaces_pending (UPSERT)
   - test_get_edits_returns_all
   - test_approve_changes_status
   - test_reject_requires_comment
   - test_history_with_filters

Gate: 5 endpoint mukodik, 6 unit teszt PASS.
```

### LEPES 3: B7.3 — Frontend: Bounding Box javitas + Diff megjelentes

```
Hol: aiflow-admin/src/pages-new/Verification.tsx (MODOSITAS)
     aiflow-admin/src/verification/ (modulos fajlok)

Cel: Valos bounding box pontossag + diff panel + field-type validation.

KONKRET TEENDOK:

1. BOUNDING BOX JAVITAS (DocumentCanvas):
   Jelenlegi problema: "Hide overlays in real image mode (bounding boxes are inaccurate
   on the photo)" — a bounding box koordinatak NEM illeszkednek a valos kepre.
   
   MEGOLDAS:
   a) A backend `document_extractor` a `docling` konyvtarat hasznalja PDF parse-olasra.
      Docling visszaadja a per-mezo bounding box koordinatakat (normalized 0-1 range).
   b) A jelenlegi `fieldToBBox()` fuggveny (document-layout.ts sor 20-50) HARDCODED
      poziciokat ad vissza! Ezt cserelni kell: a backend-rol kapott `extraction_result`
      JSON-bol kell olvasni a bbox adatokat.
   c) A DocumentCanvas-ban a bbox overlay MINDIG megjelenjen (real image mode-ban IS),
      de a koordinatakat a VALOS docling bbox-bol kell szamolni:
      
      // a backend documents by-id response-ban kell legyen:
      // field.bounding_box = { x: 0.12, y: 0.34, width: 0.25, height: 0.03, page: 1 }
      // Ezek normalized koordinatak (0-1), a canvas meretere skalazva:
      const sx = canvasWidth * bbox.x;
      const sy = canvasHeight * bbox.y;
      const sw = canvasWidth * bbox.width;
      const sh = canvasHeight * bbox.height;
   
   d) Ha a backend NEM ad bbox-ot (regi dokumentumok), fallback a jelenlegi 
      MockDocumentSvg megoldasra (ne torluk, de NE ez legyen az alapertelmezett).
   
   e) Az overlay szineket a confidence level határozza meg:
      - high (>= 0.9): zold keret, halvany zold fill (opacity 0.1)
      - medium (0.7-0.89): sarga keret, halvany sarga fill
      - low (< 0.7): piros keret, halvany piros fill (opacity 0.15 — hangsuly!)
   
   FIGYELEM: Ne tord el a jelenlegi mukodeseket! A mock SVG mode maradjon toggleable.
   Keress a forrasban: "bounding_box" / "fieldToBBox" / "MockDocumentSvg" mintakat.

2. DIFF MEGJELENTES (DataPointEditor bovites):
   Jelenlegi: az editalt mezo "Corrected" badge-et kap, de NEM latszik az eredeti ertek.
   
   UJ: Ha egy mezo modositott (original_value !== current_value), jelenjen meg:
   
   +------------------------------------------+
   | Invoice Number                    [Edit] |
   | Eredeti:  INV-2026-001     (0.95 conf)   |
   | Modositott: INV-2026-0001  ← (corrected) |
   | Diff: "001" → "0001"                     |
   +------------------------------------------+
   
   Implementacios javaslat:
   - DataPointEditor-ben uj `DiffLine` komponens:
     if (dp.original_value !== dp.current_value) {
       <div className="text-xs text-gray-500 line-through">{dp.original_value}</div>
       <div className="text-sm font-medium text-amber-700">{dp.current_value}</div>
     }
   - Ha nincs valtozas: csak az erteket mutatja (nem kell diff)
   
3. FIELD-TYPE VALIDACIO:
   Jelenlegi: inline textbox, barmit ir be a user.
   
   UJ: a mezo tipusatol fuggoen validacio:
   - osszeg mezok (net_amount, vat_amount, gross_amount, unit_price): 
     → szam format (1234.56 vagy 1 234,56), REGEX: /^[\d\s.,]+$/
   - datum mezok (invoice_date, due_date):
     → ISO format (YYYY-MM-DD) VAGY HU format (YYYY.MM.DD.)
   - adoszam (tax_number):
     → 8 vagy 11 jegy, kotojelekkel: /^\d{8}(-\d{1}-\d{2})?$/
   - egyeb: szabad szoveg (nincs validacio)
   
   Ha hibas: piros keret + error tooltip. NEM engedi a confirmot amig hibas.
   
   Implementalas:
   - types.ts-ben uj FIELD_VALIDATORS map:
     { 'net_amount': numericValidator, 'invoice_date': dateValidator, ... }
   - use-verification-state.ts-ben: validate(fieldName, value) → true/false + errorMsg

4. AZ EDITEN TESZTELESE (manualis sanity check):
   - `cd aiflow-admin && npx tsc --noEmit` → 0 TypeScript hiba
   - `cd aiflow-admin && npm run dev` → ellenorizd localhost:5174/#/documents/*/verify

Gate: Bounding box VALOS keprol olvas, diff megjelentes latszik, field validation mukodik,
      tsc --noEmit 0 hiba.
```

### LEPES 4: B7.4 — Frontend: Reviews merge + Approve/Reject workflow

```
Hol: aiflow-admin/src/pages-new/Verification.tsx (bovites)
     aiflow-admin/src/pages-new/Reviews.tsx (backward compat redirect)

Cel: A Verification oldalon approve/reject + pending review queue integracio.

KONKRET TEENDOK:

1. APPROVE / REJECT GOMBOK (BottomBar bovites):
   Jelenlegi BottomBar: Save | Reset | Confirm All | Progress bar
   
   UJ BottomBar:
   Save Draft | Approve All | Reject | Progress bar
   
   - "Save Draft": mentei a pending editeket → PATCH /verifications (meglevo logika)
   - "Approve All": 
     a) Menti az editeket (POST /documents/{id}/verifications)
     b) Approve: PATCH /documents/{id}/verifications/approve
     c) Ha sikeres → zold alert "Dokumentum elfogadva" → redirect /documents
   - "Reject":
     a) Modal: "Elutasitas indoka" textarea (kotelezo!)
     b) PATCH /documents/{id}/verifications/reject body: { comment: "..." }
     c) Piros alert "Dokumentum elutasitva" → redirect /documents
   
   Admin-only: csak admin/reviewer role-al elerheto (isAdmin() check).

2. REVIEW QUEUE PANEL (opcionalis, Verification oldalon):
   Ha a dokumentum confidence_router altal "SENT_TO_REVIEW" → a Verification oldalon
   megjelenik egy sarga banner: "Ez a dokumentum emberi ellenorzesre var (confidence: 0.78)"
   
   Implementalas:
   - useApi() hook: GET /api/v1/reviews/pending?entity_id={document_id}
   - Ha van pending review → banner + review details
   - Ha nincs → sima verifikacio mode

3. REVIEWS.TSX BACKWARD COMPAT:
   NE torold a Reviews.tsx fajlt es a /reviews route-ot!
   De az oldalon adj hozzá egy banner-t:
   
   "A review funkció áthelyezve a Verifikáció oldalra.
    [Ugrás a Verifikációhoz →]"
   
   Es minden pending review item "Review" gombja → `/documents/{entity_id}/verify`
   (nem a regi inline approve/reject).

4. DIFF EXPORT (approve utan):
   Ha a user approve-ol, a verification_edits tablabol generalhato:
   - GET /api/v1/documents/{id}/verifications?status=approved → JSON
   - Frontend: "Export CSV" gomb → download (field_name, original, edited, confidence)
   
   Ez Sprint C nice-to-have, de az API-nak mar MOST kesz kell lennie.

Gate: Approve/Reject workflow mukodik, Reviews banner a Verification-on,
      /reviews backward compat megvan.
```

### LEPES 5: B7.5 — Playwright E2E teszt

```
Hol: tests/e2e/test_verification_v2.py (UJ fajl)

Cel: Teljes Verification flow E2E (valos adatokkal, NEM mock!).

KONKRET TEENDOK:

1. Uj E2E teszt fajl: tests/e2e/test_verification_v2.py

   class TestVerificationV2:

     def test_verification_full_flow(self, authenticated_page: Page):
       """Upload PDF → LLM extract → verify page → bounding box → edit → save → retrieve."""
       
       # STEP 1: Upload egy test szamla PDF-et
       page = authenticated_page
       navigate_to(page, "/documents")
       # Upload tab, drag-and-drop VAGY file input
       # Var amig a process stream befejezodik (SSE)
       
       # STEP 2: Navigalas a Verification oldalra
       # Keres a document lista-ban → detail → "Verify" gomb
       # VAGY kozvetlen /documents/{id}/verify
       
       # STEP 3: Bounding box ellenorzes
       # Canvas renderelt → overlay lathato
       # Kattintas egy mezo bounding box-ra → DataPointEditor-ben kivalasztas
       
       # STEP 4: Mezo szerkesztes
       # Kattintas "Edit" gomb → textarea → uj ertek → Enter (confirm)
       # Ellenorzes: diff lathato (eredeti vs uj)
       
       # STEP 5: Mentes
       # "Save Draft" gomb kattintas → POST /verifications
       # Ellenorzes: save status "Saved" megjelenik
       
       # STEP 6: Visszakereses API-bol
       # GET /api/v1/documents/{id}/verifications → valid JSON
       # Ellenorzes: field_name, original_value, edited_value megvan
       
       # STEP 7: Approve
       # "Approve All" gomb → redirect /documents
       # Ellenorzes: GET /verifications → status='approved'

     def test_verification_reject_requires_comment(self, authenticated_page: Page):
       """Reject without comment should show error."""
       # Navigalas → Reject gomb → modal megjelenik
       # Submit ures comment-tel → error message
       # Submit kommenttel → sikeres reject

     def test_verification_diff_display(self, authenticated_page: Page):
       """Edit a field and verify diff display shows original vs edited."""
       # Navigalas → edit mezo → ellenorzes: line-through eredeti, bold uj

     def test_verification_field_validation(self, authenticated_page: Page):
       """Amount field rejects non-numeric input."""
       # Navigalas → edit osszeg mezo → "abc" beiras → piros keret + error tooltip

2. Teszt futtatas:
   cd aiflow-admin && npm run dev &
   uvicorn src.aiflow.api.main:app --port 8102 &
   pytest tests/e2e/test_verification_v2.py -v --headed (elso alkalommal lathatoan)

FIGYELEM: NEM mock! Valos PostgreSQL (Docker 5433), valos FastAPI, valos Vite dev server.
Ha nincs teszt szamla PDF: hasznalj egy out/ directory-ban levo test.pdf-et,
VAGY generalj egyet a teszt elott (a document_extractor kezel barmilyen PDF-et).

Gate: legalabb 2 E2E teszt PASS (full_flow + reject_comment).
```

### LEPES 6: B7.6 — Unit tesztek + regresszio

```
Hol: tests/unit/ (uj fajlok)

Cel: Unit tesztek a verification API-hoz + TypeScript check + regresszio.

KONKRET TEENDOK:

1. /regression — futtasd a teljes regressziot (1442 unit + 105 E2E + 96 promptfoo)
   SEMMI nem torik el a B7 valtozasoktol!

2. /lint-check — ruff + tsc --noEmit
   0 uj lint warning!

3. TypeScript check:
   cd aiflow-admin && npx tsc --noEmit → 0 hiba
   (A Verification.tsx modositasok NEM torhetik el a tipusokat)

4. Unit tesztek (ha meg nem lett a LEPES 2-ben):
   tests/unit/test_verification_api.py:
   - test_save_edits_creates_records
   - test_get_edits_returns_all
   - test_approve_changes_status
   - test_reject_requires_comment
   - test_history_with_filters
   - test_save_replaces_pending_edits

Gate: /regression PASS, /lint-check PASS, tsc PASS, uj unit tesztek PASS.
```

### LEPES 7: B7.7 — Plan update + Commit(ok)

```
/update-plan → 58 B7 row DONE + datum + commit SHA(k)
             CLAUDE.md + 01_PLAN/CLAUDE.md kulcsszamok frissitese:
               - DB tablek: 47 → 48 (+verification_edits)
               - Migraciok: 30 → 31 (+031_add_verification_edits)
               - E2E: 105 → 105+ (uj verification E2E-k)
               - Unit: 1442 → 1442+ (uj verification unit tesztek)

Commit strategia — KULON COMMITOK feature-onkent:
  1. feat(sprint-b): B7.1 alembic 031 verification_edits + API endpoints
     (alembic migracio + Pydantic model + 5 endpoint + unit tesztek)
  
  2. feat(sprint-b): B7.2 Verification.tsx v2 — bounding box + diff + field validation
     (Verification.tsx + verification module modositasok + Reviews redirect)
  
  3. test(sprint-b): B7.3 Verification E2E — full flow + reject + diff + validation
     (tests/e2e/test_verification_v2.py)
  
  4. docs(sprint-b): B7 plan update + key numbers
     (58 plan + CLAUDE.md)

VAGY ha szorosan osszefugg: 2 commit (backend + frontend/teszt).

Commit mindegyikhez:
  Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
```

---

## VEGREHAJTAS SORRENDJE

```
=== FAZIS A: BACKEND (LEPES 1-2) ===

--- LEPES 1: Alembic migracio ---
alembic/versions/031_add_verification_edits.py
alembic upgrade head → tabla kesz
Pydantic model → VerificationEdit, VerificationEditCreate, VerificationEditResponse

--- LEPES 2: API endpoints ---
5 endpoint (POST save, GET by-doc, PATCH approve, PATCH reject, GET history)
6 unit teszt
Teszteles: pytest tests/unit/test_verification_api.py -v

>>> Backend KESZ — DB + API + unit tesztek.


=== FAZIS B: FRONTEND (LEPES 3-4) ===

--- LEPES 3: Bounding box + Diff + Validation ---
Verification.tsx modositas:
  - fieldToBBox() → valos backend bbox koordinatak (document-layout.ts)
  - DocumentCanvas: overlay MINDIG mukodik real image-en is
  - DataPointEditor: DiffLine komponens (original vs edited)
  - Field-type validacio: numericValidator, dateValidator, taxNumberValidator
tsc --noEmit → 0 hiba

--- LEPES 4: Reviews merge + Approve/Reject ---
Verification.tsx bovites:
  - BottomBar: Save Draft | Approve All | Reject
  - Approve → POST edits + PATCH approve → redirect
  - Reject → modal comment → PATCH reject → redirect
  - Banner: "Ez a dokumentum emberi ellenorzesre var"
Reviews.tsx: backward compat banner + link

>>> Frontend KESZ — UI modositasok + Reviews merge.


=== FAZIS C: TESZTEK + LEZARAS (LEPES 5-7) ===

--- LEPES 5: Playwright E2E ---
tests/e2e/test_verification_v2.py (4 teszt)
Docker: PostgreSQL + Redis kell!
pytest tests/e2e/test_verification_v2.py -v --headed

--- LEPES 6: Regresszio ---
/regression → 1442+ unit + 105+ E2E + 96 promptfoo
/lint-check → ruff + tsc
Semmi nem torik!

--- LEPES 7: Plan + Commit ---
/update-plan → 58 B7 DONE
2-4 commit (feature-enkent)
```

---

## KORNYEZET ELLENORZES

```bash
# Branch + HEAD
git branch --show-current     # → feature/v1.3.0-service-excellence
git log --oneline -3           # → 8261e88, c7079c6, 41d3e60

# Docker KELL!
docker ps | grep -E "postgres|redis"   # → mindketto fut? Ha nem: docker compose up -d db redis

# Alembic allapot
alembic current                        # → 030 (utolso: add_generated_specs)
alembic heads                          # → egyetlen head

# Jelenlegi Verification forras:
wc -l aiflow-admin/src/pages-new/Verification.tsx     # → 925 sor
wc -l aiflow-admin/src/verification/*.ts aiflow-admin/src/verification/*.tsx  # → 390 sor
ls aiflow-admin/src/verification/                     # → 4 fajl

# Jelenlegi E2E:
ls tests/e2e/test_*document* tests/e2e/test_*verif*   # → 2 fajl, NINCS verification!

# API router ellenorzes:
grep -n "def.*verif" src/aiflow/api/v1/documents.py   # → letezik-e mar verify endpoint?

# Human review service:
wc -l src/aiflow/services/human_review/service.py     # → 290 sor
```

---

## MEGLEVO KOD REFERENCIAK (olvasd el mielott irsz!)

```
# KRITIKUS — ezeket MINDENKEPPEN olvasd MIELOTT modositasz:
aiflow-admin/src/pages-new/Verification.tsx            — 925 sor, FO MODOSITASI CELPONT
aiflow-admin/src/verification/types.ts                 — DataPoint + DataPointCategory tipusok
aiflow-admin/src/verification/document-layout.ts       — fieldToBBox() — EZT KELL CSERELNI!
aiflow-admin/src/verification/use-verification-state.ts — hook (undo/redo + selection)
aiflow-admin/src/verification/MockDocumentSvg.tsx      — fallback SVG (MARAD, de nem default)

# API — bovitendo:
src/aiflow/api/v1/documents.py                         — 1125 sor, verify endpoint mar van
src/aiflow/api/v1/human_review.py                      — 179 sor, approve/reject itt van

# Services:
src/aiflow/services/human_review/service.py            — 290 sor, HumanReviewService
src/aiflow/engine/confidence_router.py                 — 192 sor, RoutingDecision

# Alembic referenciak (legutobbiak):
alembic/versions/030_add_generated_specs.py            — utolso migracio (mintanak)
alembic/versions/027_add_pipeline_definitions.py       — FK mintanak

# E2E referencia:
tests/e2e/test_journey_document.py                     — 131 sor, document journey minta
tests/e2e/conftest.py                                  — navigate_to(), authenticated_page fixture

# B6 terv (Journey 1 Verification lepes):
01_PLAN/63_UI_USER_JOURNEYS.md                         — § 4 Journey 1, Lepes 3 (sor ~355)

# B7 plan referencia:
01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md               — B7 szekcio (sor 1557-1611)

# Kulon oldalak:
aiflow-admin/src/pages-new/Reviews.tsx                 — 68 sor, backward compat target
aiflow-admin/src/pages-new/DocumentDetail.tsx          — 249 sor, "Verify" gomb forras
```

---

## FONTOS SZABALYOK (CODE session)

- **Verification.tsx a showcase** — a leheto legprofibb megoldas kell. Nincs placeholder, nincs "majd kesobb", nincs hardcoded mock.
- **NE tord el a jelenlegi Verification mukodeseit!** A mock SVG toggle MARAD, a keyboard nav MARAD, az undo/redo MARAD. Bovitunk, nem ujrairunk.
- **Async-first** — minden I/O async (await). A FastAPI endpoint-ok mind async def.
- **Pydantic everywhere** — config, API models, step I/O, DB schemas.
- **structlog** — never print(), always `logger.info("event", key=value)`.
- **DB changes = ALWAYS Alembic** — never raw SQL. `nullable=True` for new columns.
- **REAL testing** — NEM mock PostgreSQL/Redis. Docker kell a teszt futatashoz.
- **Package manager = uv** (NOT pip, NOT poetry).
- **Field-type validacio NEM blokkolhat** — ha a validator nem tudja kezelni, szabad szoveg fallback (ne tord el az alap mukodeseket!).
- **NE commitolj failing tesztet!** Ha egy E2E teszt nem stabil, `@pytest.mark.skip(reason="...")` es dokumentald.
- **Alembic migracio DOWN is kell** — minden migration REVERSIBLE.
- **i18n**: minden uj string `translate()` a Verification.tsx-ben (aiflow.verification.* kulcsok, hu.json + en.json).
- **`.code-workspace`, `out/`, `100_*.md`, session prompt NE commitold.**
- **Branch:** SOHA NE commitolj main-ra — minden a feature/v1.3.0-service-excellence branchen.

---

## B7 GATE CHECKLIST

```
FAZIS A — BACKEND:

B7.1 — Alembic:
[ ] alembic/versions/031_add_verification_edits.py letezik
[ ] verification_edits tabla letrejott (alembic upgrade head)
[ ] Pydantic model: VerificationEdit + VerificationEditCreate + Response
[ ] Migracio REVERSIBLE (alembic downgrade -1 → tabla torolve)

B7.2 — API:
[ ] POST /api/v1/documents/{id}/verifications — save edits
[ ] GET /api/v1/documents/{id}/verifications — get edits
[ ] PATCH /api/v1/documents/{id}/verifications/approve — approve all pending
[ ] PATCH /api/v1/documents/{id}/verifications/reject — reject (comment kotelezo)
[ ] GET /api/v1/verifications/history — global audit trail
[ ] 6 unit teszt PASS

FAZIS B — FRONTEND:

B7.3 — Bounding box + Diff:
[ ] Bounding box VALOS koordinatakkal mukodik (real image mode)
[ ] Mock SVG toggle MARAD es mukodik (fallback)
[ ] Diff megjelentes: eredeti vs modositott (DiffLine komponens)
[ ] Field-type validacio: osszeg, datum, adoszam
[ ] tsc --noEmit 0 hiba

B7.4 — Reviews merge + Approve/Reject:
[ ] BottomBar: Save Draft | Approve All | Reject
[ ] Approve workflow: save edits → approve → redirect
[ ] Reject modal: kotelezo comment → reject → redirect
[ ] Pending review banner a Verification oldalon
[ ] Reviews.tsx backward compat banner + link /documents/:id/verify

FAZIS C — TESZTEK + LEZARAS:

B7.5 — E2E:
[ ] tests/e2e/test_verification_v2.py letezik
[ ] test_verification_full_flow PASS (upload → edit → save → approve)
[ ] test_verification_reject_requires_comment PASS
[ ] Legalabb 2 E2E teszt PASS

B7.6 — Regresszio:
[ ] /regression PASS (1442+ unit, 105+ E2E, 96 promptfoo — 0 uj fail)
[ ] /lint-check PASS (ruff + tsc)

B7.7 — Commit + Plan:
[ ] 2-4 commit (feature-enkent)
[ ] 58 plan B7 row DONE + datum + commit SHA
[ ] CLAUDE.md kulcsszamok frissitese (48 DB tabla, 31 migracio, E2E+, unit+)
[ ] 0 failing teszt a commit-olt kodban
```

---

## BECSULT SCOPE

- **1 uj Alembic migracio** (031_add_verification_edits.py)
- **1 uj Pydantic model fajl** (verification.py vagy bovites)
- **5 uj API endpoint** (CRUD verification edits)
- **1 fo modositott .tsx** (Verification.tsx — 925 → ~1100 sor)
- **3-4 modositott modul fajl** (document-layout.ts, types.ts, use-verification-state.ts, MockDocumentSvg.tsx)
- **1 modositott .tsx** (Reviews.tsx — backward compat banner)
- **~6 uj unit teszt** (test_verification_api.py)
- **~4 uj E2E teszt** (test_verification_v2.py)
- **i18n kulcsok** (hu.json + en.json bovites: ~15 uj kulcs)
- **2 modositott plan fajl** (58 plan + CLAUDE.md)
- **2-4 commit** (backend + frontend + teszt + plan)

**Ez az AIFlow projekt "showcase" felulete.** A Verification Page az, amit az ugyfel ELOSZOR lat, amikor a rendszer mukodeset demo-zzuk: "itt van a szamla → itt latod a kinyert adatokat → itt javitasz → elfogadod → tovabbmegy." Ha ez profi, az egesz rendszer profin nez ki. Ha ez girbegurba, semmi mas nem szamit.

**Becsult hossz:** 1 teljes session (4-5 ora). Legnagyobb idoigeny:
- Backend (Alembic + API + unit): ~1.5 ora
- Frontend (bbox + diff + validation + reviews merge): ~2 ora
- E2E tesztek + regresszio: ~1 ora
- Plan + commit: ~30 perc

---

## SPRINT B UTEMTERV (S31 utan, frissitett)

```
S19: B0      — DONE (4b09aad)
S20: B1.1    — DONE (f6670a1)
S21: B1.2    — DONE (7cec90b)
S22: B2.1    — DONE (51ce1bf)
S23: B2.2    — DONE (62e829b)
S24: B3.1    — DONE (372e08b)
S25: B3.2    — DONE (aecce10)
S26a: B3.E2E — DONE (0b5e542 + f1f0029)
S27a: B3.E2E — DONE (8b10fd6 + 70f505f)
S27b: B3.5   — DONE (4579cd2)
S28: B4.1    — DONE (9eb2769)
S29: B4.2    — DONE (e4f322e)
S30: B5      — DONE (11364cd + a77a912 + 41d3e60 + c7079c6)
S31: B6      — DONE (8261e88) — Portal audit + 4 journey (design-only)
S32: B7      ← KOVETKEZO SESSION — Verification Page v2 (THIS PROMPT)
S33: B8      — UI Journey implementacio (navigacio + Journey 1 + Journey 2 E2E)
S34: B9      — Docker deploy + UI pipeline trigger
S35: B10     — POST-AUDIT + javitasok
S36: B11     — v1.3.0 tag + merge
```

---

## KESZ JELENTES FORMATUM (B7 vege)

```
# S32 — B7 Verification Page v2 DONE

## Kimenet
- alembic/versions/031_add_verification_edits.py: verification_edits tabla
- src/aiflow/api/v1/...py: 5 uj endpoint (save, get, approve, reject, history)
- aiflow-admin/src/pages-new/Verification.tsx: v2 (bbox + diff + validation)
- aiflow-admin/src/verification/: 4 fajl modositva
- aiflow-admin/src/pages-new/Reviews.tsx: backward compat redirect banner
- tests/unit/test_verification_api.py: {X} teszt
- tests/e2e/test_verification_v2.py: {Y} teszt

## Kulcsszamok
- DB tablak: 47 → 48
- Alembic migraciok: 30 → 31
- Unit tesztek: 1442 → {1442+X}
- E2E tesztek: 105 → {105+Y}
- API endpointok: 170 → {170+5}

## Tesztek
- /regression: PASS ({total} teszt, 0 uj fail)
- /lint-check: PASS (ruff + tsc)
- E2E test_verification_v2.py: {Y}/{Y} PASS

## Commit(ok)
{SHA1} feat(sprint-b): B7.1 alembic 031 verification_edits + API endpoints
{SHA2} feat(sprint-b): B7.2 Verification.tsx v2 — bounding box + diff + field validation
{SHA3} test(sprint-b): B7.3 Verification E2E tests
{SHA4} docs(sprint-b): B7 plan update + key numbers

## Kovetkezo session
S33 = B8 — UI Journey implementacio (navigacio + Journey 1 + Journey 2 E2E)
```

---

*Kovetkezo ervenyben: S32 = B7 (Verification Page v2) → S33 = B8 (UI Journey impl.) → S34 = B9 (Docker deploy)*
