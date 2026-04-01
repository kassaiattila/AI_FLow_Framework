Show the current implementation status of an AIFlow phase.

Arguments: $ARGUMENTS
(Phase: F0, F1, F2, F3, F4, or "all" for overview. Legacy: 1-7 for old phases)

## Service Generalization Phases — Vertikalis Szelet (42_SERVICE_GENERALIZATION_PLAN.md):

> **Minden fazis EGY TELJES szolgaltatas: backend + API + Figma design + UI + Playwright E2E teszt.**
> Nem lepunk a kovetkezore amig az aktualis szelet TELJESEN KESZ!

- **F0** = Infrastruktura (cache, config versioning, rate limiter, retry, schema registry, auth)
- **F1** = **Document Extractor** — teljes szelet (backend → API → Figma → UI → E2E)
- **F2** = **Email Connector + Classifier** — teljes szelet (backend → API → Figma → UI → E2E)
- **F3** = **RAG Engine** — teljes szelet (backend → API → Figma → UI → E2E)
- **F4** = **RPA + Media + Diagram + Human Review** — 4 mini-szelet (F4a-F4d)
- **F5** = **Monitoring + Governance** — cross-cutting + admin + production readiness

## Steps:

1. Read `01_PLAN/42_SERVICE_GENERALIZATION_PLAN.md` Section 5 for phase definition
2. Check which service directories exist:
   ```bash
   ls -la src/aiflow/services/ 2>/dev/null
   ls -la src/aiflow/services/*/ 2>/dev/null
   ```
3. Check which API endpoints are implemented:
   ```bash
   grep -rn "@router\." src/aiflow/api/v1/ | grep -E "get|post|put|delete"
   ```
4. Check test status:
   ```bash
   pytest tests/unit/ -q 2>/dev/null
   ```
5. Check git tags for completed phases:
   ```bash
   git tag -l "v*"
   ```

## Report as table:

| Feladat | Fajl/Service | Statusz | Valos Teszt | Megjegyzes |
|---------|-------------|---------|-------------|------------|
| Cache Layer | services/cache/ | EXISTS/MISSING | curl teszt eredmeny | Redis mukodik? |
| Email Connector | services/email_connector/ | EXISTS/MISSING | Playwright E2E | O365/IMAP? |

## Summary:
- Phase F{X}: {completed}/{total} tasks ({pct}%)
- Git tag: v{X} (exists/missing)
- Services: {created}/{planned}
- **Valos tesztek:** {passed}/{total} (CSAK Playwright/curl, NEM mock!)
- Next task to implement: {description}

## FONTOS:
- Egy fazis CSAK AKKOR "KESZ" ha MINDEN sikerkriteriuma teljesul (ld. 42_SERVICE_GENERALIZATION_PLAN.md Section 8)
- Git tag CSAK sikeres fazis utan kerul kiadasra
- Valos teszteles KOTELEZO — mock/fake eredmeny NEM szamit!
- **Phase 1-7** (framework) es **Fazis 0-5** (service gen) KET FUGGETLEN fazis-rendszer — ne keverd!

## Valos teszteles ellenorzes fazisokent (vertikalis szelet!):
| Fazis | VALOS teszt kovetelmeny |
|-------|------------------------|
| **F0** | Redis cache `curl` (hit/miss), rate limit 429, config CRUD, Alembic 014-016 |
| **F1** | PDF upload → Docling extract → verify → save: **Playwright E2E teljes flow** |
| **F2** | Email config → IMAP fetch → classify → route → show: **Playwright E2E teljes flow** |
| **F3** | Collection → ingest PDF → query → chat → feedback: **Playwright E2E teljes flow** |
| **F4** | Diagram SVG render, video STT, web scrape, human review: **4 mini E2E** |
| **F5** | Audit log, RLS, L4 Complete regresszio, ≥80% coverage, 90%+ API |
