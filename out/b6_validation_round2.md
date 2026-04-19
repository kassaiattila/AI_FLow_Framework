# B6 Validacio 2. Kor — 63_UI_USER_JOURNEYS.md

**Datum:** 2026-04-09
**Validator:** plan-validator subagent (Claude Sonnet 4.6)
**Dokumentum:** `01_PLAN/63_UI_USER_JOURNEYS.md` (1049 sor)
**Elozmenyek:** 1. kor: 4 MAJOR + 7 MINOR talalt, 5 javitva, 2 kihagyva

---

## Validacio 2. Kor

### REGRESSION CHECK (1. kor javitasok ellenorzese)

| Fix | Leirt javitas | Sor | Allapot |
|-----|--------------|-----|---------|
| MAJOR 1 | `POST /api/v1/pipelines/run` → `POST /api/v1/pipelines/invoice_finder_v3/run` (§ 4 J1 Lepes 1) | 349 | OK — javitva |
| MAJOR 2 | `POST /api/v1/documents/:id/approve/reject` → `POST /api/v1/reviews/:review_id/approve/reject` (§ 4 J1 Lepes 3) | 369-370 | OK — javitva |
| MAJOR 3 | `POST /api/v1/pipelines/runs/:id/retry` → HIANYZÓ ENDPOINT jeloles (§ 4 J2) | 479 | OK — jelolve |
| MAJOR 4 | `GET /api/v1/rag/chat/stream` → `POST /api/v1/rag/collections/:id/query` (§ 4 J3) | 553 | OK — javitva |
| MINOR 1 | "process_docs" skill nev → "process_documentation" (§ 4 J2 monitoring) | 466 | OK — javitva |
| MINOR 2 | "process_documentation skill" → "diagram_generator service" (§ 4 J4 backend lanc) | 732 | OK — javitva |
| MINOR 3 | § 2 DOKUMENTUM FELDOLGOZAS 5 item URL atfedes dokumentalva labjeggzettel [*] | 166-168 | OK — dokumentalva |
| MINOR 4 | Login (Kat. A) explicit megjegyzes § 6.1 elott | 935 | OK — hozzaadva |
| MINOR 5 | § 6.2 B8 opcionalis → 6 → 8 tetel (Mermaid live edit + Streaming spec) | 961-963 | OK — 8 sor van |

**Regression eredmeny: 9/9 fix ellenorizve — de MAJOR 1 RESZLEGES (lasd alabb)**

---

### UJ HIBA (2. korben talalt)

#### 1. [MAJOR] § 6.1 sor 3: Emails endpoint meg mindig generikus forma — REGRESSION

