# AIFlow Development Roadmap — Eloremutatno Fejlesztesi Iranyok

> Utolso frissites: 2026-04-04 (Session 16)
> Cel: Azokat a technologiakat es fejlesztesi iranyokat tartja nyilvan, amelyek
> jelenleg NEM implementaltak, de **korszerusitesi, skalazhato vagy opcionals
> alternativat** jelentenek. Ezek NEM stub-ok — hanem tudatos, jovobeni lehetosegek.

---

## Uzenetkezeles es Event Streaming

### Apache Kafka integracio
- **Allapot:** Nincs implementalva (stub torolve v1.2.2-ben)
- **Jelenlegi megoldas:** In-memory `MessageBroker` (arq + Redis)
- **Mikor lesz szukseges:** Multi-node deployment, cross-service event streaming, audit trail
- **Technologia:** `aiokafka` (async Python Kafka kliens)
- **Komplexitas:** Kozepes — adapter reteg + config + consumer group management
- **Elofeltetelek:** Kubernetes/Docker Compose multi-node setup, Kafka cluster (Confluent/Strimzi)
- **Tervezett verzio:** v1.4.0+

---

## Titkositas es Secret Management

### HashiCorp Vault integracio
- **Allapot:** Interface letezik (`security/secrets.py:SecretProvider` ABC), Vault impl torolve
- **Jelenlegi megoldas:** `EnvSecretProvider` (kornyezeti valtozok)
- **Mikor lesz szukseges:** Multi-environment deployment, secret rotation, audit log
- **Technologia:** `hvac` Python kliens + Vault AppRole auth
- **Komplexitas:** Kozepes — CRUD + lease renewal + caching
- **Tervezett verzio:** v1.3.0+

---

## Megfigyeles es Monitoring

### Prometheus / OpenTelemetry Metrics
- **Allapot:** Nincs implementalva (placeholder torolve v1.2.2-ben)
- **Jelenlegi megoldas:** Langfuse (LLM observability), structlog (JSON logging)
- **Mikor lesz szukseges:** Infra-szintu monitoring (latency, throughput, error rates), Grafana dashboard
- **Technologia:** `prometheus_client` vagy `opentelemetry-sdk` + OTLP exporter
- **Komplexitas:** Alacsony-kozepes — counter/histogram dekoratorok + /metrics endpoint
- **Megjegyzes:** Langfuse az LLM-specifikus metrikakat mar kezeli; ez az infra reteg lenne
- **Tervezett verzio:** v1.3.0+

---

## CLI Bovitesek

### Prompt Lifecycle Management CLI
- **Allapot:** Nincs implementalva (CLI stubs torolve v1.2.2-ben)
- **Jelenlegi megoldas:** Langfuse UI + `npx promptfoo eval`
- **Mikor lesz szukseges:** CI/CD pipeline integracio, prompt versioning automation
- **Parancsok:** `aiflow prompt sync`, `aiflow prompt diff`, `aiflow prompt promote`
- **Tervezett verzio:** v1.3.0

### Workflow Execution CLI
- **Allapot:** Nincs implementalva (CLI stubs torolve v1.2.2-ben)
- **Jelenlegi megoldas:** Pipeline API (`/api/v1/pipelines/*/run`) + Admin UI
- **Mikor lesz szukseges:** Headless execution, cron job integracio, CLI scripting
- **Parancsok:** `aiflow workflow run`, `aiflow workflow inspect`, `aiflow workflow docs`
- **Tervezett verzio:** v1.3.0

### Evaluation CLI (Promptfoo wrapper)
- **Allapot:** Nincs implementalva (CLI stub torolve v1.2.2-ben)
- **Jelenlegi megoldas:** `npx promptfoo eval -c skills/*/tests/promptfooconfig.yaml`
- **Mikor lesz szukseges:** Egységes CLI élmeny, CI/CD integracio
- **Parancsok:** `aiflow eval run --skill <name>`, `aiflow eval report`
- **Tervezett verzio:** v1.3.0

---

## Dokumentum Feldolgozas

### Alternativ Parser-ek
- **Allapot:** Legacy pdf_parser.py es docx_parser.py torolve v1.2.2-ben
- **Jelenlegi megoldas:** `DoclingParser` (PDF, DOCX, XLSX, HTML — egységes interface)
- **Lehetseges bovitesek:**
  - **Azure Document Intelligence** — scan/OCR/handwriting (mar van adapter: `tools/azure_doc_intelligence.py`)
  - **Tesseract OCR** — offline OCR alternativa
  - **Unstructured.io** — komplex dokumentum layout parsing
- **Megjegyzes:** DoclingParser fedezi a jelenlegi use case-eket; bovites csak specifikus igeny eseten

---

## GraphRAG

### Microsoft GraphRAG / LazyGraphRAG
- **Allapot:** Tervezett (50_RAG_VECTOR_CONTEXT_SERVICE.md), nem implementalt
- **Jelenlegi megoldas:** pgvector hybrid search (HNSW + BM25 + RRF reranking)
- **Mikor lesz szukseges:** Komplex entitas-kapcsolat kerdesek, multi-hop reasoning
- **Technologia:** Microsoft `graphrag` Python csomag, Neo4j opcionals
- **Komplexitas:** Magas — graph extraction pipeline + index build + query engine
- **Tervezett verzio:** v1.4.0+

---

## Prioritasi Sorrend

| # | Fejlesztes | Ertek | Komplexitas | Tervezett |
|---|-----------|-------|-------------|-----------|
| 1 | Prometheus/OTel metrics | Magas (ops visibility) | Alacsony | v1.3.0 |
| 2 | CLI prompt/eval/workflow | Kozepes (DX) | Alacsony | v1.3.0 |
| 3 | Vault secret management | Magas (security) | Kozepes | v1.3.0 |
| 4 | Kafka event streaming | Magas (scale) | Kozepes | v1.4.0 |
| 5 | GraphRAG | Kozepes (advanced RAG) | Magas | v1.4.0 |
