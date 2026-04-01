# F1 Document Extractor — User Journey

> **Fazis:** F1 (Document Extractor)
> **Service:** `src/aiflow/services/document_extractor/`
> **API:** `src/aiflow/api/v1/documents.py`
> **UI:** `aiflow-admin/src/pages/DocumentUpload.tsx`, `resources/DocumentList.tsx`, `resources/DocumentShow.tsx`, `verification/VerificationPanel.tsx`
> **Tag:** `v0.10.0-document-extractor`

---

## Actor

**Konyveloi asszisztens / Back-office operator** — PDF dokumentumokat (szamlak, szerzodeesek, bizonylatok) tolt fel a rendszerbe, ellenorzi es jovahagyja a kinyert adatokat. Napi szinten 10-50 dokumentumot dolgoz fel. Nem technikai felhasznalo, de a szamla mezoket (szallito, vevo, osszegek) jol ismeri.

## Goal

Papir vagy digitalis PDF dokumentumbol strukturalt, ellenorzott adatot kinyerni a rendszerbe — upload-tol a verifikalt adatig egyetlen feluleten, emberi beavatkozassal a bizonytalan mezokon.

## Preconditions

- FastAPI backend fut (`localhost:8100`), PostgreSQL + Redis Docker-ben
- Alembic migraciok lefutottak (015 `document_type_configs` + 016 `invoices` tabla)
- Legalabb 1 document type config letezik (default: `invoice-hu`, 14 mezo)
- Vite frontend fut (`localhost:5174`)

---

## Steps (User Journey)

### 1. Dokumentum feltoltes (Document Upload oldal)

**URL:** `/document-upload`
**Felhasznalo:** Megnyitja a "Document Upload" oldalt a sidebar menubol.

- Drag-and-drop vagy kattintas a dropzone-ra
- 1 vagy tobb PDF fajl kivalasztasa (max 20MB/fajl)
- Upload gomb automatikusan elindul
- **API:** `POST /api/v1/documents/upload` (multipart form, `files[]`)
- **Eredmeny:** Feltoltott fajlok listaja, fajlonkent "pending" statusz

### 2. Dokumentum feldolgozas (Processing)

**Felhasznalo:** A "Feldolgozas" gombra kattint.

- SSE stream indul: `POST /api/v1/documents/process-stream`
- 6 lepesu pipeline fajlonkent:
  1. **PDF parse** — Docling inicializacio + parse
  2. **Classify** — dokumentum tipus es irany felismeres
  3. **Field extraction** — LLM (gpt-4o) header + tetelek kinyeres
  4. **Validation** — osszeg-ellenorzes (netto + AFA = brutto)
  5. **Store** — PostgreSQL mentes (`invoices` + `invoice_line_items` tablak)
  6. **Export** — CSV/JSON/Excel kimenet
- Valos ideju progress: lepesenkent progress bar + elapsed_ms
- Fajlonkent: confidence %, siker/hiba statusz

### 3. Eredmenyek attekintese

**Felhasznalo:** Latja a feldolgozasi eredmenyt fajlonkent.

- Sikeres: zold pipa + confidence szazalek + "Verify" gomb
- Sikertelen: piros X + hibauzenet
- Uj batch inditasa: "Reset" gomb (sessionStorage torlodkik)

### 4. Dokumentumok listazasa (Documents oldal)

**URL:** `/documents`
**Felhasznalo:** A sidebar "Documents" menure kattint.

