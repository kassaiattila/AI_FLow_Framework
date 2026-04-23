# Live E2E: Emails module

> **Modul:** `aiflow-admin/src/pages-new/Emails.tsx`
> **API:** `src/aiflow/api/v1/emails.py`
> **Backend skill:** `skills/email_intent_processor/`
> **Verzio:** v1.4.7 Sprint K S108a

## Elofeltetelek

```
curl -sf http://127.0.0.1:8102/health
curl -sf http://127.0.0.1:5173
docker ps | grep 07_ai_flow_framwork-db-1
```

## Journey

### 1. Login

```
navigate → http://localhost:5173/#/login
fill  → email textbox = "admin@aiflow.local"
fill  → jelszo textbox = "AiFlowDev2026"
click → Bejelentkezes button
```

**Expect**
- URL valtozas → `http://localhost:5173/#/`
- Console errors: 0 (warning OK)
- Network: `POST /api/v1/auth/login` → 200

### 2. Navigate to Emails

```
navigate → http://localhost:5173/#/emails
```

**Expect**
- Heading "Emailek" lathato
- 4 KPI kartya: Emailek / Szandek felismeres / Unprocessed / Csatolmanyok
- Process All gomb ENABLED ha `unprocessed > 0`
- Table: legalabb 1 sor, "Felado / Targy / Szandek / Prioritas / % / Beerkezett" oszlopok
- Console errors: 0
- Network: `GET /api/v1/emails` → 200

### 3. Cost preview modal (Process All)

```
click → Process All (N) button
```

**Expect**
- Dialog megjelenik: `"N email feldolgozasa"` cimmel
- "Becsult koltseg" + "Becsult ido" grid lathato
- Cost string tartalmaz `$` jelet
- ETA string tartalmaz `h` vagy `m` vagy `s`
- 2 gomb: **Megse** (left) + **Inditas** (right)

**Action**
```
click → Megse button
```

**Expect**
- Dialog eltunik
- Process All gomb visszaall alap allapotba

### 4. Single email process

```
scroll table → talalj egy "Not processed" sort a 3. oldalakon bellul
click → Process button a soron
```

**Expect**
- Process gomb disabled lesz (grayed)
- "Pipeline lepesek" progress panel megjelenik (<3s)
- Panel felirata: `"0/1 kesz · ETA ~<1m"` vagy hasonlo
- Panel alatt 1 sor 5 step-pel: Parse / Classify / Extract / priority / route

**Wait** (max 120s)
- Network: `POST /api/v1/emails/process-batch-stream` → 200 SSE
- Network figyelese: `streaming response`, kb. 60-90s teljes ido

**Expect befejezese utan**
- Progress panel: `"1/1 kesz"`, minden step zold check
- KPI "Szandek felismeres" eggyel nagyobb, "Unprocessed" eggyel kisebb
- A feldolgozott sor a lista tetejen: intent (Marketing / Belso / Informacio / etc), confidence %
- Console errors: 0

### 5. Cancel mid-processing

```
click → Process All (N) button
click → Inditas button (modal-ban)
wait → 3 masodperc (hogy egy-ket email elinduljon)
click → Megszakitas button (progress panel header jobb oldal)
```

**Expect**
- Megszakitas utan:
  - Progress panel: `"X/N kesz · Y hiba"` formatum
  - Pending sorok "Megszakitva" error statusszal
  - Process All gomb ismet ENABLED
  - Network: folyo SSE kapcsolat lezart

### 6. CSV Export

```
click → CSV Export button
```

**Expect**
- Letoltott fajl: `aiflow_emails.csv` vagy hasonlo
- Content-Type: `text/csv`

### 7. Connectors tab

```
click → Connectorok tab
```

**Expect**
- Lista / `Nincs adat` uzenet
- Console errors: 0
- Network: `GET /api/v1/emails/connectors/` → 200

### 8. Upload tab

```
click → Upload tab
```

**Expect**
- Drop zone / "Emailek feltoltese" UI
- Console errors: 0

## Sikerkriteriumok (PASS)

Minden lepes utan:
- [ ] 0 console error
- [ ] 0 network 5xx (kiveve ha teszteljuk)
- [ ] Elvart UI elemek jelen

Vegallapot:
- [ ] Uj email feldolgozva (4. lepes utan)
- [ ] Megszakitas mukodik (5. lepes utan)

## Utolso futtatas

<!-- Ide jon az utolso futtatas riport-ja `/live-test emails` utan. Elhagyhato commit-bol a `.gitignore` szerint ha a user nem akarja verziozni. -->

### 2026-04-23 06:04 — **PARTIAL (CORS fix eligazito)**
- Lepes 1-2: PASS (login + /emails betoltes, 0 error a 1e8c15d fix utan)
- Lepes 3: PASS (cost modal ~$0.13 / ~2h 48m, Megse zar)
- Lepes 4: PASS (1 email, intent=marketing, 60s, DB commit OK)
- Lepes 5: PASS (Megszakitas 168 hiba, Process All re-enabled)
- Lepes 6-8: nem futtatva
- **Findings (usability):**
  - ETA kezdetben `~2h 48m`-et mutat, de nincs dinamikus frissites amig 0 a done
  - Connectors tab sajat 307→CORS kockazat potencial (jovobeli teszt)
  - Nincs "retry failed" gomb a 168 hiba utan
- **Commits tett:** `1680188` (api-client clone), `e75a42d` (S108a baseline), `1e8c15d` (services slash)
