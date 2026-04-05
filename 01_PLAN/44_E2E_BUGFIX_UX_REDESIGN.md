# AIFlow v1.1.1 — E2E Bug Fix + UX Redesign + Konfigurálható Mezők

## Kontextus

A v1.1.0 UI migracio es az elso E2E teszteles utan 8 kategorianyi problema maradt:
1. Verification PDF kep NEM jelenik meg (mock SVG marad)
2. CSV export auth hiany miatt ures
3. Verification prev/next lepteto lassu/torott (race condition)
4. RAG ingest nem mutat dokumentum metaadatot
5. Adat perzisztencia nem megbizhato (temp dir, relativ utak)
6. RAG Chat UI szuk, gorgetese nem profi
7. Dokumentum tipusok hardcode-olva "szamla"-ra
8. Konfiguralható mezok hianyoznak

**Referenciak:**
- `01_PLAN/F1_DOCUMENT_EXTRACTOR_JOURNEY.md` — Document pipeline user journey
- `01_PLAN/F3_RAG_ENGINE_JOURNEY.md` — RAG pipeline user journey
- `01_PLAN/43_UI_RATIONALIZATION_PLAN.md` — UI migracio terv

---

## FAZIS 1: Verification PDF kep + Navigacio (KRITIKUS)

### 1.1 PDF kep URL javitas
**Fajlok:**
- `aiflow-admin/src/pages-new/Verification.tsx:120-137` (image URL)
- `src/aiflow/api/v1/documents.py:397-436` (image endpoint)

**Gyokerok:**
- `sourceFile` a DB-bol `data\uploads\invoices\file.pdf` formaban jon, de az image endpoint csak a fajlnevet varja
- UTF-8 karakter (ekezetetek) URL encoding/decoding issue Windows-on
- `encodeURIComponent` a backslash-t `%5C`-re kodolva kuldi

**Javitas:**
- Frontend: `sourceFile`-bol kinyerni CSAK a fajlnevet: `sourceFile.split(/[/\\]/).pop()`
- Backend: normalizalni a path-ot, tobb varianciat probalni, Path().name hasznalata
- Fallback: ha a real kep nem toltodik, vizualis cimke legyen a mock-on "Minta dokumentum"

### 1.2 Prev/Next navigacio refaktor
**Fajl:** `Verification.tsx:630-683`

**Gyokerok:**
- Minden `id` valtozaskor teljes `/api/v1/documents` listat tolt ujra (~29+ doc)
- `docIds.indexOf(id)` = -1 amig a fetch nem fejezodik be → gombok disabled
- Race condition

**Javitas:**
- Kulon `useEffect` a `docIds` listahoz (egyszer, mount-kor)
- Kulon `useEffect` az aktualis doc betoltesehez (`id` valtozaskor)
- `docIds`-t `useRef`-ben tarolni hogy ne trigereljen ujrarenderlest
- Pre-fetch: a kovetkezo/elozo doc adatat elore betolteni

---

## FAZIS 2: Export javitas

### 2.1 Auth-os export letoltes
**Fajl:** `aiflow-admin/src/pages-new/Documents.tsx`

**Problema:** `<a href="/api/v1/documents/export/csv">` nem kuldi a Bearer tokent

