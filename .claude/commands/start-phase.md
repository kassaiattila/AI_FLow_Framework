Start a new vertical slice phase — orchestrate the full service development lifecycle.

Arguments: $ARGUMENTS
(Phase: F0, F1, F2, F3, F4, F4a, F4b, F4c, F4d, F5)

> **Ez a LEGFONTOSABB orchestrator command.** Egy teljes vertikalis szeletet indit el:
> Backend → DB → API → curl teszt → Figma design → UI → Playwright E2E → KESZ.
> Nem lepunk a kovetkezo fazisra amig ez TELJESEN KESZ!

## Steps:

### 1. ELOFELTETEL ELLENORZES
```bash
# Elozo fazis KESZ? (git tag letezik?)
git tag -l "v*"

# Szerverek futnak?
curl -s http://localhost:8100/health
cd aiflow-admin && npx tsc --noEmit
```

Ha elozo fazis nincs lezarva (git tag hianyzik) → **STOP**, eloszor azt kell befejezni!

### 2. FAZIS TERV BEOLVASAS
Olvasd el `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 5 — az aktualis fazis teljes feladatlistaját.

### 3. FELADAT LISTA GENERALAS
Keszits checklist-et a fazis MINDEN feladatabol:

**Backend lepesek:**
- [ ] Service implementacio (`src/aiflow/services/{name}/`)
- [ ] Alembic migracio (`alembic/versions/NNN_add_{feature}.py`)
- [ ] `alembic upgrade head` + `downgrade -1` + `upgrade head` — HIBA NELKUL

**API lepesek:**
- [ ] Endpoint implementacio (`src/aiflow/api/v1/`)
- [ ] `curl` teszt — valos adat, `source: "backend"`, NEM 200 OK check, hanem TARTALOM

**UI lepesek (CSAK ha az API KESZ!):**
- [ ] `/ui-journey` — user journey definicio + API audit
- [ ] `/ui-design` — Figma MCP design (PAGE_SPECS.md frissites)
- [ ] `/ui-page` vagy `/ui-component` — React implementacio
- [ ] `cd aiflow-admin && npx tsc --noEmit` — TypeScript HIBA NELKUL

**Teszteles:**
- [ ] Playwright E2E — TELJES FLOW (upload → process → result → verify)
- [ ] Console hiba ellenorzes (`browser_console_messages`)
- [ ] i18n toggle (HU/EN) — MINDEN string valtozik?
- [ ] Dark mode — nem torik el?
- [ ] Backward compat — regi skill CLI tovabbra is mukodik?

**Lezaras:**
- [ ] `/regression` — regresszios tesztek PASS
- [ ] `git tag v{version}` — fazis lezaras
- [ ] Success criteria check — `42_SERVICE_GENERALIZATION_PLAN.md` Section 8

### 4. SORREND (SOHA NE UGORD AT!)
```
Backend → DB migracio → API → curl teszt
    ↓ CSAK ha API MUKODIK
Figma design → UI fejlesztes → TypeScript check
    ↓ CSAK ha UI MUKODIK
Playwright E2E → Console check → i18n → Dark mode
    ↓ CSAK ha MINDEN ATMENT
Backward compat → Regression → Git tag → KESZ
```

### 5. VALOS TESZTELES (SOHA NE MOCK!)
- **Backend:** `curl` hivással valos adatot ad — NEM stub, NEM placeholder
- **UI:** Playwright MCP valos bongeszioben, valos backend-del
- **Integracio:** Regi skill CLI (`python -m skills.{name}`) tovabbra is mukodik
- **Ha BARMELY teszt sikertelen:** STOP → javitas → ujra tesztel → AZTAN tovabb

## FAZIS DEFINICIOK:
| Fazis | Szolgaltatas | Forras Skill | Tag |
|-------|-------------|-------------|-----|
| F0 | Infra (cache, config, rate limit, auth) | — | v0.9.1-infra |
| F1 | Document Extractor | invoice_processor | v0.10.0-document-extractor |
| F2 | Email Connector + Classifier | email_intent_processor | v0.10.1-email-connector |
| F3 | RAG Engine | aszf_rag_chat | v0.11.0-rag-engine |
| F4a | Diagram Generator | process_documentation | v0.12.0-complete-services |
| F4b | Media Processor | cubix_course_capture (STT) | v0.12.0-complete-services |
| F4c | RPA Browser | cubix_course_capture (RPA) | v0.12.0-complete-services |
| F4d | Human Review + Cubix compose | — | v0.12.0-complete-services |
| F5 | Monitoring + Governance + Admin | — | v1.0.0-rc1 |
