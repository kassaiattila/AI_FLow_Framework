# AIFlow Session Restart Prompt

Masold be ezt a promptot uj Claude Code session indulaskor:

---

## Kontextus

AIFlow Enterprise AI Automation Framework — service generalizacios fazisban vagyunk (vertikalis szeletek).

### Kiindulas
- **Git tag:** `v0.9.0-stable` (rollback pont)
- **Aktualis branch:** `main`
- **Utolso session (2026-04-01):** F0 + F1 + F2 KESZ — pipeline audit + szigoritas keszult
- **F0 tag:** `v0.9.1-infra`
- **F1 tag:** `v0.10.0-document-extractor`
- **F2 tag:** `v0.10.1-email-connector`
- **Kovetkezo feladatok:** E2E audit befejezese + Invoice→Document atnevezes + F3 inditas

### Mi keszult el eddig (F0 + F1 + F2 + audit)
```
src/aiflow/services/
  __init__.py, base.py, registry.py          # F0.1 — BaseService + ServiceRegistry
  cache/                                      # F0.2 — Redis cache
  config/                                     # F0.3 — Config versioning
  rate_limiter/                               # F0.4 — Rate limiter
  resilience/                                 # F0.5 — Retry + circuit breaker
  schema_registry/                            # F0.8 — Schema registry
  document_extractor/                         # F1.1 — Document extraction service
  email_connector/                            # F2.1 — Email connector (IMAP/O365/Gmail)
  classifier/                                 # F2.2 — Hybrid keyword+LLM classifier

alembic/versions/ (001-017)                  # 17 migracio (utolso: 017_email_connector)

src/aiflow/api/v1/emails.py                 # 13 endpoint (connector CRUD, classify, fetch, detail)

aiflow-admin/src/pages/EmailConnectors.tsx   # F2 — Connector config CRUD UI
aiflow-admin/figma-sync/PAGE_SPECS.md        # Page 14: EmailConnectors hozzaadva
```

### PIPELINE AUDIT + SZIGORITAS (2026-04-01)
**FONTOS:** F1 es F2 KIHAGYTA a Journey (Gate 1) es Figma Design (Gate 4) lepeseket!
Emiatt CLAUDE.md es az osszes /ui-* command fajl SZIGORITVA lett:
- **CLAUDE.md:** "DETERMINISTIC UI PIPELINE — 7 HARD GATE" szekció
- **`/start-phase`:** 12 lepesu determinisztikus pipeline, minden lepes GATE-elt
- **`/dev-step`:** Hard gate checks UI munka elott (journey + design letezik-e?)
- **`/ui-design`, `/ui-page`, `/ui-component`:** Artefaktum ellenorzes (PAGE_SPECS.md, journey doc)

### HIANYZIK MEG (E2E audit eredmenye):
| Feladat | Statusz |
|---------|---------|
| Playwright E2E: F1 Document flow (upload → list → detail → verify) | **TODO** |
| Playwright E2E: F2 Email flow (list → detail → upload) | **TODO** |
| **Invoice → Document atnevezes** az UI-ban (generalizacio!) | **TODO** |
| F3 RAG Engine inditas | **Kovetkezo fazis** |

### FONTOS NAMING SZABALY
> A projekt GENERALIZACIOS — az F1 service neve `document_extractor`, NEM `invoice_processor`.
> Az UI-ban MINDENHOL "Document" / "Dokumentum" kell legyen, NEM "Invoice" / "Szamla".
> Amikor F1 UI oldalakat erintesz, nevezd at: InvoiceUpload → DocumentUpload, stb.

### FO TERV: `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`
Olvasd el a terv **Section 5** (Fazisok) es **Section 8** (Sikerkritieriumok) szekciot!

**6 fazis, vertikalis szeletek:**
```
F0: Infra        → v0.9.1-infra              ✅ KESZ
F1: Doc Extractor → v0.10.0-document-extractor ✅ KESZ (UI: Invoice→Document atnevezes TODO)
F2: Email+Classifier → v0.10.1-email-connector ✅ KESZ
F3: RAG Engine   → v0.11.0-rag-engine         ← KOVETKEZO
F4: RPA+Media+Diagram                          (tervezett)
F5: Monitoring+Governance                       (tervezett)
```

### Szerverek inditasa
```bash
docker compose up -d db redis
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8100
cd aiflow-admin && npx vite --port 5174
```

### FO PARANCSOK
| Parancs | Mikor |
|---------|-------|
| `/start-phase F3` | **F3 fazis inditas** — RAG Engine (12 lepesu HARD GATE pipeline!) |
| `/phase-status F3` | Aktualis fazis allapot |
| `/dev-step` | Fejlesztes + valos teszt + commit (UI: hard gate check!) |
| `/ui-journey` | **GATE 1** — User journey doc (KOTELEZO UI elott!) |
| `/ui-design` | **GATE 4** — Figma design (KOTELEZO UI kodolas elott!) |

### KRITIKUS SZABALYOK (SZIGORITVA!)
1. **7 HARD GATE pipeline:** Journey → API → Figma → UI → E2E → Sync. **TILOS** kihagyni!
2. **Document, NEM Invoice:** F1 UI atnevezes generalalt szolgaltatas nevre
3. **VALOS TESZTELES:** SOHA ne mock/fake! Playwright E2E + curl + valos DB
4. **Alembic ELOSZOR:** Tabla migracio ELOSZOR, service kod MASODSZOR
5. **Ha gate FAIL: STOP** — javitas → gate ujra → AZTAN tovabb

### Hol tartunk?
1. Fejezd be az E2E auditot: Playwright F1+F2 oldalak tesztelese
2. Invoice → Document atnevezes az F1 UI oldalakban
3. Inditsd: `/start-phase F3` — RAG Engine (a 12 lepesu determinisztikus pipeline-nal!)

---