**Javitas:**
```typescript
const handleExport = async (format: "csv" | "json") => {
  const res = await fetch(`/api/v1/documents/export/${format}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `aiflow_documents.${format}`;
  a.click();
};
```

### 2.2 Export tartalom bovites
**Fajl:** `src/aiflow/api/v1/documents.py` export endpoint

- CSV: summary (1 sor/doc) + detail (1 sor/tetelsor) valasztasi lehetoseg
- Fejlec sorok ertelmezese egyertelmu (HU es EN oszlopnevekkel)
- Excel export (openpyxl/xlsxwriter) kulon sheet-ekkel: Osszesites, Tetelek

---

## FAZIS 3: RAG Ingest UX

### 3.1 Dokumentum metadata megjelenitese
**Fajl:** `aiflow-admin/src/pages-new/RagDetail.tsx`

**Jelenlegi:** Csak `files_processed: N, chunks_created: M` szamok

**Javitas:**
- Backend (rag_engine.py): IngestResponse-ba hozzaadni `file_details: [{name, size_bytes, chunks, duration_ms}]`
- Frontend: tabl data-t mutatni a fajlnev, meret, chunk szam oszlopokkal
- Sikertelenseg eseten fajlonkent hiba uzenet

### 3.2 Chunks tab metadata fix
**Fajl:** `RagDetail.tsx:274-286`

**Problema:** `item.metadata?.document_name` — de az API root-on kuldi: `item.document_name`

**Javitas:** `item.document_name` hasznalata, plusz `item.created_at` datum oszlop

### 3.3 Dokumentumok tab (uj)
**Fajl:** `RagDetail.tsx` + uj backend endpoint

- Uj tab: "Dokumentumok" — listazza az ingestalt fajlokat
- Backend: `GET /api/v1/rag/collections/{id}/documents` → aggregated from chunks (group by document_name)
- Oszlopok: nev, chunk szam, datum, akcio (torles)

---

## FAZIS 4: RAG Chat UI redesign

### 4.1 Teljes kepernyos layout
**Fajl:** `aiflow-admin/src/components-new/ChatPanel.tsx`

- `h-[500px]` → `h-full` vagy `calc(100vh - topbar - tabs)`
- RagDetail: chat tab eseten KPI kartyak elrejtese, teljes magassag a chat-nek
- Szelelesseg: `max-w-3xl mx-auto` a chat buborekoknak (ne legyenek tul szelesek)

### 4.2 Gorgetesi javitas
- `scrollIntoView({ behavior: "smooth", block: "end" })` — mar megvan
- Felso betoltes: "Tobb uzenet betoltese" gomb (pagination)
- Ures allapot: nagyobb ikon + 3 pelda kerdes gomb

### 4.3 Forras megjelenes
- `<details>` → mindig latszodo "Forrasok" szekció a valasz alatt
- Dokumentum nev kiemelt, score szazalekban
- Kattinthato forras → chunks tab szures

---

## FAZIS 5: Dokumentum tipusok generalizalasa + Konfiguralhato mezok

### 5.1 Terminologia: "Invoice" → "Document"
**Fajlok:** `Documents.tsx`, `locales/hu.json`, `locales/en.json`

- Hardcoded "Invoice #" → `translate("aiflow.documents.invoiceNumber")` (mar letezik)
- "Vendor" → `translate("aiflow.documents.vendor")`
- Tobb helyen hasznalt: "Verify" gomb, oszlop fejlecek, KPI cimkek

### 5.2 Konfiguralhato mezok
**Fajlok:** 
- `src/aiflow/api/v1/documents.py` (extractor configs endpoint mar letezik)
- `aiflow-admin/src/pages-new/Documents.tsx` (uj: config valaszto)

**Jelenlegi backend:** `GET /api/v1/documents/extractor/configs` → configs lista (invoice-hu, stb.)
**Terv:**
- Config valaszto a Documents oldalon (dropdown a fejlecben)
- Config alapjan valtoznak az oszlopnevek es a mezok a verifikacioban
- Uj config letrehozasa: "Uj config" gomb → dialog (nev, mezo lista)
- Backend: `POST /api/v1/documents/extractor/configs` (mar implementalva)
- Frontend: config editor UI (mezo lista + drag-drop sorrend + validacio szabalyok)

**Fazisok:**
1. Config valaszto dropdown (gyors, a meglevo endpoint-ot hasznalja)
2. Config editor dialog (kozep, uj UI komponens)
3. Dinamikus oszlopok a listaban es verifikacioban (komplex, a teljes Documents flow atalakitasa)

---

## FAZIS 6: Adat perzisztencia production szint

### 6.1 RAG dokumentum tarolasa
**Fajl:** `src/aiflow/api/v1/rag_engine.py:225`

**Problema:** `tempfile.mkdtemp()` → OS torolheti

**Javitas:** 
- Upload-ot menteni `./data/uploads/rag/{collection_id}/` konyvtarba
- DB-ben tarolni: `document_uploads` tabla (collection_id, filename, size, upload_at, path)
- Ingest utan: fajl megmarad, torolheto kulon gombbal

### 6.2 Upload utvonal abszolutizalas
**Fajl:** `src/aiflow/api/v1/documents.py:95`

- `./data/uploads/invoices` → `PROJECT_ROOT / "data" / "uploads" / "invoices"`
- `__file__` alapu szamitas vagy env var

### 6.3 Torles funkcionalitas
- Documents: DELETE gomb a listaban + API `DELETE /api/v1/documents/{id}`
- RAG collections: DELETE gomb a collections listaban (API mar letezik)
- RAG documents: DELETE az ingestalt dokumentumokra (uj API)
- Megerosito dialog: "Biztosan torli?"

---

## E2E Teszteles protokoll (MINDEN fazis utan)

### Teszt adatok
- Szamlak: `02_Szamlak/Bejovo/2021/` (20+ PDF)
- RAG docs: `94_Cubix_RAG_AI/allianz-rag-unified/documents/` (6 kategoria, 50+ PDF)

### Teszteles modszertan
Minden fazis utan Playwright MCP-vel:
1. **Login** → admin@bestix.hu / admin
2. **Navigate** → az erintett oldalra
3. **Minden gomb es funkcio tesztelese** — upload, process, verify, export, torles, navigacio
4. **Screenshot** evidencia
5. **Console error check** — 0 error kell
6. **Perzisztencia** — page reload, API restart utan adat megmarad?
7. **i18n** — HU/EN toggle MINDEN szovegre vonatkozzon

### Fazis 1 E2E tesztek
```
1. Navigate /documents/{uuid}/verify
2. ELLENORZES: bal oldalon VALOS PDF kep (nem mock SVG)
3. Prev/Next nyilak → gyors valtas, helyes szamlalo
4. SCREENSHOT + console check
```

### Fazis 2 E2E tesztek
```
1. Navigate /documents → CSV Export gomb
2. Kattintas → fajl letoltes (nem 401)
3. CSV megnyitas → fejlecek + adatsorok ellenorzese
4. SCREENSHOT
```

### Fazis 3 E2E tesztek
```
1. Navigate /rag/{id} → Ingest tab → PDF feltoltes
2. ELLENORZES: fajlnev, meret, chunk szam megjelenik
3. Chunks tab → document_name oszlop latszik
4. Dokumentumok tab → ingestalt fajlok listaja
5. SCREENSHOT
```

### Fazis 4 E2E tesztek
```
1. Navigate /rag/{id} → Chat tab
2. ELLENORZES: teljes magassagu chat area
3. Kerdes → valasz → gorgetik lefele
4. Forrasok szekció latszik, kattinthato
5. SCREENSHOT
```

### Fazis 5 E2E tesztek
```
1. Navigate /documents → oszlopnevek i18n-eltek
2. HU/EN toggle → MINDEN szoveg valt
3. Config valaszto dropdown megjelenik
4. SCREENSHOT
```

### Fazis 6 E2E tesztek
```
1. Upload doc → API restart → doc megmarad
2. RAG ingest → API restart → chunks megmaradnak
3. Delete doc → doc eltűnik listából ÉS DB-ből
4. SCREENSHOT
```

---

## Modositando fajlok osszefoglalas

| Fajl | Fazis | Valtozas |
|------|-------|----------|
| `Verification.tsx` | F1 | PDF URL fix (filename extract) + nav refactor (separate useEffects) |
| `documents.py` (image) | F1 | Path normalizalas, UTF-8 kezeles |
| `Documents.tsx` | F2,F5 | Export auth fix + i18n + config dropdown |
| `documents.py` (export) | F2 | Export tartalom bovites (summary + detail) |
| `RagDetail.tsx` | F3,F4 | Metadata fix + Docs tab + chat height |
| `ChatPanel.tsx` | F4 | Full-height responsive + gorgetesi javitas |
| `rag_engine.py` | F3,F6 | IngestResponse metadata + file persistence |
| `locales/hu.json`, `en.json` | F5 | Document generalas |
| `documents.py` (API) | F6 | DELETE endpoint + absolute paths |

## Vegrehajtasi sorrend

| Sorrend | Fazis | Becslés | Fuggoseg |
|---------|-------|---------|----------|
| 1 | F1: Verification PDF + nav | 45 perc | — |
| 2 | F2: Export auth + tartalom | 30 perc | — |
| 3 | F3: RAG ingest metadata | 45 perc | — |
| 4 | F4: Chat UI redesign | 60 perc | F3 |
| 5 | F5.1: i18n generalas | 20 perc | — |
| 6 | F5.2: Config dropdown | 45 perc | F5.1 |
| 7 | F6: Perzisztencia | 60 perc | F3 |
| **Ossz** | | **~5 ora** | |
