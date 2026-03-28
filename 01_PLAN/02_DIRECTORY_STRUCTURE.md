# AIFlow - Konyvtar Struktura

## Teljes Projekt Struktura

```
aiflow/
|
|-- pyproject.toml                          # Package def, fuggosegek, tool config
|-- alembic.ini                             # DB migration config
|-- aiflow.yaml                             # Framework-level config (nem titkok!)
|-- .env.example                            # Titkok template
|-- docker-compose.yml                      # Dev kornyezet
|-- docker-compose.prod.yml                 # Production overrides
|-- Dockerfile                              # API + Worker image
|-- Makefile                                # Gyakori parancsok (make dev, make test, etc.)
|
|-- k8s/                                    # Kubernetes manifests
|   |-- base/
|   |   |-- namespace.yaml
|   |   |-- configmap.yaml
|   |   |-- secrets.yaml                    # Vault referenciak
|   |-- overlays/
|       |-- dev/
|       |-- staging/
|       |-- prod/
|
|-- src/
|   |-- aiflow/                             # Fo Python csomag
|   |   |-- __init__.py                     # Public API exports
|   |   |-- _version.py                     # Egyetlen verzioszam forras
|   |   |
|   |   |-- core/                           # Framework kernel
|   |   |   |-- __init__.py
|   |   |   |-- config.py                   # AIFlowSettings (pydantic-settings)
|   |   |   |-- registry.py                 # Univerzalis registry (workflows, skills, agents)
|   |   |   |-- types.py                    # Kozos tipusdefiniciok
|   |   |   |-- errors.py                   # Exception hierarchia
|   |   |   |-- context.py                  # ExecutionContext (request-scoped)
|   |   |   |-- di.py                       # Dependency Injection container
|   |   |   |-- events.py               # Event Bus (CrewAI minta)
|   |   |
|   |   |-- engine/                         # Workflow execution engine
|   |   |   |-- __init__.py
|   |   |   |-- workflow.py                 # Workflow class + @workflow decorator
|   |   |   |-- step.py                     # Step class + @step decorator
|   |   |   |-- dag.py                      # DAG builder, topological sort, validation
|   |   |   |-- runner.py                   # WorkflowRunner (local + distributed)
|   |   |   |-- checkpoint.py              # Checkpoint/resume hosszu workflow-khoz
|   |   |   |-- policies.py               # RetryPolicy, CircuitBreaker, Timeout
|   |   |   |-- conditions.py             # Feltetelek elagazasokhoz
|   |   |   |-- serialization.py        # Workflow YAML export/import (Haystack minta)
|   |   |
|   |   |-- agents/                         # 2-szintu agent rendszer
|   |   |   |-- __init__.py
|   |   |   |-- orchestrator.py             # Orchestrator bazis osztaly
|   |   |   |-- specialist.py              # Specialist agent bazis osztaly
|   |   |   |-- messages.py                # AgentRequest, AgentResponse (tipusos)
|   |   |   |-- quality_gate.py            # Score-alapu minosegi kapuk
|   |   |   |-- human_loop.py             # Human-in-the-loop integracio
|   |   |   |-- reflection.py             # Generate-Critique-Improve loop
|   |   |
|   |   |-- skills/                         # Skill (domain knowledge) rendszer
|   |   |   |-- __init__.py
|   |   |   |-- base.py                    # Skill bazis osztaly
|   |   |   |-- loader.py                  # Skill felfedeztes es betoltes
|   |   |   |-- manifest.py               # SkillManifest (progressive disclosure)
|   |   |   |-- registry.py               # Skill registry
|   |   |
|   |   |-- prompts/                        # Prompt menedzsment platform
|   |   |   |-- __init__.py
|   |   |   |-- manager.py                # PromptManager (Langfuse SSOT + fallback)
|   |   |   |-- sync.py                   # YAML -> Langfuse sync pipeline
|   |   |   |-- ab_testing.py             # A/B teszteles traffic splitting-gel
|   |   |   |-- schema.py                 # Prompt YAML schema definiciok
|   |   |   |-- analytics.py              # Prompt teljesitmeny analitika
|   |   |
|   |   |-- execution/                      # Queue-alapu vegrehajtasi platform
|   |   |   |-- __init__.py
|   |   |   |-- queue.py                   # JobQueue (arq + Redis)
|   |   |   |-- worker.py                 # WorkflowWorker (pool management)
|   |   |   |-- scheduler.py              # Cron, event, webhook triggerek
|   |   |   |-- dlq.py                    # Dead Letter Queue
|   |   |   |-- rate_limiter.py           # Konkurencia es rate limiting
|   |   |   |-- messaging.py            # MessageBroker abstract interface
|   |   |
|   |   |-- state/                          # Elosztott allapotkezeles
|   |   |   |-- __init__.py
|   |   |   |-- models.py                  # SQLAlchemy ORM modellek
|   |   |   |-- repository.py             # Adathozzaferesi reteg
|   |   |   |-- migrations/               # Alembic migraciok
|   |   |   |   |-- env.py
|   |   |   |   |-- versions/
|   |   |
|   |   |-- observability/                  # Teljes megfigyelehetoseg
|   |   |   |-- __init__.py
|   |   |   |-- tracing.py                # Langfuse (LLM) + OpenTelemetry (infra)
|   |   |   |-- cost_tracker.py           # Koltseg kovetest per workflow/team/model
|   |   |   |-- sla_monitor.py            # SLA monitoring es alerting
|   |   |   |-- logging.py                # structlog konfig (JSON output)
|   |   |   |-- metrics.py                # Prometheus metriak
|   |   |
|   |   |-- evaluation/                     # Evaluation-driven development
|   |   |   |-- __init__.py
|   |   |   |-- framework.py              # EvalSuite - tesztfuttato
|   |   |   |-- scorers.py                # Beepitett scoring fuggvenyek
|   |   |   |-- promptfoo.py              # Promptfoo integracio
|   |   |   |-- datasets.py               # Teszt dataset kezeles
|   |   |   |-- reports.py                # Evaluacios riportok
|   |   |
|   |   |-- security/                       # Biztonsag es governance
|   |   |   |-- __init__.py
|   |   |   |-- auth.py                    # JWT + API key authentication
|   |   |   |-- rbac.py                    # Role-Based Access Control
|   |   |   |-- audit.py                   # Audit logging
|   |   |   |-- secrets.py                 # Vault integracio (prod) / .env (dev)
|   |   |   |-- guardrails.py              # Input/output guardrails
|   |   |
|   |   |-- api/                            # FastAPI alkalmazas
|   |   |   |-- __init__.py
|   |   |   |-- app.py                     # Application factory (create_app)
|   |   |   |-- deps.py                    # Dependency injection route-okhoz
|   |   |   |-- middleware.py              # Auth, CORS, rate limiting middleware
|   |   |   |-- v1/
|   |   |   |   |-- __init__.py
|   |   |   |   |-- workflows.py           # Workflow CRUD + execution
|   |   |   |   |-- jobs.py                # Job statusz es management
|   |   |   |   |-- skills.py              # Skill registry endpoints
|   |   |   |   |-- prompts.py             # Prompt management endpoints
|   |   |   |   |-- evaluations.py         # Evaluation endpoints
|   |   |   |   |-- schedules.py           # Scheduler CRUD
|   |   |   |   |-- admin.py               # Admin: users, teams, budgets
|   |   |   |   |-- health.py              # Health + readiness checks
|   |   |
|   |   |-- llm/                            # LLM absztrakcios reteg
|   |   |   |-- __init__.py
|   |   |   |-- client.py                  # LiteLLM wrapper retry + fallback
|   |   |   |-- instructor.py             # Structured output (instructor lib)
|   |   |   |-- models.py                 # Model registry (cost/capability info)
|   |   |
|   |   |-- cli/                            # CLI tool (typer-based)
|   |   |   |-- __init__.py
|   |   |   |-- main.py                    # Fo CLI belepesi pont
|   |   |   |-- commands/
|   |   |       |-- init.py                # aiflow init
|   |   |       |-- workflow.py            # aiflow workflow {new,list,run,test,inspect,replay,docs,export}
|   |   |       |-- skill.py              # aiflow skill {new,install,list,test,validate,upgrade,uninstall}
|   |   |       |-- prompt.py             # aiflow prompt {sync,test,diff,promote,rollback,list}
|   |   |       |-- eval.py               # aiflow eval {run,report}
|   |   |       |-- dev.py                # aiflow dev {up,logs,shell}
|   |   |       |-- deploy.py             # aiflow deploy {staging,prod}
|   |   |       |-- report.py           # aiflow report {compliance,cost,sla}
|   |   |       |-- admin.py            # aiflow admin {redact,users,teams}
|   |   |
|   |   |-- models/                          # ML Modell reteg (LECSERELI llm/-t!)
|   |   |   |-- __init__.py
|   |   |   |-- client.py                  # ModelClient facade (generate,embed,classify,extract,vision)
|   |   |   |-- registry.py               # DB-backed ModelRegistry + lifecycle
|   |   |   |-- router.py                 # Cost/capability/latency routing + fallback
|   |   |   |-- metadata.py               # ModelMetadata, ModelType, enums
|   |   |   |-- cost.py                   # ModelCostCalculator
|   |   |   |-- protocols/
|   |   |   |   |-- generation.py          # TextGenerationProtocol (LLM)
|   |   |   |   |-- embedding.py           # EmbeddingProtocol
|   |   |   |   |-- classification.py      # ClassificationProtocol
|   |   |   |   |-- extraction.py          # ExtractionProtocol (NER)
|   |   |   |   |-- vision.py              # VisionProtocol (OCR)
|   |   |   |   |-- custom.py              # CustomModelProtocol
|   |   |   |-- backends/
|   |   |   |   |-- litellm_backend.py     # LiteLLM (default: LLM + embedding)
|   |   |   |   |-- local_backend.py       # In-process (transformers, sklearn)
|   |   |   |   |-- server_backend.py      # Triton, TorchServe, vLLM
|   |   |   |-- finetuning/
|   |   |       |-- manager.py              # FineTuneManager
|   |   |       |-- data_collector.py       # Training data gyujtes
|   |   |
|   |   |-- vectorstore/                    # Vector DB (RAG skill-ekhez)
|   |   |   |-- __init__.py
|   |   |   |-- base.py                    # VectorStore ABC, SearchResult, SearchFilter
|   |   |   |-- pgvector_store.py          # pgvector HNSW + BM25 + RRF
|   |   |   |-- embedder.py               # Embedding generalas (LiteLLM wrapper)
|   |   |   |-- search.py                 # HybridSearchEngine
|   |   |
|   |   |-- documents/                      # Dokumentum eletciklus (RAG)
|   |   |   |-- __init__.py
|   |   |   |-- registry.py               # DocumentRegistry (CRUD + lifecycle)
|   |   |   |-- versioning.py             # Supersession, version tracking
|   |   |   |-- freshness.py              # Freshness enforcement
|   |   |   |-- sync.py                   # External sync (SharePoint, S3, GDrive)
|   |   |
|   |   |-- ingestion/                      # Dokumentum feldolgozas
|   |   |   |-- __init__.py
|   |   |   |-- pipeline.py               # IngestionPipeline
|   |   |   |-- parsers/
|   |   |   |   |-- pdf_parser.py
|   |   |   |   |-- docx_parser.py
|   |   |   |   |-- xlsx_parser.py
|   |   |   |-- chunkers/
|   |   |       |-- semantic_chunker.py
|   |   |       |-- fixed_size_chunker.py
|   |   |
|   |   |-- ui/                             # Frontend (Reflex / NiceGUI / Next.js)
|   |   |   |-- pages/
|   |   |   |   |-- operator/              # Dashboard, jobs, alerts
|   |   |   |   |-- chat/                  # RAG chat, history, upload
|   |   |   |   |-- developer/             # Workflows, prompts, evals
|   |   |   |   |-- admin/                 # Users, teams, RBAC, audit
|   |   |   |   |-- reports/               # Usage, costs, SLA, docs
|   |   |   |-- components/                # Reusable UI components
|   |   |
|   |   |-- contrib/                        # Opcionalis integraciok
|   |       |-- playwright/                 # Web automatizacio (RPA + GUI teszt)
|   |       |   |-- browser.py             # PlaywrightBrowser DI service
|   |       |   |-- page_actions.py
|   |       |-- shell/                      # Sandboxed shell (ffmpeg, pandoc)
|   |       |   |-- executor.py
|   |       |   |-- sandbox.py
|   |       |-- messaging/                  # Kafka, RabbitMQ, Azure SB, AWS SQS
|   |       |   |-- kafka.py
|   |       |   |-- rabbitmq.py
|   |       |-- n8n/                        # n8n vizualis workflow editor
|   |       |-- chainlit/                   # Chat UI (legacy)
|   |       |-- kroki/                      # Diagram rendereles
|   |       |   |-- client.py
|   |       |-- miro/                       # Miro board integracio
|   |       |   |-- exporter.py
|   |       |-- docs/                       # Auto-gen dokumentacio
|   |       |   |-- generator.py            # Workflow docs generalas
|   |       |   |-- compliance.py           # Compliance riport
|   |       |-- mcp_server.py               # Claude Code MCP server
|
|-- skills/                                 # Beepitett skill csomagok
|   |-- process_documentation/              # Skill 1: AI - Diagram generalas (POC)
|   |   |-- skill.yaml                      # Skill manifest
|   |   |-- __init__.py
|   |   |-- workflow.py                     # process-documentation workflow
|   |   |-- agents/
|   |   |   |-- __init__.py
|   |   |   |-- classifier.py              # ClassifierAgent
|   |   |   |-- elaborator.py              # ElaboratorAgent
|   |   |   |-- extractor.py               # ExtractorAgent
|   |   |   |-- reviewer.py                # ReviewerAgent
|   |   |   |-- diagram_generator.py       # DiagramGeneratorAgent
|   |   |-- models/
|   |   |   |-- __init__.py
|   |   |   |-- process.py                  # ProcessExtraction, ProcessStep, StepType
|   |   |-- prompts/
|   |   |   |-- classifier.yaml
|   |   |   |-- elaborator.yaml
|   |   |   |-- extractor.yaml
|   |   |   |-- reviewer.yaml
|   |   |   |-- mermaid_flowchart.yaml
|   |   |-- tools/
|   |   |   |-- diagram_renderer.py         # Kroki integracio
|   |   |   |-- table_generator.py          # MD/DOCX/XLSX export
|   |   |   |-- drawio_exporter.py          # Draw.io XML export
|   |   |   |-- miro_exporter.py            # Miro board export
|   |   |-- tests/
|   |       |-- promptfooconfig.yaml
|   |       |-- test_classifier.py
|   |       |-- test_extractor.py
|   |       |-- test_workflow.py
|   |       |-- datasets/
|   |           |-- classification_100.json  # 100+ teszt eset
|   |           |-- extraction_100.json
|   |
|   |-- aszf_rag_chat/                      # Skill 2: AI+RAG - ASZF dokumentum chat
|   |   |-- skill.yaml
|   |   |-- workflow.py                     # Q&A workflow
|   |   |-- ingest_workflow.py              # Document ingestion workflow
|   |   |-- agents/                         # classifier, search, rerank, answer, citation
|   |   |-- models/                         # document.py, conversation.py, answer.py
|   |   |-- prompts/                        # answer_generator.yaml, citation.yaml, etc.
|   |   |-- tests/
|   |
|   |-- email_intent_processor/             # Skill 3: AI+Kafka - Email routing
|   |   |-- skill.yaml
|   |   |-- workflow.py
|   |   |-- agents/                         # classifier, extractor, faq_search, drafter
|   |   |-- prompts/
|   |   |-- tests/
|   |
|   |-- cubix_course_capture/               # Skill 4: Hybrid RPA - Kurzus rogzites
|   |   |-- skill.yaml
|   |   |-- workflows/                      # course_capture.py, transcript_processing.py
|   |   |-- agents/                         # web_navigator, audio_extractor, transcriber, structurer
|   |   |-- config/selectors.yaml
|   |   |-- prompts/structurer.yaml
|   |   |-- tests/
|   |
|   |-- cfpb_complaint_router/              # Skill 5: ML - Szoveg klasszifikacio
|   |   |-- skill.yaml
|   |   |-- workflow.py
|   |   |-- agents/                         # text_cleaner, classifier, router
|   |   |-- models/                         # intent_mapping, routing_groups
|   |   |-- tests/
|   |
|   |-- qbpp_test_automation/              # Skill 6: RPA - Biztositasi kalkulátor teszt
|   |   |-- skill.yaml
|   |   |-- workflow.py
|   |   |-- agents/                         # registry_loader, data_generator, test_runner, analyzer
|   |   |-- config/                         # field_registry.json, test_strategies.json
|   |   |-- tests/
|
|-- deployments/                            # Ugyfél deployment profilok
|   |-- _shared/
|   |   |-- base-config.yaml
|   |-- allianz/
|   |   |-- deployment.yaml                 # Skill lista + instance-ok
|   |   |-- instances/
|   |   |   |-- hr_aszf_chat.yaml
|   |   |   |-- legal_aszf_chat.yaml
|   |   |-- k8s/
|   |       |-- kustomization.yaml
|   |-- cubix-edu/
|       |-- deployment.yaml
|       |-- instances/
|       |   |-- python_course.yaml
|       |-- k8s/
|           |-- kustomization.yaml
|
|-- templates/                              # Workflow sablonok
|   |-- small_linear/                       # 3-5 lepes, linearis
|   |   |-- workflow.py.j2
|   |   |-- step.py.j2
|   |   |-- test.py.j2
|   |-- medium_branching/                   # 5-15 lepes, elagazassal
|   |   |-- workflow.py.j2
|   |   |-- agents/
|   |   |-- prompts/
|   |-- large_orchestrated/                 # 15-50+ lepes, sub-workflow-ok
|       |-- workflow.py.j2
|       |-- sub_workflows/
|       |-- orchestrator.py.j2
|
|-- tests/                                  # Framework szintu tesztek
|   |-- ui/                                 # Playwright GUI tesztek
|   |   |-- conftest.py
|   |   |-- pages/                          # Page Object Model
|   |   |   |-- login_page.py
|   |   |   |-- dashboard_page.py
|   |   |   |-- chat_page.py
|   |   |-- test_login.py
|   |   |-- test_dashboard.py
|   |   |-- test_chat.py
|   |-- unit/
|   |   |-- engine/
|   |   |   |-- test_step.py
|   |   |   |-- test_dag.py
|   |   |   |-- test_workflow.py
|   |   |   |-- test_runner.py
|   |   |   |-- test_policies.py
|   |   |-- agents/
|   |   |   |-- test_specialist.py
|   |   |   |-- test_quality_gate.py
|   |   |-- prompts/
|   |   |   |-- test_manager.py
|   |   |-- security/
|   |       |-- test_rbac.py
|   |       |-- test_auth.py
|   |-- integration/
|   |   |-- test_api.py
|   |   |-- test_queue.py
|   |   |-- test_state_store.py
|   |-- e2e/
|   |   |-- test_full_workflow.py
|   |-- conftest.py                         # Kozos fixtures
|
|-- docs/                                   # Dokumentacio
|   |-- getting-started.md
|   |-- architecture.md
|   |-- writing-workflows.md
|   |-- writing-skills.md
|   |-- writing-agents.md
|   |-- prompt-management.md
|   |-- deployment.md
|   |-- api-reference/
|   |-- claude-code-integration.md
|
|-- .github/
|   |-- workflows/
|       |-- ci.yml                          # Lint + Test + Build
|       |-- deploy-staging.yml
|       |-- deploy-prod.yml
```
