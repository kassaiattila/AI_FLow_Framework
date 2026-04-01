Define and validate a complete user journey with required API endpoints.

Arguments: $ARGUMENTS
(e.g., "invoice verification", "email processing", "RAG collection management")

> **GATE 1 a 7 HARD GATE pipeline-bol. Ez MINDIG az ELSO lepes.**
> SEMMILYEN UI munka NEM indulhat el enelkul. Sem /ui-design, sem /ui-page, sem /ui-component.
> A journey definialja: milyen API kell → mi a Figma design → mi a UI implementacio → mi a teszt.
> **OUTPUT ARTEFAKTUM:** Journey dokumentacio a `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`-ben
> VAGY onallo fajl a `01_PLAN/` konyvtarban. Enelkul a kovetkezo gate FAIL.

## Steps:

### 1. USER JOURNEY DEFINICIO
Kerdezd meg (vagy argumentumbol):
1. Ki a felhasznalo? (admin, operator, viewer)
2. Mi a celja? (mit akar elerni a feluleten)
3. Milyen lepesekbol all? (navigacio → input → feldolgozas → eredmeny)

Dokumentald a journey-t igy:
```
Journey: {nev}
Szerep: {felhasznalo tipus}
Cel: {mit akar elerni}

Lepesek:
1. {Oldal} → {Akcio} → {Vart eredmeny}
2. {Oldal} → {Akcio} → {Vart eredmeny}
...

Szukseges oldalak: [oldal lista]
Szukseges API-k: [endpoint lista]
```

### 2. API ENDPOINT AUDIT
Minden lepeshez ellenorizd:
1. **Letezik-e mar az API?** — Grep `src/aiflow/api/v1/` az endpoint-ert
2. **Van-e DB tabla?** — Grep `alembic/versions/` a tabliert
3. **Van-e ORM model?** — Grep `src/aiflow/state/` a model-ert

Jelold:
- ✅ Letezik es mukodik
- ⚠️ Letezik de reszleges (pl. csak GET, nincs POST)
- ❌ Hianyzik — implementalni kell a UI ELOTT
- 🧟 Zombie tabla (DB letezik, API nincs)

### 3. FIGMA DESIGN AUDIT
Ellenorizd a Figma-ban:
1. Van-e mar design az oldalhoz? — `aiflow-admin/figma-sync/PAGE_SPECS.md`
2. Van-e component a szukseges elemekhez? — `aiflow-admin/figma-sync/config.ts`
3. Kell-e uj Figma page/component?

### 4. IMPLEMENTATION TERV
Oszefoglald a szukseges munkakat:

| # | Feladat | Tipus | Becsult ido | Fuggeseg |
|---|---------|-------|-------------|----------|
| 1 | API endpoint: GET /api/v1/... | Backend | X ora | - |
| 2 | Figma design: {Page} page | Design | X ora | #1 API kell eloszor |
| 3 | UI implementacio: {Page}.tsx | Frontend | X ora | #2 Design kell eloszor |
| 4 | Playwright E2E teszt | Teszt | X ora | #3 UI kell eloszor |

### 5. OUTPUT
Mentsd el a journey dokumentaciot:
- Ha uj journey: hozzaadni `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 11.2-hoz
- Ha letezo journey modositas: frissiteni a meglevo bejegyzest

## FONTOS SZABALYOK:
- **API-First:** Ha API hianyzik, ELOSZOR backend, AZTAN design, AZTAN UI
- **Figma-First:** Ha API letezik de design nincs, ELOSZOR Figma, AZTAN UI kod
- **Valos teszt:** Journey CSAK AKKOR "KESZ" ha Playwright E2E teszten atment valos backend-del
- **42_ plan reference:** Minden journey a megfelelo fazishoz (F0-F5) tartozik
