# AIFlow v1.0.0 — Helyzetjelentes (2026-04-02)

**Cel:** Teljes kontextus a kovetkezo session-hoz (UI finomhangolas, funkciobovites).

---

## 1. Projekt Osszefoglalo

| Metrika | Ertek |
|---------|-------|
| **Verzio** | v1.0.0 (tag: `1436c8f`) |
| **Python modulok** | 182 (`src/aiflow/`) |
| **API endpointok** | 87 (20 router fajl) |
| **DB tablak** | 41 + 6 view |
| **Alembic migraciok** | 25 (001-025) |
| **Services** | 15 (`src/aiflow/services/`) |
| **Admin UI oldalak** | 18 (`aiflow-admin/`) |
| **TypeScript fajlok** | 41 (`aiflow-admin/src/`) |
| **i18n kulcsok** | ~214 HU + ~214 EN |
| **Skills** | 6 (4 working, 1 in-dev, 1 stub) |
| **Teszt fajlok** | 87 (`tests/`) |
| **Git commitok** | 183, 9 tag |

---

## 2. Architektura

### Backend Stack
- **Python 3.12+**, FastAPI, PostgreSQL 16 + pgvector, Redis
- **LiteLLM** (multi-LLM), instructor (structured output), Langfuse (observability)
- **arq + Redis** (async job queue), APScheduler 4.x (cron)
- **bcrypt** (password hash), PyJWT-kompatibilis custom token, SHA256 API keys
- **Alembic** (migraciok), structlog (JSON logging), ruff (lint)

### Frontend Stack
- **React Admin + Vite + React 19 + MUI** (`aiflow-admin/`)
- **i18nProvider.ts** — teljes HU/EN, ~214 kulcs
- Vite proxy → FastAPI `localhost:8101`
- ~~Next.js 16 + shadcn/ui~~ (`aiflow-ui/` TOROLVE, archiv: `v0.9-nextjs-ui` tag)

### Security (v1.0.0 javitasok)
- AuthMiddleware: minden `/api/v1/*` es `/v1/*` endpoint vedett
- RBAC: `/api/v1/admin/*` → admin role kell
- Publikus: `/health/*`, `/api/v1/auth/login`, `/docs`
- CORS: `AIFLOW_CORS_ORIGINS` env var (production: REQUIRED)
- JWT: production-ben min 32 char secret REQUIRED
- Traceback: production-ben elrejtve (error_id only)
- Connection pool: kozponti asyncpg pool + SQLAlchemy engine (`deps.py`)

---

## 3. API Endpoint Terkep (87 endpoint, 20 router)

### Auth & Admin (12 endpoint)
| Prefix | Endpoint | Megjegyzes |
|--------|----------|------------|
| `/api/v1/auth` | POST `/login`, GET `/me`, POST `/refresh` | DB + bcrypt, JWT token |
| `/api/v1/admin` | GET/POST `/users`, GET/POST/DELETE `/api-keys` | Admin role required |
| `/api/v1/admin` | GET `/health`, GET `/health/{name}`, GET `/metrics` | Service monitoring |
| `/api/v1/admin` | GET `/audit`, GET `/audit/{id}` | Audit trail |

### Document Processing (10 endpoint)
| Prefix | Endpoint | Megjegyzes |
|--------|----------|------------|
| `/api/v1/documents` | GET list, GET by-id, GET by-path | Dokumentum lista + detail |
| | POST `/upload`, POST `/process`, POST `/process-stream` | Upload + feldolgozas (SSE) |
| | POST `/{id}/verify` | Verifikacio |
| | GET `/images/{file}/page_{n}.png` | PDF rendereles |
| | GET/POST `/extractor/configs` | Konfig CRUD |

### Email Processing (13 endpoint)
| Prefix | Endpoint | Megjegyzes |
|--------|----------|------------|
| `/api/v1/emails` | GET list, GET `/{id}` | Email lista + detail |
| | POST `/upload`, POST `/process`, POST `/classify` | Upload + process + classify |
| | GET/POST/PUT/DELETE `/connectors/*` | IMAP/O365 connector CRUD |
| | POST `/connectors/{id}/test`, POST `/fetch` | Connector test + fetch |

