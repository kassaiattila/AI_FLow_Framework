# AIFlow Session Restart Prompt

Masold be ezt a promptot uj Claude Code session indulaskor:

---

## Kontextus

AIFlow Enterprise AI Automation Framework — service generalizacios fazisban vagyunk (vertikalis szeletek).

### Kiindulas
- **Git tag:** `v0.9.0-stable` (rollback pont)
- **Aktualis branch:** `main`
- **Utolso session:** Teljes konzisztencia audit + fazis atstruktralas (4 commit: 92720a9..d76b3c5)

### FO TERV: `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md`
Olvasd el a terv **Section 5** (Implementacios Fazisok) es **Section 8** (Sikerkritieriumok) szekciot!

**6 fazis, vertikalis szeletek** — egy szolgaltatas TELJESEN KESZ mielott a kovetkezore lepunk:
```
F0: Infra (cache, config, rate limit, schema registry, auth)        → v0.9.1-infra
F1: Document Extractor (backend → API → Figma → UI → E2E)           → v0.10.0-document-extractor
F2: Email Connector + Classifier (backend → API → Figma → UI → E2E) → v0.10.1-email-connector
F3: RAG Engine (backend → API → Figma → UI → E2E)                   → v0.11.0-rag-engine
F4: RPA + Media + Diagram + Human Review (4 mini-szelet)             → v0.12.0-complete-services
F5: Monitoring + Governance + Admin + Production Ready               → v1.0.0-rc1
```

Minden fazis pipeline-ja:
```
Backend → Alembic → API → curl teszt → /ui-journey → /ui-design (Figma MCP)
  → /ui-page (React) → Playwright E2E → /service-test → git tag → KESZ
```

### Projekt szamok
- **DB:** 36 tabla, 13 view, 13 letezo migracio (001-013), 11 tervezett (014-024)
- **Skills:** 6 db (4 working, 1 dev, 1 stub)
- **Commands:** 18 slash command (ld. CLAUDE.md)
- **Services:** `src/aiflow/services/` — TERVEZETT, F0-ban keszul

### Szerverek inditasa
```bash
docker compose up -d db                                                    # PostgreSQL + Redis
.venv/Scripts/python -m uvicorn aiflow.api.app:create_app --factory --port 8100  # FastAPI
cd aiflow-admin && npx vite --port 5174                                    # Admin UI
```

### FO PARANCSOK
| Parancs | Mikor |
|---------|-------|
| `/start-phase F0` | **Fazis inditas** — teljes vertikalis szelet orchestracio |
| `/phase-status F0` | Aktualis fazis allapot |
| `/dev-step` | Fejlesztes + valos teszt + commit |
| `/service-test` | Szolgaltatas E2E teszt (backend + API + UI) |
| `/ui-journey` | User journey + API audit (UI elott!) |
| `/ui-design` | Figma MCP design (API utan!) |
| `/regression` | Regresszios tesztek (commit elott!) |

### KRITIKUS SZABALYOK
1. **Vertikalis szelet:** Egy szolgaltatas TELJESEN KESZ (backend + API + UI + E2E) mielott a kovetkezore lepunk
2. **VALOS TESZTELES:** SOHA ne mock/fake! Playwright E2E + curl + valos DB
3. **API-First + Figma-First:** Backend → API → curl teszt → Figma design → UI → Playwright E2E
4. **Alembic ELOSZOR:** Tabla migracio ELOSZOR, service kod MASODSZOR
5. **Ha teszt sikertelen: STOP** — javitas → ujra teszt → AZTAN tovabb

### Hol tartunk?
1. Olvasd el: `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 5
2. Futtasd: `/phase-status F0` — mi van kesz, mi hianyzik
3. Inditsd: `/start-phase F0` — ha elozo fazis KESZ es tovabb lephetunk

---