- **API:** `GET /api/v1/documents` (limit, offset)
- Tablazat: fajlnev, szallito, szamlaszam, datum, penznem, brutto, validacio
- Szurok: kereses (vendor, invoice#), "Mind" vs "Csak feldolgozott"
- Rendezés: datum szerint csokkeno (alapertelmezett)
- Feldolgozatlan dokumentumok: 50% opacity, "Feldolgozatlan" chip
- Gyors muveletek: "Verify" ikon, "Details" ikon

### 5. Dokumentum reszletek (Document Detail oldal)

**URL:** `/documents/{id}/show`
**Felhasznalo:** A "Details" gombra kattint egy sorban.

- **API:** `GET /api/v1/documents/{source_file}` vagy `/by-id/{uuid}`
- 3 oszlopos layout:
  - **Dokumentum fejlec:** szamlaszam, tipus, datumok, penznem, fizetesi mod
  - **Szallito:** nev, cim, adoszam
  - **Vevo:** nev, cim, adoszam
- **Tetelsor tablazat:** sorszam, leiras, mennyiseg, egyseg, egysegar, netto, AFA%, brutto
- **Osszesites:** netto osszesen, AFA osszesen, brutto osszesen (kiemelt)
- **Validacio:** ervenyes/ervenytelen chip, confidence %, parser, hibak listaja
- "Verify" gomb: atnavigal a verifikacios felulettre

### 6. Dokumentum verifikacio (Verification Panel)

**URL:** `/documents/{id}/verify`
**Felhasznalo:** A "Verify" gombra kattint (upload oldalrol, listabol vagy detail oldalrol).

- **API:** `GET /api/v1/documents/by-id/{uuid}` vagy lista + keresses
- **Layout:** 55% / 45% split
  - **Bal oldal (DocumentCanvas):** PDF oldal renderelese (valos kep vagy sablon nezet), kinyert mezo overlay-ek bounding box-okkal, konfidencia szin-kodolas (zold ≥90%, sarga ≥70%, piros <70%)
  - **Jobb oldal (DataPointEditor):** Kategoriankent csoportositott mezok (Szallito, Vevo, Fejlec, Tetelek, Osszesites), mezonkent: nev, ertek, confidence bar, statusz (Auto/Corrected/OK)
- **Interakciok:**
  - Hover: mezo kiemelese mindket oldalon
  - Kattintas: mezo kivalasztasa
  - Dupla kattintas vagy "E" billentyű: szerkesztes mod (inline input)
  - Enter: jovahagyas, Tab: kovetkezo mezo, Esc: megse
  - "Confirm All": minden mezo jovahagyasa egyszerre
  - "Reset": visszaallitas az eredeti kinyert ertekekre
- **Mentes:** "Save" gomb → `POST /api/v1/documents/{invoice_id}/verify`
  - Request: `{ verified_fields: {field: value, ...}, verified_by: "user" }`
  - Backend: `invoices.verified = true`, `verified_fields` JSONB, `verified_at` timestamp
  - Feedback: "Saved" zold chip vagy hiba jelzes
  - Backup: localStorage-ba is ment

### 7. Visszaellenorzes (opcionalis)

**Felhasznalo:** Visszanavigal a Documents listara.

- A verifikalt dokumentum "OK" statuszban jelenik meg
- A verification panel ujra megnyithato — a mentett ertekek lathatoak

---

## API Endpoints (teljes lista)

| # | Method | Path | Purpose | Response |
|---|--------|------|---------|----------|
| 1 | GET | `/api/v1/documents` | Dokumentumok listazasa | `{documents: [...], total, source}` |
| 2 | GET | `/api/v1/documents/by-id/{uuid}` | Egyedi dokumentum UUID alapjan | `{...document fields}` |
| 3 | GET | `/api/v1/documents/{source_file}` | Egyedi dokumentum fajlnev alapjan | `{...document fields}` |
| 4 | POST | `/api/v1/documents/upload` | PDF fajlok feltoltese | `{uploaded: [...], count}` |
| 5 | POST | `/api/v1/documents/process` | Feldolgozas (szinkron) | `{results: [...], source}` |
| 6 | POST | `/api/v1/documents/process-stream` | Feldolgozas SSE stream-mel | SSE events |
| 7 | GET | `/api/v1/documents/images/{file}/page_{n}.png` | PDF oldal rendereles PNG-be | PNG image |
| 8 | POST | `/api/v1/documents/{invoice_id}/verify` | Verifikacio mentes | `{verified, invoice_id, source}` |
| 9 | GET | `/api/v1/documents/extractor/configs` | Extractor config lista | `{configs: [...]}` |
| 10 | POST | `/api/v1/documents/extractor/configs` | Uj extractor config | `{config}` |

## UI Pages

| Oldal | Route | Komponens | Fo funkció |
|-------|-------|-----------|------------|
| Document Upload | `/document-upload` | `DocumentUpload.tsx` | PDF feltoltes + valos ideju feldolgozas |
| Documents | `/documents` | `DocumentList.tsx` | Lista + szures + gyors muveletek |
| Document Detail | `/documents/{id}/show` | `DocumentShow.tsx` | Reszletes nezet (read-only) |
| Verification | `/documents/{id}/verify` | `VerificationPanel.tsx` | Side-by-side verifikacio + mentes |

## Success Criteria

1. PDF feltoltes → feldolgozas → eredmeny latszik az upload oldalon
2. Documents lista betoltodik valos backend adattal (`source: "backend"`)
3. Document Detail megjeleníti az osszes kinyert mezot
4. Verification Panel: mezo kivalasztas, szerkesztes, jovahagyas, mentes mukodik
5. Mentes utan a `verified` flag true a DB-ben
6. HU/EN nyelv valtas MINDEN stringet frissit
7. 0 JavaScript konzol hiba
8. Playwright E2E teszten atment valos backend-del

## Error Scenarios

| Hiba | UI viselkedes |
|------|--------------|
| Backend nem elerheto | "API offline" warning banner |
| Upload sikertelen (HTTP error) | Alert: hibauzenet |
| Feldolgozas sikertelen (1 fajl) | Piros X + hibauzenet a fajl soraban, tobbi fajl folytatodik |
| Dokumentum nem talalhato (verify) | "Document not found: {id}" error alert |
| Save sikertelen | "Error" piros chip a footer-ben |
| PDF rendereles sikertelen (404) | Automatikus fallback sablon nezetre (MockDocumentSvg) |

---

## Database Tables

- **`invoices`** — fo tabla (migration 016): vendor, buyer, header, totals, validation, verification mezok
- **`invoice_line_items`** — tetelsorok (FK → invoices.id CASCADE)
- **`document_type_configs`** — kinyeresi konfiguraciok (migration 015)

## Service Dependencies

- **DocumentExtractorService** (`src/aiflow/services/document_extractor/`)
- **Docling** — PDF parse (lokalis, ingyenes)
- **LLM (gpt-4o)** — mezo kinyeres
- **PostgreSQL** — adat tarolasa
- **pypdfium2** — PDF → PNG rendereles