### RAG Engine (12 endpoint)
| Prefix | Endpoint | Megjegyzes |
|--------|----------|------------|
| `/api/v1/rag` | GET/POST/PUT/DELETE `/collections/*` | Collection CRUD |
| | POST `/collections/{id}/ingest` | Dokumentum ingest |
| | GET `/collections/{id}/ingest-status` | Ingest status |
| | POST `/collections/{id}/query` | RAG query |
| | POST `/collections/{id}/feedback` | Feedback |
| | GET `/collections/{id}/stats`, `/chunks` | Statisztika, chunk browse |

### Diagram + Media + RPA + Review (21 endpoint)
| Prefix | Endpoint | Megjegyzes |
|--------|----------|------------|
| `/api/v1/diagrams` | POST `/generate`, GET list/detail/export, DELETE | BPMN generalas |
| `/api/v1/media` | POST `/upload`, GET list/detail, DELETE | Video/audio STT |
| `/api/v1/rpa` | GET/POST/DELETE `/configs/*`, POST `/execute`, GET `/logs` | RPA automatizalas |
| `/api/v1/reviews` | GET `/pending`, `/history`, POST create/approve/reject | Human review |

### Infra + Monitoring (19 endpoint)
| Prefix | Endpoint | Megjegyzes |
|--------|----------|------------|
| `/health` | GET `/`, `/live`, `/ready` | K8s probe |
| `/api/v1/costs` | GET `/summary`, `/team-daily`, `/budget` | Koltseg + budget |
| `/api/v1/services` | GET `/`, `/health`, `/cache/stats`, `/rate-limit/*`, `/resilience/*` | Infra |
| `/api/v1/runs` | GET list, GET `/{id}` | Workflow run historia |
| `/api/v1/workflows` | GET list, GET `/{name}`, POST `/{name}/run` | Workflow inditas |
| `/v1/chat/completions` | POST (OpenAI compat) | LLM chat |
| `/v1/feedback` | POST submit, GET stats | Feedback |

---

## 4. Admin UI Oldalak (aiflow-admin/)

### React Admin Resources (read-only CRUD)
| Resource | List | Show | Megjegyzes |
|----------|------|------|------------|
| `runs` | RunList | RunShow | Workflow futasok |
| `documents` | DocumentList | DocumentShow | Dokumentumok |
| `emails` | EmailList | EmailShow | Emailek |

### Custom Pages (18 oldal)
| Oldal | Fajl | Funkció |
|-------|------|---------|
| **Dashboard** | App.tsx (beepitett) | KPI kartyak, aktiv pipeline-ok, friss aktivitas |
| **ProcessDocViewer** | ProcessDocViewer.tsx | BPMN diagram generalas NL-bol + review |
| **RagChat** | RagChat.tsx | Chat UI kollekcio-valasztoval, streaming, hallucination |
| **CubixViewer** | CubixViewer.tsx | Cubix kurzus metadata megjelenites |
| **DocumentUpload** | DocumentUpload.tsx | Dokumentum upload + feldolgozo pipeline |
| **EmailUpload** | EmailUpload.tsx | Email fajl upload + feldolgozas |
| **EmailConnectors** | EmailConnectors.tsx | IMAP/O365 connector CRUD + test + history |
| **CostsPage** | CostsPage.tsx | Koltseg tablak + chart-ok |
| **CollectionManager** | CollectionManager.tsx | RAG kollekcio CRUD |
| **CollectionDetail** | CollectionDetail.tsx | Kollekcio detail: ingest, chunks, stats |
| **MediaViewer** | MediaViewer.tsx | Media job lista + upload (STT) |
| **RpaViewer** | RpaViewer.tsx | RPA config CRUD + execution log |
| **ReviewQueue** | ReviewQueue.tsx | Human review: pending/approved/rejected |
| **MonitoringDashboard** | MonitoringDashboard.tsx | Service health + metrics |
| **AuditLog** | AuditLog.tsx | Audit trail + szures + CSV export |
| **AdminPage** | AdminPage.tsx | User + API key management |
| **VerificationPanel** | (route: /documents/:id/verify) | Dokumentum mezo verifikacio |

### UI Komponensek
| Komponens | Funkció |
|-----------|---------|
| PipelineProgress.tsx | Animalt pipeline step progress bar |
| StepTimeline.tsx | Vertikalis timeline run execution-hoz |

### Figma Design
- **PAGE_SPECS.md**: 19 oldal tervezve
- **Figma file**: `GPg8UQzYXYust9vjN5AAwQ` (Untitled UI components)
- **Channel**: `hq5dlkhu`

