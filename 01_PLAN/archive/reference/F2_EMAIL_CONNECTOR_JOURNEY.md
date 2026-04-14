# F2 Email Connector + Classifier — User Journey

> **Fazis:** F2 (Email Connector + Classifier)
> **Services:** `src/aiflow/services/email_connector/`, `src/aiflow/services/classifier/`
> **API:** `src/aiflow/api/v1/emails.py`
> **UI:** `aiflow-admin/src/pages/EmailConnectors.tsx`, `pages/EmailUpload.tsx`, `resources/EmailList.tsx`, `resources/EmailShow.tsx`
> **Tag:** `v0.10.1-email-connector`

---

## Actor

**IT Administrator / Back-office vezeto** — email postafiokok konfiguralasat vegzi, figyeli a beerkezett emailek automatikus osztalyozasat es utvalasztasat. A connectorokat allitja be, teszteli a kapcsolatot, es ellenorzi az osztályozas minosseget. Naponta 1-2 alkalommal nezi at az eredmenyeket.

## Goal

Email postafiokok csatlakoztatasa a rendszerhez (IMAP/O365), beerkezett levelek automatikus letoltese, hibrid (ML + LLM) osztalyozasa es utvalasztasa — konfiguraltol a feldolgozott emailig egyetlen admin feluletrol.

## Preconditions

- FastAPI backend fut (`localhost:8100`), PostgreSQL + Redis Docker-ben
- Alembic migracio lefutott (017 `email_connector_configs` + `email_fetch_history` tablak)
- Classifier service elerheto (keyword + LLM backend)
- Vite frontend fut (`localhost:5174`)
- Email szerver elerheto (IMAP/O365) — valós email fiokkal rendelkezik a teszteleshez

---

## Steps (User Journey)

### 1. Email Connector konfiguracio (Connectors oldal)

**URL:** `/emails` → **Connectors** tab (v1.1 konszolidacio: `/email-connectors` megszunt)
**Felhasznalo:** Megnyitja az "Emails" oldalt es atvalt a "Connectors" tab-ra.

- Latja a meglevo connectorok tablazatat (nev, provider, szerver, postafink, polling, aktiv, utolso lekeres)
- **Uj connector:** "+ Uj connector" gombra kattint
  - Dialog megnyilik: nev, provider (IMAP/O365/Gmail), host, port, SSL, mailbox, credentials, polling intervallum, max email/lekeres
  - **API:** `POST /api/v1/emails/connectors`
  - Dialog bezarod, tablazat frissul

### 2. Kapcsolat tesztelese

**Felhasznalo:** A connector soraban a WiFi ikonra kattint.

- **API:** `POST /api/v1/emails/connectors/{config_id}/test`
- Eredmeny: zold snackbar ("Kapcsolat sikeres") vagy piros ("Kapcsolat sikertelen" + hiba)
- A teszt ellenorzi: IMAP bejelentkezes, mappa letezes, O365 token ervenyes-e

### 3. Email lekeres (Fetch)

**Felhasznalo:** A connector soraban a Play ikonra kattint.

- **API:** `POST /api/v1/emails/fetch` (`{config_id, limit, since_days}`)
- Eredmeny: zold snackbar (`{new_count} uj email, {total_count} osszes, {duration_ms}ms`)
- Hiba eseten: piros snackbar + hibauzenet
- A `last_fetched_at` mezo frissul a connector sorban

### 4. Lekerdezesi elozmeny megtekintese

**Felhasznalo:** A connector soraban a lefelé nyilra kattint → kibomlik a history tabla.

- **API:** `GET /api/v1/emails/connectors/{config_id}/history?limit=10`
- Tablazat: statusz (completed/failed), email szam, uj emailek, idotartam, hiba, idopont
- Statusz szin: zold (completed), piros (failed), sarga (pending/running)

### 5. Connector szerkesztese / torlese

- **Szerkesztes:** Ceruza ikon → Dialog pre-filled adatokkal → Modositas → `PUT /api/v1/emails/connectors/{config_id}`
- **Torles:** Kuka ikon → Megerosito dialog → `DELETE /api/v1/emails/connectors/{config_id}` (cascade: history is torlodik)

### 6. Email feltoltes (Email Upload oldal)

**URL:** `/email-upload`
**Felhasznalo:** Megnyitja a "Email feltoltes" oldalt (manualis email betoltes).

- Drag-and-drop zona: .eml / .msg / .txt fajlok
- **API:** `POST /api/v1/emails/upload` (multipart form)
- Eredmeny: feltoltott fajlok szama + hibak

### 7. Email feldolgozas

**Felhasznalo:** A "Feldolgozas" gombra kattint.

- Fajlonkent: `POST /api/v1/emails/process` (`{file: filename}`)
- 5 lepesu pipeline:
  1. **Email parse** — header + body + csatolmanyok
  2. **ML classify** — sklearn TF-IDF (gyors, <1ms)
  3. **LLM classify** — GPT finomhangolas (pontosabb, ~3s)
  4. **Entity extraction** — NER kinyeres
  5. **Routing** — osztaly + prioritas hozzarendeles
- Eredmeny kartya: statusz, intent chip (confidence %), prioritas, hiba

### 8. Emailek listazasa (Emails oldal)

**URL:** `/emails`
**Felhasznalo:** A sidebar "Emails" menure kattint.

- **API:** `GET /api/v1/emails` (limit, offset, intent filter)
- Tablazat: felado, targy, szandek, konfidencia, prioritas, beerkezett, csatolmanyok szama
- Szurok: kereses (sender, subject), intent filter
- Prioritas szin: critical=piros, high=narancs, medium=kek, low=zold
- Kattintasra: email reszletek oldal

