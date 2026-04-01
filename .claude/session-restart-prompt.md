# AIFlow Session Restart Prompt

Masold be ezt a promptot uj Claude Code session indulaskor:

---

## Kontextus

AIFlow Enterprise AI Automation Framework — service generalizacios fazisban vagyunk.

### Kiindulas
- **Git tag:** `v0.9.0-stable` (rollback pont)
- **Aktualis branch:** `main`
- **Utolso commit:** `e33686e` (Alembic strategy)

### FO TERV: `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`
Olvasd el a teljes tervet! Tartalmazza:
- 7 domain szolgaltatas (Email Connector, Document Extractor, RAG Engine, Classifier, RPA Browser, Media Processor, Diagram Generator)
- 9 infra epitokocka (Cache, Events, Config Versioning, Health Monitoring, Rate Limiter, Circuit Breaker, Human Review, Audit Trail, Schema Registry)
- 5 fazis: F0 (infra) → F1 (Email+Doc+Classifier) → F2 (RAG+Monitoring) → F3 (RPA+Media) → F4 (Governance)
- Alembic migracios strategia: 13 letezo migracio (001-013), 11 tervezett (014-024)
- DB: 36 tabla + 13 view PostgreSQL-ben (localhost:5433) — ld. `03_DATABASE_SCHEMA.md`

### Projekt struktura
- **Backend:** `src/aiflow/` (FastAPI, Python 3.12+, port 8100)
- **Admin UI:** `aiflow-admin/` (Vite + React Admin + MUI, port 5174)
- **Legacy UI:** `aiflow-ui/` (Next.js — DEPRECATED, ne hasznald!)
- **Skills:** `skills/` (6 skill, ebbol 4 production, 1 dev, 1 stub)
- **Services:** `src/aiflow/services/` (TERVEZETT, meg nem letezik — F0-ban keszul)
- **Tervek:** `01_PLAN/` (49 dokumentum)

### Szerverek inditasa
```bash
# 1. Docker (DB + Redis)
docker compose up -d db

# 2. FastAPI backend
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8100

# 3. Admin UI (Vite)
cd aiflow-admin && npx vite --port 5174
```

### KRITIKUS SZABALYOK
1. **VALOS TESZTELES KOTELEZO** — SOHA ne mock/fake adatokkal! Playwright MCP E2E teszt minden UI valtozasnal.
2. **Alembic ELOSZOR** — Tabla ELOSZOR (migracio), service kod MASODSZOR. SOHA ne hozz letre tablat raw SQL-lel!
3. **Ha egy teszt sikertelen: STOP** — elobb javitsd, teszteld ujra, AZTAN lepj tovabb.
4. **Fejlesztes utan:** `/dev-step` parancs — backend curl teszt + TypeScript check + Playwright E2E
5. **`source` mezo KOTELEZO** minden API valaszban: `"backend"` vagy `"demo"`
6. **Git tag** minden fazis vegen (v0.9.1-infra, v0.10.0-services, stb.)

### Hasznos parancsok
- `/dev-step` — fejlesztes + valos teszt + commit (FO PARANCS)
- `/phase-status F0` — aktualis fazis allapot
- `/regression` — regresszios tesztek
- `curl -s http://localhost:8100/health` — backend check
- `curl -s http://localhost:8100/api/v1/documents | head -100` — adat check

### Hol tartunk?
Kerdezd meg: "Melyik fazissal/feladattal folytassuk?" es olvasd el a `42_SERVICE_GENERALIZATION_PLAN.md` Section 5 (Bovitett Implementacios Fazisok) aktualis feladatait!

---