---

## 5. Services (src/aiflow/services/)

| Service | Mappa | Leiras |
|---------|-------|--------|
| **audit** | `audit/` | Immutable audit trail (DB log) |
| **cache** | `cache/` | Redis embedding + LLM cache |
| **classifier** | `classifier/` | Hibrid ML+LLM intent classifier |
| **config** | `config/` | Config versioning (DB CRUD) |
| **diagram_generator** | `diagram_generator/` | BPMN diagram generalas (Mermaid + DrawIO + SVG) |
| **document_extractor** | `document_extractor/` | PDF/DOCX feldolgozas (Docling + Azure + LLM) |
| **email_connector** | `email_connector/` | O365/Gmail/IMAP email fetch |
| **health_monitor** | `health_monitor/` | Service health check + metrics |
| **human_review** | `human_review/` | Approval flow (pending/approve/reject) |
| **media_processor** | `media_processor/` | Video/audio → STT transcript |
| **rag_engine** | `rag_engine/` | pgvector hybrid search + chat |
| **rate_limiter** | `rate_limiter/` | Redis sliding window rate limit |
| **resilience** | `resilience/` | Circuit breaker |
| **rpa_browser** | `rpa_browser/` | YAML-alapu browser automatizalas |
| **schema_registry** | `schema_registry/` | Kozponti JSON schema kezeles |

---

## 6. Skills

| Skill | Tipus | Statusz |
|-------|-------|---------|
| **process_documentation** | ai | PRODUCTION — NL → BPMN diagram |
| **cubix_course_capture** | hybrid | PRODUCTION — video STT + RPA |
| **aszf_rag_chat** | ai | PRODUCTION — RAG chat (86% eval) |
| **email_intent_processor** | ai | PRODUCTION — email + intent + routing |
| **invoice_processor** | ai | IN DEV — PDF szamla feldolgozas |
| **qbpp_test_automation** | rpa | STUB — biztositasi kalkulator teszt |

---

## 7. Database (41 tabla, 6 view, 25 migracio)

### Tablak (fobb csoportok)
- **Core:** workflow_runs, step_runs, workflow_definitions, skills, skill_instances
- **Security:** users, teams, api_keys, audit_log
- **Documents:** documents, invoices, invoice_line_items, document_type_configs
- **Email:** email_connector_configs, email_fetch_history
- **RAG:** rag_collections, rag_chunks, rag_feedback, rag_query_log, collections, chunks, embedding_models
- **Media/RPA:** media_jobs, rpa_configs, rpa_execution_log, generated_diagrams
- **Review:** human_review_queue, human_reviews
- **Infra:** service_config_versions, service_health_log, schedules, cost_records, model_registry
- **Testing:** test_cases, test_datasets, test_results, ab_experiments, ab_assignments, ab_outcomes
- **Prompts:** skill_prompt_versions, document_sync_schedules

### View-k
- v_daily_team_costs, v_monthly_budget (→ `/api/v1/costs/` endpoint-ok)
- v_workflow_metrics, v_instance_stats, v_model_usage, v_test_trends (→ monitoring dashboard-hoz)

---

## 8. Kovetkezo Session: Javasolt Feladatok

### A) UI Finomhangolas (PRIORITAS)

#### A1. Figma ↔ Code konzisztencia audit
- **PAGE_SPECS.md** vs tenyleges UI: minden oldal megfelel-e a Figma tervnek?
- Untitled UI komponens-konyvtar hasznalata konzisztens-e?
- Dark/light mode minden oldalon mukodik-e?

#### A2. UX javitasok
- **Loading state-ek**: skeleton/spinner minden oldalon?
- **Error state-ek**: retry gomb, ertelmeshiba uzenet?
- **Empty state-ek**: ertelmesuzenet ha nincs adat?
- **Responsiveness**: mobile/tablet nezetekre optimalizalt-e?

#### A3. Dashboard javitas
- KPI kartyak valos backend adattal (jelenleg reszben demo)
- v_workflow_metrics es v_instance_stats view-k integralasa
- Real-time frissites (polling vagy WebSocket)

#### A4. Verifikacio oldal finomhangolas
- PDF overlay pontossag
- Mezo szerkesztes UX (inline edit vs dialog)
- Batch verify mukodes

