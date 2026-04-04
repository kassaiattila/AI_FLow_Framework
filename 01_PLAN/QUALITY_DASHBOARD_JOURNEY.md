# Quality Dashboard — User Journey (S3)

> **Fazis:** S3 (v1.2.1 Production Ready Sprint)
> **Szolgaltatas:** Quality Service (quality evaluations, rubric scoring, cost tracking)
> **Felhasznalo:** Admin / DevOps — LLM minoseg es koltseg monitorozas

---

## 1. Journey Attekintes

Az admin felhasznalo a Quality Dashboard-on latja az osszes LLM ertekeles eredmenyet,
a rubric-ok allapotat, a napi/havi koltsegeket, es ad-hoc ertekeleseket futtathat.

```
Dashboard → Quality (sidebar) → KPI attekintes → Rubric tabla → Evaluate form → Eredmeny
```

---

## 2. User Journey Lepesek

### 2.1 Navigacio
- **Honnan:** Dashboard vagy barmelyik oldal
- **Hogyan:** Sidebar > Muveletek > Quality
- **Hova:** `/quality` oldal

### 2.2 KPI Attekintes (fo nezet)
Az oldal teteje KPI kartyakat mutat:

| KPI | API mezo | Leiras |
|-----|----------|--------|
| Total Evaluations | `total_evaluations` | Osszes lefutott ertekeles szama |
| Avg Score | `avg_score` | Atlagos minosegi pontszam (0-100%) |
| Pass Rate | `pass_rate` | Sikeres ertekelesek aranya (%) |
| Cost Today | `cost_today` | Mai LLM koltseg ($) |
| Cost This Month | `cost_month` | Havi LLM koltseg ($) |

**API:** `GET /api/v1/quality/overview` → `source: "backend"`

### 2.3 Rubric Lista
A KPI kartyak alatt tabla a beepitett rubric-okkal:

| Oszlop | Tartalom |
|--------|----------|
| Name | Rubric neve (relevance, faithfulness, stb.) |
| Description | Rubric leirasa |

**API:** `GET /api/v1/quality/rubrics` → `source: "backend"`
**Beepitett rubric-ok (6 db):** relevance, faithfulness, completeness, extraction_accuracy, intent_correctness, hungarian_quality

### 2.4 Evaluate Form
Az admin kivalaszt egy rubric-ot, beiras egy LLM outputot, es futtat egy ertekelesst:

- **Input mezok:**
  - Actual output (textarea, kotelezo)
  - Expected output (textarea, opcionalis)
  - Rubric (dropdown, a /rubrics listajbol)
- **Action:** "Evaluate" gomb → `POST /api/v1/quality/evaluate`
- **Eredmeny:** Score (0-100%), Pass/Fail badge, Reasoning szoveg

### 2.5 Cost Estimation (opcionalis)
Pipeline koltseg becsles:
- **Input:** Pipeline steps JSON
- **Action:** `POST /api/v1/quality/estimate-cost`
- **Eredmeny:** Becsult token szam, becsult koltseg ($)

---

## 3. API Endpointok

| Method | Endpoint | Cel | Allapot |
|--------|----------|-----|---------|
| GET | `/api/v1/quality/overview` | KPI osszesites | KESZ (v1.2.0) |
| GET | `/api/v1/quality/rubrics` | Rubric lista | KESZ (v1.2.0) |
| POST | `/api/v1/quality/evaluate` | Ad-hoc ertekeles | KESZ (v1.2.0) |
| POST | `/api/v1/quality/estimate-cost` | Koltseg becsles | KESZ (v1.2.0) |

**Minden endpoint `source: "backend"` mezot ad vissza.**

---

## 4. UI Komponensek

| Komponens | Tipus | Leiras |
|-----------|-------|--------|
| KpiCard | Untitled UI Card | 5 db, KPI ertekekkel |
| DataTable | @tanstack/react-table | Rubric lista (6 sor) |
| Evaluate Form | Textarea + Select + Button | Ad-hoc ertekeles |
| Score Display | Badge + Text | Eredmeny megjelenites |
| StatusBadge | Badge | Pass/Fail jelzes |

---

## 5. Sikerkriteriuok

- [ ] `/quality` oldal betolt, KPI kartyak valos adatot mutatnak
- [ ] Rubric tabla 6 sort mutat (source: backend)
- [ ] Evaluate form → POST → score + pass/fail megjelenik
- [ ] i18n: HU/EN valtogatas mukodik
- [ ] 0 console error
- [ ] tsc --noEmit PASS