- **Sor:** 941
- **Jelenlegi szoveg:** `"Scan inditas" gomb → \`POST /pipelines/run\` trigger + SSE progress`
- **Helyes forma:** `POST /api/v1/pipelines/invoice_finder_v3/run` (ahogy § 4 J1 Lepes 1-ben, sor 349)
- **Problema:** A § 4-ben MAJOR 1-kent javitott endpoint a § 6.1 tablajabol kimaradt. A fixlog azt irja "§ 6.1 Runs retry endpoint szoveg konzisztencia javitva" (MINOR 6) — de a Emails sor (6.1 #3) javitasa NEM tortent meg. Ket helyen ellentmondo endpont all fenn.
- **Sulyossag:** MAJOR — ez implementacios hibaforras B8-ban, ha a fejleszto a § 6 tabla alapjan kodol.
- **Javaslat:** `POST /pipelines/run` → `POST /api/v1/pipelines/invoice_finder_v3/run`

#### 2. [MEDIUM] § 6.1 sor 8: Monitoring restart endpoint hianyzik az `/api/v1/` prefix — inkonzisztens

- **Sor:** 946
- **Jelenlegi szoveg:** `Service restart button (\`POST /services/:name/restart\`, admin-only)`
- **Kontrasztban:** § 4 J2 Lepes 3 (sor 480): `POST /api/v1/services/:name/restart`
- **Problema:** A § 6 tablaban az endpoint forma elter a § 4-tol: hianyzik az `/api/v1/` prefix. Nem technikai hiba (a kontextusbol ertelmezheto), de konvencio-tortes — az osszes tobbi endpoint teli urlel van megadva.
- **Javaslat:** `POST /services/:name/restart` → `POST /api/v1/services/:name/restart`

#### 3. [MEDIUM] § 6.2 SpecWriter duplikalt tetel — streaming overlap

- **Sorok:** 957 es 963
- **Problema:** A § 6.2 tablaban SpecWriter ketszer szerepel (#2 es #8). A #2 tartalmazza: "History kereso + recent specs widget + **streaming response**". A #8: "Streaming response (SSE) a `/api/v1/specs/write`-en". A streaming ugyanaz a fejlesztes ketszer van listazva, ket kulonbozo becsleshez (2 ora #2-ben, 2 ora #8-ban). Ez ketto-szamitas kockazata B8-ban.
- **Javaslat:** #2-bol el kell venni a "streaming response" reszt (maradjon: "History kereso + recent specs widget"), a #8 marad streaming-dedikaltan. VAGY egyesitenni a kettot.

#### 4. [LOW] § 4 J3 Lepes 4: `POST /api/v1/feedback` endpont nincs HIANYZÓ jelolessel ellátva

- **Sor:** 562
- **Problema:** A `POST /api/v1/feedback` endpoint hivatkozas nincs sem a § 6 B8 tablakban, sem HIANYZÓ jelolessel ellátva. Ha ez az endpoint nem letezik meg, B8-ban el fogja magat rejteni mint "nem tervezett" teendő.
- **Javaslat:** Ellenorizni, hogy a `/api/v1/feedback` endpoint letezik-e a backendben, es ha nem: HIANYZÓ ENDPOINT jeloles hozzaadasa, es § 6.2-be felvenni.

#### 5. [LOW] § 4 J1 Lepes 4: `POST /api/v1/notifications/send` nincs sehol a B8 tervben

- **Sor:** 375
- **Problema:** Az Invoice journey Step 4 "auto-trigger `POST /api/v1/notifications/send`"-t hivatkozza, de ez az endpoint nincs a HIANYZÓ listaban es nincs a § 6 tablakban. Ha az endpoint nem letezik, a J1 E2E teszt (`invoice_finder_full_flow.spec.ts` sor 1014) sikertelen lesz.
- **Javaslat:** Ellenorizni backend-en, es ha hianyos: § 6.1 tartalmat kiegesziteni.

---

### UJ HIBA OSSZEFOGLALO TABLA

| # | Fajl | Sor | Problema | Sulyossag |
|---|------|-----|---------|-----------|
| 1 | `01_PLAN/63_UI_USER_JOURNEYS.md` | 941 | § 6.1 Emails: `POST /pipelines/run` (generikus) — helyes: `POST /api/v1/pipelines/invoice_finder_v3/run` | MAJOR |
| 2 | `01_PLAN/63_UI_USER_JOURNEYS.md` | 946 | § 6.1 Monitoring: `POST /services/:name/restart` hiányos — helyes: `POST /api/v1/services/:name/restart` | MEDIUM |
| 3 | `01_PLAN/63_UI_USER_JOURNEYS.md` | 957+963 | § 6.2 SpecWriter duplikalt "streaming response" tetel (ketto-szamitas kockazata) | MEDIUM |
| 4 | `01_PLAN/63_UI_USER_JOURNEYS.md` | 562 | `POST /api/v1/feedback` nincs HIANYZÓ jelolessel, nincs § 6 tervben | LOW |
| 5 | `01_PLAN/63_UI_USER_JOURNEYS.md` | 375 | `POST /api/v1/notifications/send` nincs HIANYZÓ jelolessel, nincs § 6 tervben | LOW |

---

### MINOSEG + OLVASOSZEMPONT

**Erthetoseg uj olvasónak: 8.5/10**

A dokumentum nagyon jo strukturajú — 6 fő szekció logikus sorrendben, cross-referencia tabla az oldalak es journey-k kozt (§ 3), es minden journey azonos szerkezetet kovet (Cel → Entry → Lepesek → Backend → Oldalak → Hianyzó funcciók). Egy uj fejleszto meg tud erteni minden journey-t ebbol a dokumentumbol egyedül.

Levont 1.5 pont okai:
- A § 6 migracios tablak tobbszor hasznalik a rovid endpoint formot (prefix nelkul), ami zavart okozhat B8-ban
- A § 4 J2 monitoring "Monitoring oldal" lepes 2c skill listajaban 7 skill van felsorolva, de az invoice_finder kentes: skill (code) vs pipeline template vs service

**Implementálhato B8-ban: 8/10**

- J1 es J2 pontosan specifikalt entry point-okkal, lepesekkel, backend lancokkal
- A 7 HARD GATE explicit sorrend van adva (§ 6.5), Playwright E2E targettel
- A B7 deep dive (Verification page) kulön sessionnek van jelolve (S32) — jo elkülonites
- Levont 2 pont: a § 6 tablak nem teljes endpoint URL-eket hasznalnak (sor 941, 946), es a HIANYZÓ endpoint-ok nem mind vannak listazva (notifications, feedback)

**Wireframe kodalas-keszre elégséges-e: IGEN, reszlegesen**

- § 5.1 Sidebar ASCII wireframe: ELÉG a Sidebar.tsx MENU_GROUPS atirásához — megadja a csoportokat, item-eket, icon neveket, default open/close state-et, es Untitled UI token neveket
- § 5.2 Dashboard ASCII wireframe: ELÉG a Dashboard layout kodalasahoz — megadja a kártya mereteket (360x200px, border-radius 12px), grid layoutot (2x2 desktop / 1x4 mobile), Alert banner specet, KPI row specet
- § 5.3 Figma Frame Registry: TODO B8 — csak a Figma frame-ek listaja van, maguk a frame-ek meg nem leteznek
- NINCS wireframe: Emails "Scan inditas" gomb, Documents confidence badge, Verification B7 (ott a B7 session fogja meghatarozni)

---

### HIANYZÓ ENDPOINT OSSZESZAMLAS

| Endpoint | Szekcio | Jeloles | § 6-ban van? |
|----------|---------|---------|-------------|
| `POST /api/v1/pipelines/:pipeline_id/runs/:run_id/retry` | § 4 J2 Lepes 3 (sor 479), § 6.1 #6 (sor 944) | HIANYZÓ ENDPOINT, B8 Gate 3 | IGEN |
| `POST /api/v1/rag/collections/:id/query` (SSE streaming verzio) | § 4 J3 Lepes 3 (sor 553) | HIANYZÓ ENDPOINT, B8 Gate 3 (opcionalis) | NEM (de opcionalis, OK) |
| `POST /api/v1/notifications/send` | § 4 J1 Lepes 4 (sor 375) | NEM jelolve | NEM |
| `POST /api/v1/feedback` | § 4 J3 Lepes 4 (sor 562) | NEM jelolve | NEM |
| `GET /api/v1/diagrams/types` + `GET /api/v1/specs/types` | § 6.4 #6 (sor 987) | Ajanlott (future-proof) | NEM (de csak ajanlott) |

**Osszes HIANYZÓ jelolt endpoint: 2** (retry + SSE RAG)
**Potencialisan hianyzó, de nem jelolt: 2** (notifications/send, feedback)

---

### Verdict: NEEDS FIX

**1 MAJOR** probléma (§ 6.1 Emails endpoint regression) javitandó mielőtt B8 implementáció indul.
**2 MEDIUM** problema (§ 6.1 Monitoring prefix, § 6.2 SpecWriter duplikáció) erősen ajánlott javítani.
**2 LOW** problema (notifications + feedback endpoint B8 tervből hiányoznak) opcionalisan vizsgálandó.

A dokumentum összességeben alkalmas B8 tervezési alapnak, de a MAJOR javítás kötelező.

---

*Validator: plan-validator subagent | 2026-04-09 | Kor: 2/2*