#### A5. RAG Chat javitas
- Streaming valasz megjelenites
- Citation panel kattinthatosag
- Hallucination indicator finomhangolas
- Collection valtasakor context reset

#### A6. Costs oldal bovites
- Chart-ok (bar/line) a v_daily_team_costs adatbol
- Budget alert vizualizacio
- Export CSV/Excel

### B) Funkciobovites

#### B1. Workflow Builder UI
- Vizualis DAG szerkeszto (drag & drop)
- Step konfiguracio panel
- Workflow inditas es monitorozas

#### B2. Scheduling UI
- APScheduler cron job kezeles
- Job lista + history
- Enable/disable toggle

#### B3. Evaluation Dashboard
- Promptfoo eredmenyek megjelenites
- Skill-enkenti pass rate trendek
- A/B teszt eredmenyek

#### B4. User Management bovites
- Jelszo csere
- Role valtas
- Team hozzarendeles
- API key lejarat

### C) Backend Finomhangolas

#### C1. PyJWT migracio
- Custom token → szabvanyos PyJWT RS256
- Key rotation tamogatas

#### C2. WebSocket support
- Real-time dashboard frissites
- Processing pipeline progress

#### C3. Teszteles
- Unit test coverage noveles (cel: 80%)
- Playwright E2E tesztek minden UI oldalra
- Load test: 50 parhuzamos request

---

## 9. Git Tag Historia

| Tag | Datum | Tartalom |
|-----|-------|----------|
| `v0.9.0-stable` | 2026-03-28 | Framework mag kesz (Phase 1-7) |
| `v0.9-nextjs-ui` | 2026-03-30 | Utolso Next.js UI verzio (ARCHIV) |
| `v0.9.1-infra` | 2026-04-01 | F0: infra epitokockak |
| `v0.10.0-document-extractor` | 2026-04-01 | F1: Document Extractor |
| `v0.10.1-email-connector` | 2026-04-01 | F2: Email + Classifier |
| `v0.11.0-rag-engine` | 2026-04-01 | F3: RAG Engine |
| `v0.12.0-complete-services` | 2026-04-02 | F4: RPA + Media + Diagram |
| `v1.0.0-rc1` | 2026-04-02 | F5: Monitoring + Governance |
| **`v1.0.0`** | **2026-04-02** | **Production release + security fix** |

---

## 10. Fajlok es Mappak

```
src/aiflow/
    api/           # FastAPI (app.py, deps.py, middleware.py, v1/*.py)
    core/          # Config, context, errors, events, registry, types
    engine/        # Step, SkillRunner, WorkflowRunner, DAG
    models/        # ModelClient, LiteLLM backend
    prompts/       # PromptManager (YAML + Jinja2)
    services/      # 15 domain + infra service
    execution/     # JobQueue (arq+Redis), Worker, Scheduler
    evaluation/    # EvalSuite, scorers, Promptfoo
    skill_system/  # Skill manifest, loader, registry, instance
    tools/         # Shell, Playwright, RobotFramework, HumanLoop
    vectorstore/   # pgvector, HybridSearchEngine
    documents/     # DocumentRegistry, versioning
    ingestion/     # Parsers (PDF/DOCX), chunkers
    state/         # SQLAlchemy ORM, repository
    security/      # JWT auth, RBAC, secrets
    observability/ # Tracing, cost_tracker
    cli/           # typer CLI
aiflow-admin/      # React Admin + Vite + MUI (AKTIV production dashboard)
skills/            # 6 skill package
alembic/           # 25 migracio
tests/             # 87 teszt fajl
scripts/           # seed_admin.py + utility scripts
01_PLAN/           # Dokumentacio (42+ terv dokumentum)
```

---

## 11. Inditas Gyorsutmutato

```bash
# Backend
make dev                    # Docker (PostgreSQL, Redis) + Alembic migrate
make api                    # FastAPI @ localhost:8101

# Seed admin user
AIFLOW_ADMIN_EMAIL=admin@bestix.hu AIFLOW_ADMIN_PASSWORD=Admin1234 \
  python scripts/seed_admin.py

# Frontend
cd aiflow-admin && npm run dev   # Vite @ localhost:5173 (proxy → 8101)

# Teszt
curl -X POST http://localhost:8101/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@bestix.hu","password":"Admin1234"}'
```