### 9. Email reszletek (Email Detail oldal)

**URL:** `/emails/{email_id}`
**Felhasznalo:** Egy email sorra kattint a listaban.

- **API:** `GET /api/v1/emails/{email_id}`
- Szekciok:
  - **Fejlec:** felado, targy, datum
  - **Torzs:** email body (max 5000 karakter, monospace)
  - **Szandek felismeres:** intent chip + confidence + method (sklearn/llm/hybrid), reasoning
  - **Kinyert entitasok:** entity chipek (tipus: ertek, confidence%)
  - **Prioritas es utvalasztas:** prioritas szint + SLA orak + szabaly, sor + osztaly + email
  - **Csatolmanyok:** fajlnev, MIME, meret, doc tipus, feldolgozo
  - **Feldolgozas:** ido (ms), pipeline verzio

### 10. Osztályozás tesztelese (API)

**Fejleszto / Admin:** Kozvetlenul teszteli az osztályozot.

- **API:** `POST /api/v1/emails/classify`
  - Request: `{text, subject, strategy, schema_name}`
  - Response: `{label, display_name, confidence, method, reasoning, alternatives[]}`
- Strategiak: SKLEARN_FIRST (gyors), LLM_FIRST (pontos), ENSEMBLE (mindketto), SKLEARN_ONLY, LLM_ONLY

---

## API Endpoints (teljes lista — 13 endpoint)

| # | Method | Path | Purpose |
|---|--------|------|---------|
| 1 | GET | `/api/v1/emails` | Email feldolgozasi eredmenyek listazasa |
| 2 | GET | `/api/v1/emails/{email_id}` | Email reszletek |
| 3 | POST | `/api/v1/emails/upload` | Email fajlok feltoltese |
| 4 | POST | `/api/v1/emails/process` | Email feldolgozas |
| 5 | POST | `/api/v1/emails/classify` | Szoveg osztályozas (hibrid ML+LLM) |
| 6 | GET | `/api/v1/emails/connectors` | Connector konfig lista |
| 7 | GET | `/api/v1/emails/connectors/{id}` | Egyedi connector |
| 8 | POST | `/api/v1/emails/connectors` | Uj connector letrehozas |
| 9 | PUT | `/api/v1/emails/connectors/{id}` | Connector modositas |
| 10 | DELETE | `/api/v1/emails/connectors/{id}` | Connector torles |
| 11 | POST | `/api/v1/emails/connectors/{id}/test` | Kapcsolat tesztelese |
| 12 | POST | `/api/v1/emails/fetch` | Email lekeres triggerelese |
| 13 | GET | `/api/v1/emails/connectors/{id}/history` | Lekerdezesi elozmeny |

## UI Pages

| Oldal | Route | Komponens | Fo funkció |
|-------|-------|-----------|------------|
| Email Connectors | `/email-connectors` | `EmailConnectors.tsx` | Connector CRUD + test + fetch + history |
| Email Upload | `/email-upload` | `EmailUpload.tsx` | Email fajl feltoltes + feldolgozas |
| Emails | `/emails` | `EmailList.tsx` | Feldolgozott emailek lista + szures |
| Email Detail | `/emails/{id}` | `EmailShow.tsx` | Reszletes email + intent + routing |

## Success Criteria

1. Connector letrehozas → kapcsolat teszt → sikeres (zold snackbar)
2. Email lekeres → `new_count > 0` eredmeny
3. Lekerdezesi elozmeny mutatja a korabbi fetch-eket (status, count, duration)
4. Email Upload → feldolgozas → intent + prioritas eredmeny latszik
5. Emails lista betoltodik valos backend adattal (`source: "backend"`)
6. Email Detail mutatja: intent, entities, routing, attachments szekciokat
7. Classify API valos eredmenyt ad (NEM demo)
8. HU/EN nyelv valtas MINDEN stringet frissit
9. 0 JavaScript konzol hiba
10. Playwright E2E teszten atment valos backend-del

## Error Scenarios

| Hiba | UI viselkedes |
|------|--------------|
| Connector szerver nem elerheto | Test: piros snackbar + IMAP/O365 hibauzenet |
| Hibas credentials | Test: "Authentication failed" uzenet |
| Fetch sikertelen | Piros snackbar + hiba; history-ban "failed" statusz |
| Email feldolgozas sikertelen | Piros kartya + error uzenet az upload oldalon |
| Email nem talalhato (detail) | "Not found" error |
| Classifier LLM timeout | Fallback sklearn eredmenyre (method: "keywords") |
| Backend offline | Emails lista: fallback demo adatra + "Demo" badge |

---

## Database Tables

- **`email_connector_configs`** — connector konfiguraciok (migration 017)
- **`email_fetch_history`** — lekerdezesi elozmeny (FK → configs, CASCADE)
- **`workflow_runs`** — email feldolgozasi eredmenyek (korabbi migration)

## Service Dependencies

- **EmailConnectorService** (`src/aiflow/services/email_connector/`) — IMAP/O365 kapcsolat
- **ClassifierService** (`src/aiflow/services/classifier/`) — hibrid osztályozas
- **email_intent_processor skill** (`skills/email_intent_processor/`) — teljes feldolgozasi pipeline
- **PostgreSQL** — konfiguracio + elozmeny tarolasa
- **LLM (gpt-4o-mini)** — osztályozas pontositas
