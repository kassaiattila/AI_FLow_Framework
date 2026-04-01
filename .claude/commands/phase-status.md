Show the current implementation status of an AIFlow phase.

Arguments: $ARGUMENTS
(Phase: F0, F1, F2, F3, F4, or "all" for overview. Legacy: 1-7 for old phases)

## Service Generalization Phases (aktualis — 42_SERVICE_GENERALIZATION_PLAN.md):

- **F0** = Infrastruktura Alapozas (cache, config versioning, rate limiter, retry, __all__ exports)
- **F1** = Domain Szolgaltatasok A (Schema Registry, Email Connector, Document Extractor, Classifier, Auth)
- **F2** = RAG Engine + Monitoring (RAG multi-collection, Health Monitoring, Event Bus, Cost Budget, Runs API)
- **F3** = RPA + Media + Approval (RPA Browser, Media Processor, Diagram Generator, Human Review, Skills API)
- **F4** = Governance & Production Ready (Audit Trail, Prompts API, Scheduling, Admin, Tests, Multi-tenant RLS)

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
- **Phase 1-7** (framework) es **Fazis 0-4** (service gen) KET FUGGETLEN fazis-rendszer — ne keverd!

## Valos teszteles ellenorzes fazisokent:
| Fazis | VALOS teszt kovetelmeny |
|-------|------------------------|
| **F0** | Redis cache `curl` teszt (hit/miss), rate limit 429, config CRUD, Alembic 014-016 |
| **F1** | IMAP email fetch, PDF Docling extraction, Playwright Admin UI E2E, backward compat |
| **F2** | RAG ingest+query valos PDF, Playwright chat UI, health endpoint, event publish |
| **F3** | Playwright web scrape, ffmpeg+Whisper transcript, Human review E2E, SVG render |
| **F4** | Audit log DB check, RLS test, L4 Complete regresszio, ≥80% coverage |
