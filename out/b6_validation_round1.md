# Validacio 1. Kor — `01_PLAN/63_UI_USER_JOURNEYS.md`

> Validator: plan-validator subagent | Branch: feature/v1.3.0-service-excellence | Date: 2026-04-09
> Document lines: 1027 | Checks: A-F (6 dimenzio)

---

## (A) NUMBERS CONSISTENCY

### PASS
- § 1 audit tabla: pontosan 23 sor (sorok 60-82, #1 Login ... #23 Audit). Szamlalt: 23. HELYES.
- Kategoria osszeg: A=1 + B=15 + C=7 = 23. HELYES (sor 87-90).
- Journey eloszlas: 1+5+5+2+3+3+1+3 = 23. HELYES (sor 92-101).
- § 3 kereszt-referencia tabla: 23 sor (sorok 282-305, #1 Login ... #23 Audit). Szamlalt: 23. HELYES.

### FAIL / WARNING
1. [MINOR] § 2 IA "DOKUMENTUM FELDOLGOZAS" csoport 5 menu itemet sorol fel, de ezek kozul tobb UGYANARRA a route-ra mutat (`/documents` ketsz er: "Dokumentum Upload" es "Mentett Dokumentumok" mindketto `/documents`). Ez nem hiba a szamolasban, de redundanciara utal — 5 item != 5 kulonbozo oldal. Javaslat: Megjegyezni, hogy a 23 oldal 20 menu itemre van levetitve (tobb item ugyanazt az oldalt tabokon keresztul eri el), hogy az olvasok ne kerik szamon 5+2+3+5+4+2=21 menu item vs 23 oldal ellentmondasat.

2. [MINOR] § 6 migracios tabelak fedezete: B8 kotelezo (10 sor) + B8 opcionalis (6 sor) + Sprint C (6 sor) = 22 sor. A 23 oldalbol a Login (#1, Kategoria A) nem szerepel egyik B8 tablaban sem — ez HELYES (Login mukodik E2E, nincs tennivalaja), de nem expliciten van dokumentalva, hogy "Login: kihagyjuk mert A kategoria". Javaslat: 6.1 tablaban egy mondat: "Login (#1, Kat. A) — nem szerepel, mukodik E2E".

---

## (B) REFERENCES VALIDITY

### PASS
- **TSX fajlok — 23/23 letezik.** Az alabbi route ↔ fajl parak mind ellenorzottek (glob: `aiflow-admin/src/pages-new/*.tsx`):
  - `/login` → `Login.tsx` OK
  - `/` → `Dashboard.tsx` OK
  - `/runs` → `Runs.tsx` OK
  - `/costs` → `Costs.tsx` OK
  - `/monitoring` → `Monitoring.tsx` OK
  - `/quality` → `Quality.tsx` OK
  - `/documents` → `Documents.tsx` OK
  - `/documents/:id/show` → `DocumentDetail.tsx` OK
  - `/documents/:id/verify` → `Verification.tsx` OK
  - `/emails` → `Emails.tsx` OK
  - `/rag` → `Rag.tsx` OK
  - `/rag/:id` → `RagDetail.tsx` OK
  - `/process-docs` → `ProcessDocs.tsx` OK
  - `/spec-writer` → `SpecWriter.tsx` OK
  - `/media` → `Media.tsx` OK
  - `/rpa` → `Rpa.tsx` OK
  - `/reviews` → `Reviews.tsx` OK
  - `/cubix` → `Cubix.tsx` OK
  - `/services` → `Services.tsx` OK
  - `/pipelines` → `Pipelines.tsx` OK
  - `/pipelines/:id` → `PipelineDetail.tsx` OK
  - `/admin` → `Admin.tsx` OK
  - `/audit` → `Audit.tsx` OK

- **Pipeline templates — leteznek a hivatkozott fajlok:**
  - `invoice_finder_v3.yaml` → letezik (`src/aiflow/pipeline/builtin_templates/invoice_finder_v3.yaml`) OK
  - `advanced_rag_ingest.yaml` → letezik OK
  - `knowledge_base_update.yaml` → letezik OK
  - `diagram_generator_v1.yaml` → letezik OK
  - `spec_writer_v1.yaml` → letezik OK

- **API endpoint-ok — ellenorzottek:**
  - `POST /api/v1/specs/write` → `spec_writer.py` sor 124 OK
  - `POST /api/v1/process-docs/generate` → `process_docs.py` sor 46 OK
  - `POST /api/v1/process-docs/generate-stream` → `process_docs.py` sor 187 OK
  - `GET /api/v1/runs` → `runs.py` sor 53 OK
  - `GET /api/v1/runs/stats` → `runs.py` sor 179 OK
  - `POST /api/v1/notifications/send` → `notifications.py` sor 130 OK
  - `POST /api/v1/feedback` → `feedback.py` sor 52 OK
  - `POST /api/v1/reviews/:id/approve` → `human_review.py` sor 107 OK
  - `POST /api/v1/reviews/:id/reject` → `human_review.py` sor 116 OK
  - `POST /api/v1/pipelines/:id/run` → `pipelines.py` sor 450 OK
  - `POST /api/v1/services/manager/:name/restart` → `services.py` sor 333 OK
  - `GET /api/v1/diagrams/:id/export` → `diagram_generator.py` sor 105 OK
  - `GET /api/v1/specs/:id/export` → `spec_writer.py` sor 261 OK

- **Services — leteznek a hivatkozott services:**
  - `rag_engine` → `src/aiflow/services/rag_engine/` OK
  - `advanced_chunker` → `src/aiflow/services/advanced_chunker/` OK
  - `vector_ops` → `src/aiflow/services/vector_ops/` OK
  - `reranker` → `src/aiflow/services/reranker/` OK
  - `diagram_generator` → `src/aiflow/services/diagram_generator/` OK
  - `document_extractor` → `src/aiflow/services/document_extractor/` OK
  - `human_review` → `src/aiflow/services/human_review/` OK
  - `notification` → `src/aiflow/services/notification/` OK
  - `health_monitor` → `src/aiflow/services/health_monitor/` OK
  - `media_processor` → `src/aiflow/services/media_processor/` OK
  - `email_connector` → `src/aiflow/services/email_connector/` OK

### FAIL / WARNING
1. [MAJOR] § 4 Journey 1, Lepes 1 (sor 345): "Scan inditas gomb → `POST /api/v1/pipelines/run`" — ez az endpoint NEM LETEZIK ilyen formaban. A leteza endpoint: `POST /api/v1/pipelines/{pipeline_id}/run` (pipeline_id parametert igenyel). A dokumentum generic `/pipelines/run`-ra hivatkozik, de ez nem leteza endpoint — a helyes forma pipeline_id-t igenyel. Javaslat: Javitani `POST /api/v1/pipelines/{pipeline_id}/run` formara (pl. `invoice_finder_v3` az ID), es megjegyezni, hogy a pipeline_id a YAML template nevebol jo.

2. [MAJOR] § 4 Journey 2, Lepes 3 (sor 475): "`POST /api/v1/pipelines/runs/:id/retry`" — ez az endpoint NEM LETEZIK a codebase-ben. A `runs.py` fajlban (sor 53-231) nincs retry endpoint. A `pipelines.py` fajlban sincs `/runs/:id/retry`. Ez egy B8-ban implementalando endpoint, de a dokumentum ugy hivatkozik ra, mintha letezne. Javaslat: Jelolni explicit "HIANYZO ENDPOINT — B8-ban implementalando" szoveggel, es felvenni a B8 Gate 3 (API Impl) listajaba.

3. [MAJOR] § 4 Journey 3, Lepes 3 (sor 549): "`SSE streaming: /api/v1/rag/chat/stream`" — ez az endpoint NEM LETEZIK. Az `rag_engine.py` tartalmaz ingest-stream-et, de RAG chat stream endpointot nem. A meglevo RAG query endpoint: `POST /api/v1/rag/collections/:id/query` (sor 612). Javaslat: Javitani a hivatkozott endpoint-ot a leteza `/rag/collections/:id/query`-re, es jelolni, hogy a streaming valiant B8/Sprint C munka.

4. [MINOR] § 4 Journey 1, Lepes 3 (sor 365-367): A verifikacios "Elfogadas" / "Elutasitas" akciokhoz a dokumentum `POST /api/v1/documents/:id/approve` es `POST /api/v1/documents/:id/reject` endpointokat hivatkozik. Ezek NEM LETEZNEK a `documents.py`-ban. Az approve/reject logika a `human_review.py`-ban van (`POST /api/v1/reviews/:id/approve`). A dokumentum a verifikalasi workflow-t teves endpoint-ra iranyitja. Javaslat: Javitani "Elfogadas" → `POST /api/v1/reviews/:id/approve` (review_id-val, nem document_id-val), es megjegyezni, hogy a document ↔ review ID mapping B7-ben tisztazando.

5. [MINOR] § 2 IA monitoring csoport (sor 462): A service health kartyaban felsorolt skilleknel (sor 462): `process_docs, aszf_rag, email_intent, invoice_processor, invoice_finder, cubix, spec_writer` — 7 skill van felsorolva. A CLAUDE.md (root es 01_PLAN) szerint 7 skill letezik (spec_writer B5.2-ben jott), de a kartyaban "process_docs" neven szerepel, mig a valodi skill neve `process_documentation`. Ez egy naming inkonzisztencia, de minor (UI label, nem endpoint).

---

## (C) JOURNEY CONSISTENCY

### PASS
- § 4 Journey 1 (Invoice) lapjai: `/emails`, `/documents`, `/documents/:id/verify`, `/documents` — mind megjelenik "DOKUMENTUM FELDOLGOZAS" csoport alatt § 2-ben. Konzisztens.
- § 4 Journey 2 (Monitoring) lapjai: `/`, `/runs`, `/costs`, `/monitoring`, `/quality`, `/audit` — mind "MONITORING" csoport alatt § 2-ben. Konzisztens.
- § 4 Journey 3 (RAG) lapjai: `/rag`, `/rag/:id` — mind "TUDASBAZIS" csoport alatt § 2-ben. Konzisztens.
- § 4 Journey 4 (Generation) lapjai: `/process-docs`, `/spec-writer`, `/media` — mind "GENERALAS" csoport alatt § 2-ben. Konzisztens.
- § 4 "hianyzo funkciok" listak es § 6 B8 kotelezo tabla: a legfontosabb tetelek (dashboard journey kartya, email scan trigger, confidence badge, verification bounding box) mindket helyen megjelennek. Alapveto konzisztencia OK.
- Minden journey step valodi backend service-t hasznal (rag_engine, advanced_chunker, vector_ops, reranker, notification, health_monitor, media_processor mind letezik).

### FAIL / WARNING
1. [MINOR] § 4 Journey 2 "Oldalak a user szemszogebol" (sor 495-499): 6 oldalt sorol fel (/, /runs, /costs, /monitoring, /quality, /audit), de a § 1 audit tablaban az Audit oldal (sor 82) es a § 3 kereszt-referencia tablaban az Audit-nak journey = "2-Monitoring" van megjelolve. Ez konzisztens. Azonban § 6.3 Sprint C halasztott tablaban az Audit NEM szerepel — helyes, mert Audit a J2 Monitoring reszekent B8 kotelezo. De az Audit (#23) a § 1 tablaban "C" kategoriat kapott (backend stub) es "2-Monitoring" journey-t. A § 6.1 B8 kotelezo tablahoz (#10, Audit) az export CSV + date range meg van hatarozva. Konzisztens.

2. [MINOR] § 4 Journey 4 "Hianyzo funkciok" listaja 9 tetelek tartalmaz (sor 746-754), § 6.2 B8 opcionalis tablaja 6 sort tartalmaz. A § 4 ProcessDocs diagram_type dropdown es § 6.2 #1 megegyeznek. A § 4 SpecWriter history kereso es § 6.2 #2 megegyeznek. A § 4 Media provider selection es § 6.2 #3 megegyeznek. Azonban a § 4-ben levo "Mermaid live edit" es "Streaming response spec_writer-en" nem jelenik meg § 6.2-ben. Javaslat: B8 opcionalis tablat kiboviteni 2 sorral (sor 950-957 utan), vagy jelolni, hogy ezek "Sprint C" tetelek.

---

## (D) B5.1 + B5.2 INTEGRATION

### PASS
- Journey 4 (sor 619-622): mindharom diagram tipus expliciten emlitett: `flowchart`, `sequence`, `bpmn_swimlane`. HELYES.
- Journey 4 (sor 627-631): mindnegy spec tipus expliciten emlitett: `feature`, `api`, `db`, `user_story`. HELYES.
- § 1 audit tabla #14 (sor 73): SpecWriter `Route: /spec-writer` a 14. sorban szerepel. HELYES.
- `diagram_generator_v1.yaml` (sor 736) → letezik a builtin_templates-ben. HELYES.
- `spec_writer_v1.yaml` (sor 737) → letezik a builtin_templates-ben. HELYES.
- § 6.2 B8 opcionalis #1 (sor 950): "ProcessDocs diagram_type dropdown — NAGY IMPACT 30 perc" expliciten kiemeli a B5.1 gyorsnyereseg-et. HELYES.
- § 1 #13 (sor 72): "UI diagram_type selector CSAK BPMN-re hardcoded — a B5.1 3 tipus nem valaszthato frontend-rol" — explicit dokumentalva. HELYES.
- § 1 #14 (sor 73): SpecWriter "nincs a Sidebar.tsx menüben" B5.2 utan — explicit dokumentalva es a § 2 IA + § 6.2 #6 kezeli. HELYES.

### FAIL / WARNING
1. [MINOR] Journey 4 backend lanc (sor 727-732) a diagram generalasnal "process_documentation skill" nevere hivatkozik (sor 649), mig a valodi service neve `diagram_generator` (a `src/aiflow/services/diagram_generator/` mappaban) es a pipeline `diagram_generator_v1.yaml`. A "process_documentation" a regi skill neve. Javaslat: Javitani "flowchart → process_documentation skill (default)" szoreget "flowchart → diagram_generator service (process_documentation prompts)" formara.

---

## (E) MISSING SECTION DETECTION

### PASS
- § 1 jelen van: 23-soros audit tabla + osszegzes. Nem trivialis tartalom. OK.
- § 2 jelen van: 5-csoportos regi nav → 6 uj csoport + mozgatasi tabla. OK.
- § 3 jelen van: ASCII journey terkep + 23-soros kereszt-referencia tabla. OK.
- § 4 jelen van: 4 reszletes journey definicio (J1 Invoice + J2 Monitoring + J3 RAG + J4 Generation). OK.
- § 5 jelen van: ASCII sidebar wireframe (§5.1) + Dashboard wireframe (§5.2) + Figma Frame Registry (§5.3). OK.
- § 6 jelen van: B8 kotelezo (§6.1) + B8 opcionalis (§6.2) + Sprint C halasztott (§6.3) + anti-pattern-ek (§6.4) + HARD GATE sorrend (§6.5) + Playwright coverage (§6.6). OK.
- Wireframe szekcio: mindket (sidebar + dashboard) ASCII wireframe-t tartalmaz, reszletes specifikaciokal (meret, szin, tipografia, mobile). Figma Frame Registry 5 bejegyzessel. OK.
- Dokumentum sorok: 1027 sor. 600 sor felett. OK.
- Validacios komment blokkok (sor 1015-1021): mind a ket blokk jelen van ("B6 VALIDATION ROUND 1 FIXES" + "B6 VALIDATION ROUND 2 FIXES"). OK.

### FAIL / WARNING
Nincs. Minden szekcio teljesiti az E kritikumot.

---

## (F) FIGMA + PAGE_SPECS SYNC

### PASS
- § 5.3 Figma Frame Registry jelen van (sor 904-912): 5 bejegyzessel (Sidebar light, Sidebar dark, Dashboard desktop, Dashboard mobile, Breadcrumb component). 3 bejegyzes minimum teljesul (5 van). OK.
- Figma MCP elerheto megjegyzes (sor 760): "a mcp__figma__* tool-csomag elerheto, de uj Figma file / frame letrehozasahoz fileKey kell" — expliciten dokumentalva. OK.
- PAGE_SPECS.md commitment: a dokumentum NEM vallal PAGE_SPECS.md irast ebben a sessionben — "CSAK ez a dokumentum + PAGE_SPECS.md journey mapping" szerepel a scope-ban (sor 29), de a § 5.3 szekcio egyertelmuen B8-ra halasztja a Figma frame-ek letrehozasat: "A Figma frame-ek letrehozasa B8 Step 4 (Figma design) lesz — ez a B6 wireframe csak a specifikacio." OK.
- § 6.5 GATE 1 (sor 986): "63_UI_USER_JOURNEYS.md (EZ A DOKUMENTUM) ← KESZ" + PAGE_SPECS.md B8-ra halasztva. OK.

### FAIL / WARNING
1. [MINOR] § 5.3 Figma Frame Registry mind az 5 bejegyzes "TODO B8" statuszu. Ez onmagan helyes (design-only session), de a session prompt azt irja, hogy "Note about Figma MCP availability (the session prompt mentioned it's available but fileKey needed)" — ez az informacio jelen van a § 5 bevezeto szovegeben (sor 760), de nem kozvetlenul a Figma Frame Registry tablaban. Javaslat: A § 5.3 tablaba felvenni egy "Megjegyzes" oszlopot, amelyik a `feedback_figma_quality.md` memoria-bejegyzessel hivatkozva jelzi, hogy placeholder wireframe-ek TILOSAK, valodi Untitled UI komponensek kellenek.

---

## Osszesített Eredmény

### PASS tételek száma: 28
### FAIL / WARNING tételek száma: 11 (0 CRITICAL, 4 MAJOR, 7 MINOR)
### MISSING tételek száma: 0

---

### Issue összefoglaló (prioritás szerint)

| # | Dimenzio | Sulyossag | Problema | Javaslat |
|---|----------|-----------|---------|----------|
| 1 | B | MAJOR | `POST /api/v1/pipelines/run` nem letezik — helyes: `POST /api/v1/pipelines/{pipeline_id}/run` | Javitani az endpoint path-t J1 Lepes 1-ben |
| 2 | B | MAJOR | `POST /api/v1/pipelines/runs/:id/retry` nem letezik a codebase-ben | Jelolni "HIANYZO ENDPOINT — B8 Gate 3" szoveggel |
| 3 | B | MAJOR | `GET /api/v1/rag/chat/stream` nem letezik — valodi endpoint: `/rag/collections/:id/query` | Javitani a streaming endpoint hivatkozast J3 Lepes 3-ban |
| 4 | B | MAJOR | `POST /api/v1/documents/:id/approve|reject` nem letezik — helyes: `POST /api/v1/reviews/:id/approve|reject` | Javitani a verifikacas workflow endpoint-jait J1 Lepes 3-ban |
| 5 | D | MINOR | "process_documentation skill" nev teves — a valodi nev `diagram_generator` | Javitani a backend lanc leirast J4-ben |
| 6 | B | MINOR | `process_docs` skill nev a Monitoring health kartyaban — helyes: `process_documentation` | Javitani sor 462 skill-lista nevet |
| 7 | C | MINOR | J4 "Hianyzo funkciok" 2 tetelje (Mermaid live edit, streaming spec) nincs § 6.2-ben | Felvenni § 6.2-be vagy explicit jelolni Sprint C-kent |
| 8 | A | MINOR | § 2 DOKUMENTUM FELDOLGOZAS csoport 5 item != 5 kulonbozo oldal (URL atmlefedes) | Labjegyzettel dokumentalni az URL atilapadas szandekat |
| 9 | A | MINOR | Login (#1, Kat. A) hianyzik a § 6 migracios tabellakbol (nem szerepel sehol) | Rovid megjegyzes: "Login Kat. A — nincs B8 tennivaloja" |
| 10 | C | MINOR | J2 "hianyzo funkciok" listajanak 2 tetelje (retry button, monitoring restart) nem egyezik meg pontosan § 6.1 tabla megfogalmazasaval | Minor szovegezesi konzisztencia fix |
| 11 | F | MINOR | § 5.3 Figma Frame Registry tablaban hianyzik a "no placeholder" megjegyzes | Kiegesziteni `feedback_figma_quality.md` hivatkozassal |

---

### Osszpontszam: 28 PASS / 11 FAIL-WARNING / 0 MISSING

### Verdikt: **NEEDS FIX** (4 MAJOR issue miatt — mind javithato < 30 percen belul)

---

> A MAJOR issue-k mind endpoint-hivatkozasi hibak (nem leteza path-ok). Ezek javitasa utan a dokumentum 2. korra alkalmas.
> Kovetkezo: LEPES 8 = javitasok beepitese a 63_UI_USER_JOURNEYS.md-be, majd VALIDACIO 2. KOR.
