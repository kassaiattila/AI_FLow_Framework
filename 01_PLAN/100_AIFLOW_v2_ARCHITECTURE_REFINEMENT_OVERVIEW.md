# AIFlow v2 — Architectural Refinement Overview

> **Verzio:** 2.0 (FINAL — ELFOGADVA)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — `103_*` 2. ciklus utan
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` (kezdd itt az olvasast!)
> **Szulo dokumentumok:**
> - `FEATURES.md` (v1.2.2 baseline feature list)
> - `01_ARCHITECTURE.md` (v1.0.0 framework architektura)
> - `58_POST_SPRINT_HARDENING_PLAN.md` (v1.3.0 Sprint A+B status)
> - `DEVELOPMENT_ROADMAP.md` (v1.3.0+ / v1.4.0+ opcionalis iranyok)
> - `document_pipeline.md` (multi-source intake target architektura)
> - `CrewAI_development_plan.md` (opcionalis bounded agentic layer)
> **Kiegeszito dokumentumok (kotelezo olvasmany):**
> - `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` (13 Pydantic contract)
> - `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` (7 entitas allapotgep)
> - `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` (backward compat + rolling deploy)
> **Reszletes komponens terv:** `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md`
> **Felulvizsgalati ciklusok:** `102_*` (1. ciklus) + `103_*` (2. ciklus, sign-off)
>
> **Valtozas naplo:**
> - **v2.0 (2026-04-09):** `103_*` sign-off elfogadva. Phase 1 bontas 1a/1b/1c/1.5-re (Section 7).
>   Hivatkozasok `100_b/c/d` + `103_*` szakaszokra bekotve. Section 4 provider/routing/isolation
>   frissitesei `103_` Section 4-6-ra mutatnak. Status "TERVEZET" → "ELFOGADVA".
> - **v1.0 (2026-04-08):** initial draft, ADR-1 (CrewAI core REJECTED) hozzaadva.

---

## 0. Vezetoi Osszefoglalo

Az AIFlow v1.2.2 (Sprint A COMPLETE) es v1.3.0 (Sprint B FOLYAMATBAN) egy mukodo,
production-szintu enterprise AI automation framework. A jelen terv **NEM ujraepiti**
a rendszert — a meglevo Step + Workflow + Pipeline + Service architekturat
**megtartja, kiterjeszti es megkemenyiti** a kovetkezo strategiai celok mente:

1. **Multi-source intake package model** — email + file + folder + free-text egysegben
2. **Single shared codebase, ket deployment profil**:
   - **Profile A** (Cloud-disallowed) — on-prem, air-gapped capable
   - **Profile B** (Cloud-allowed, Azure-optimized) — Azure DI/Search/OpenAI
3. **Provider abstraction & policy engine** — tenant-szintu cloud/PII/embedding kontroll
4. **Multi-signal parser routing** — gyors fast-path, deep-path, VLM hard-path
5. **Self-hosted AI stack** (BGE-M3 embedding, Qwen2.5-VL classification)
6. **PDF/A archival pipeline** (Gotenberg + veraPDF) — compliance-grade
7. **Optional bounded CrewAI agentic reasoning sidecar** — multi-source ambiguity
8. **Production-grade ops** — Vault, OTel/Prometheus, audit lineage

A terv 4 fazisra bontott:
- **Phase 1 — Critical corrections** (intake model + provider abstraction + policy engine)
- **Phase 2 — Architectural refinements** (parser routing + archival + embedding governance)
- **Phase 3 — Governance & operational hardening** (Vault, OTel, audit lineage, CrewAI)
- **Phase 4 — Optional optimizations** (GraphRAG, Kafka, multi-tenant SaaS)

A v1.3.0 (Sprint B) folyamatban van — a refinement Phase 1 a v1.4.0 sprint nyitva,
NEM blokkolja a jelen Sprint B befejezeset.

---

## 1. Baseline Interpretacio (v1.2.2 + folyamatban v1.3.0)

### 1.1 Mukodo komponensek (megorzendo magtanok)

| Reteg | Komponens | Allapot | Megorzes indoklas |
|-------|-----------|---------|------------------|
| Core | ExecutionContext + DI Container | Production | Az egesz framework idegrendszere |
| Core | Step + Workflow + DAG + Runner | Production | Bizonyitott, 1424 unit teszt |
| Core | Skill System (max 6 specialist) | Production | "Add state, add bugs" elvre tervezve |
| Pipeline | PipelineRunner + Compiler | Production | YAML→DAG, 21 adapter |
| Pipeline | 21 adapter (email, doc, classifier, ...) | Production | Provider-szeruen mar absztrakt |
| Storage | PostgreSQL + pgvector | Production | HNSW + BM25 + RRF mukodik |
| Storage | Redis + arq job queue | Production | At-least-once, prio queue, DLQ |
| Security | JWT RS256 (PyJWT) + bcrypt + RBAC | Production | A3 sprint hardening kesz |
| Security | Guardrails (Input/Output/Scope rule-based) | Production | A5 keretrendszer + B1 LLM layer |
| Observability | Langfuse v4 (LLM trace + prompt SSOT) | Production | Mukodik, central artifact |
| Observability | structlog + cost_tracker | Production | JSON logging, Per-step cost |
| Prompts | PromptManager (cache → Langfuse → YAML) | Production | Release-mentes prompt swap |
| Skill instances | skill_system/instance_*.py | Production | Multi-tenant alap (28_MOD_DEPLOY) |
| HITL | HumanReviewService + human_reviews tabla | Production | Kesz, B7 verification page koveti |
| Notification | NotificationService (email/Slack/webhook/in-app) | Production | Multi-channel, Jinja2 |
| Engine | Resilience: Retry + Circuit Breaker + Timeout | Production | Per-step policy |
| Quality | Quality Gates + threshold | Production | Per-workflow, dontes-pontok |

### 1.2 Reszben kesz (befejezendo) — kontextus a v1.3.0 Sprint B-bol

| Komponens | Jelen statusz | Soron kovetkezo lepes |
|-----------|--------------|----------------------|
| LLM Guardrail prompts (4 yaml) | B1 KESZ | per-skill testreszabas (B1.2) |
| Per-skill PII strategia | B0.1 KESZ + 61_GUARDRAIL_PII_STRATEGY.md | aktivalas (B1.2) |
| Service unit tesztek | B2 KESZ (130 teszt) | coverage gate >=70% |
| invoice_finder pipeline | B3 KESZ (E2E Phase 3 zol) | UI verification (B7) |
| Confidence scoring kalibracio | B3.5 KESZ (5-faktor minta) | per-field kiterjesztes mas skill-re |
| Skill hardening | B4.1 KESZ (aszf_rag, email_intent) | B4.2 (process_docs, invoice, cubix) |
| Docker container deploy | B9 NYITOTT | docker-compose.prod.yml + healthcheck |

### 1.3 Hianyzo / stub komponensek (jelen all stub-kent)

| Komponens | Jelen | Hatas | Roadmap helye |
|-----------|-------|-------|--------------|
| `VaultSecretProvider` | STUB (NotImplementedError) | Prod kornyezet ENV-bol kep `secrets.py:107-125` | DEVELOPMENT_ROADMAP v1.3.0+ |
| `prometheus-client` integracio | Dependency deklaralt, kod nincs | Nincs infra metrika, csak Langfuse LLM | DEVELOPMENT_ROADMAP v1.3.0+ |
| `opentelemetry-sdk` integracio | Dependency deklaralt, kod nincs | Nincs distributed tracing | DEVELOPMENT_ROADMAP v1.3.0+ |
| `GraphRAGService` | Modul letezik, impl stub | Multi-hop reasoning nincs | DEVELOPMENT_ROADMAP v1.4.0+ |
| Kafka adapter | Mar torolve (v1.2.2-ben) | Nincs cross-service event streaming | DEVELOPMENT_ROADMAP v1.4.0+ |
| `aiflow` CLI (prompt/eval/workflow) | Stub-okig levaglak v1.2.2 | Headless szuksegletek | DEVELOPMENT_ROADMAP v1.3.0 |

---

## 2. Tervezett Bovites — Strategiai Iranyok

A jelen terv harom independent forrasbol szintetizalt celarchitekturat hatarozza meg:

### 2.1 `document_pipeline.md` — Multi-source intake celarchitektura

A document_pipeline.md egy senior architect szempontjabol kerul a jelenlegi
rendszerre, **NEM redesign**, hanem refinement. Kulcs allitasok:

- A platform NEM csak email — szukseges altalanos **multi-source intake package model**
- **Fixed technologiai irany** (NE legyen helyettesites random alternativakkal):
  - Email: **Unstructured OSS** (egyseges EML/MSG/csatolmany/body context parser)
  - Fast PDF: **PyMuPDF4LLM** (gyors, GPU-mentes, nem univerzalis)
  - Structured: **Docling standard pipeline** (tartomany, OCR, layout)
  - Hard cases: **Docling VLM pipeline** + **vLLM** runtime
  - Self-hosted classifier: **Qwen2.5-VL-7B-Instruct** (vLLM-en keresztul)
  - Routing: **multi-signal routing engine**
  - Archival: **Gotenberg** (PDF/A) + **veraPDF** (validacio)
  - Metadata + vector: **PostgreSQL + pgvector** (megorzendo)
  - Self-hosted embedding: **BGE-M3** (primary), **multilingual-e5-large-instruct** (fallback)
  - Cloud parsing: **Azure Document Intelligence** (provider, NEM domain modell)
  - Cloud retrieval: **Azure AI Search** (provider, NEM domain modell)
  - Cloud embedding: **Azure OpenAI / Azure Foundry** (`text-embedding-3-large/small`)
- **Egyetlen kodbazis, ket profil**: A (cloud-disallowed) es B (cloud-allowed/Azure)
- **Policy engine**: `cloud_ai_allowed`, `pii_embedding_allowed`, ... — kotelezo elem

### 2.2 `DEVELOPMENT_ROADMAP.md` — Tudatos opcionalis iranyok

| # | Fejlesztes | Komplexitas | Becsult verzio |
|---|-----------|-------------|---------------|
| 1 | Prometheus / OTel infra metrics | Alacsony | v1.3.0/v1.4.0 |
| 2 | CLI bovitesek (prompt/eval/workflow) | Alacsony | v1.3.0 |
| 3 | Vault secret management (`hvac`) | Kozepes | v1.3.0/v1.4.0 |
| 4 | Kafka event streaming | Kozepes | v1.5.0+ |
| 5 | GraphRAG (Microsoft / LazyGraphRAG) | Magas | v1.4.0+ |

### 2.3 `CrewAI_development_plan.md` — Opcionalis bounded reasoning

CrewAI **opcionalisan**, **NEM core orchestrator**-kent. Hasznalhato:
- intake package interpretation
- file-to-description association (ambiguitas eseten)
- cross-document consistency reasoning
- low-confidence triage / review eloolaszitas
- operator/reviewer copilot

**Tilos hasznalat**:
- parser provider routing core
- archival conversion / PDF-A validacio
- policy enforcement / tenant boundary
- storage / metadata DB tranzakcio
- idempotens allapotkezeles
- compliance-kritikus state transition

**Architekturalis pozicio**: kulon agent service VAGY bounded module,
provider-szeru adapteren keresztul. A fo pipeline happy path CrewAI nelkul
is mukodjon. A CrewAI output mindig **strukturalt + validalt**, ervenytelenseg
eseten retry / fallback / manual review aktivalodik.

> A reszletes szakmai megfontolas — **miert NEM lehet a CrewAI az AIFlow core
> orchestratora** — az alabbi ADR-1 szekcioban talalhato.

---

## 2.A Architecture Decision Record — ADR-1: CrewAI mint core orchestrator (REJECTED)

> **Statusz:** ACCEPTED — 2026-04-08
> **Tipus:** Architecture Decision Record (ADR)
> **Dontes hozok:** Solution architect + lead Python platform engineer
> **Felulvizsgalat:** Phase 3 controlled experiment-ben szuksegseg eseten
> **Forras:** Felhasznaloi felvetesre (sprint koz uzleti megbeszeles)

### Kontextus

A `CrewAI_development_plan.md` forras dokumentum egy ELORE ROGZITETT iranymutatassal
erkezik: "CrewAI opcionalis bounded sidecar, NEM core orchestrator." Ezt a 100_ es 101_
dokumentumok elso valtozata kritikai vizsgalat nelkul atvette.

A felhasznalo kerese (2026-04-08): vizsgaljuk meg ujra, miert nem lehet a CrewAI
**alapveto driver / orchestrator** megoldas az AIFlow-ban, es indokoljuk meg a dontest.

Ez az ADR rögziti a vizsgalat menetet, az ervek matrixat es a vegleges dontest.

### Alternativak

| Alternativa | Leiras |
|------------|--------|
| **A**: AIFlow native (`Workflow + Step + DAG + Skill System`) | Megorzes — jelenlegi rendszer |
| **B**: CrewAI as core (`Crew + Tasks + Tools + Flows`) | Csere — CrewAI-vezerelt orchestracio |
| **C**: Hybrid (AIFlow core + CrewAI bounded sidecar) | A jelenlegi terv (101 N22) |
| **D**: Step-szintu opcionalis CrewAI adapter | Phase 3 controlled experiment, opt-in |

### Ertekelesi szempontok (15 architekturalis + 3 uzleti)

#### Architekturalis

| # | Szempont | Sulyozas | A: Native | B: CrewAI core | C: Hybrid | D: Step-opt-in |
|---|---------|---------|-----------|---------------|-----------|---------------|
| 1 | **Determinizmus** | KRITIKUS | EROS (DAG kontrollalt) | GYENGE (agentic randomness) | EROS | EROS |
| 2 | **Idempotencia + replay** | KRITIKUS | EROS (`WorkflowRunner.resume()` + checkpoint) | GYENGE (nincs natív replay) | EROS | EROS |
| 3 | **State management** | KRITIKUS | EROS (PostgreSQL ACID) | GYENGE (in-memory + SQLite) | EROS | EROS |
| 4 | **DAG validation** | MAGAS | EROS (build-time topological sort + cycle) | GYENGE | EROS | EROS |
| 5 | **Type safety** | MAGAS | EROS (Pydantic everywhere) | KOZEPES (lazább) | EROS | EROS |
| 6 | **Compliance audit / lineage** | KRITIKUS (Profile A) | EROS (per-step + N17 lineage) | GYENGE (agent reasoning kodos) | EROS | EROS |
| 7 | **Cost predictability** | MAGAS | EROS (`BudgetExceededError`) | GYENGE (multi-LLM ciklus) | EROS | EROS |
| 8 | **Latency contract / SLA** | MAGAS | EROS (per-step monitoring) | GYENGE (multi-agent overhead) | EROS | EROS |
| 9 | **Resilience policies** | MAGAS | EROS (retry/CB/timeout per step) | KOZEPES | EROS | EROS |
| 10 | **Resource management** | MAGAS | EROS (JobQueue prio + DLQ) | GYENGE (nincs hasonló) | EROS | EROS |
| 11 | **Provider abstraction** | KRITIKUS (Phase 1) | EROS (21 adapter, R15) | KOZEPES (Tools modell) | EROS | EROS |
| 12 | **Quality Gates** | MAGAS | EROS (formalizalt) | GYENGE (ad-hoc) | EROS | EROS |
| 13 | **HITL integration** | MAGAS | EROS (HumanReviewService + tabla) | GYENGE | EROS | EROS |
| 14 | **Observability (Langfuse)** | MAGAS | EROS (integralva) | KOZEPES (saját trace, parhuzamos) | EROS | EROS |
| 15 | **Multi-agent reasoning** | KOZEPES (csak 5 use case) | KOZEPES (Skill System max 6) | EROS (natív) | EROS (sidecar) | KOZEPES |

#### Uzleti / projekt

| # | Szempont | Sulyozas | A: Native | B: CrewAI core | C: Hybrid | D: Step-opt-in |
|---|---------|---------|-----------|---------------|-----------|---------------|
| 16 | **Migracios koltseg** | KRITIKUS | 0 | NAGYON MAGAS (~6+ honap, 1424 unit teszt rewrite) | ALACSONY (sidecar) | ALACSONY |
| 17 | **Sprint B blokkolas (v1.3.0)** | KRITIKUS | NEM | IGEN (deadline csuszas) | NEM | NEM |
| 18 | **Compliance kockazat (Profile A)** | KRITIKUS | NINCS (auditor accept) | MAGAS (auditor szamara opaque agentic dontesek) | NINCS | NINCS |

### Score osszeg (5/strong, 3/medium, 1/weak)

| Alternativa | Architekturalis (15) | Uzleti (3) | Total | Megjegyzes |
|------------|---------------------|-----------|-------|------------|
| **A: Native** | 14 EROS, 1 KOZEPES = **73** | 3 EROS = **15** | **88** | A jelenlegi alap |
| **B: CrewAI core** | 1 EROS, 4 KOZEPES, 10 GYENGE = **27** | 0 EROS = **3** | **30** | Migracios kockazat tul magas |
| **C: Hybrid** | 14 EROS, 1 EROS = **75** | 3 EROS = **15** | **90** | A 101 N22 javasolt |
| **D: Step-opt-in** | 14 EROS, 1 KOZEPES = **73** | 3 EROS = **15** | **88** | Phase 3 experiment |

### Dontes

> **ELFOGADVA: A + C kombinacio (Hybrid)**
>
> 1. **Az AIFlow core orchestratora MARAD a Step + Workflow + DAG + Skill System architektura.**
>    Az `WorkflowRunner` a determinisztikus, idempotens, audit-keszhetetlen vegrehajtasi
>    motor — KRITIKUS a Profile A compliance + Profile B production-grade SLA-ra.
>
> 2. **A CrewAI bounded reasoning sidecar (N22) megorzendo** — Phase 3-ban.
>    5 elore definialt use case-re, strukturalt I/O contracts-szel, fail-safe fallback-kel.
>
> 3. **Phase 3-ban controlled experiment** (D alternativa step-opt-in) indul:
>    Ket darab Skill System specialist (`ClassifierAgent`, `ExtractorAgent`)
>    OPCIONALIS CrewAI Crew adapterrel mernek A/B-ben:
>    - control: AIFlow native specialist (jelenlegi)
>    - treatment: CrewAI Crew-alapu specialist (uj)
>    Metrika: confidence, latency, cost, accuracy, hallucinacio rate
>    Dontes: HA a CrewAI varians min 10%-kal jobb es min 50%-kal nem dragabb,
>    akkor opcionalisan engedelyezett a step-szintu csere — DE
>    a Workflow + Pipeline core MARAD.
>
> 4. **NEM kerul sor a teljes core csereere.** Az `WorkflowRunner`, `PipelineRunner`,
>    `JobQueue`, `Skill System`, `HumanReviewService` MIND megorzendo.

### Indoklas (rovid)

A B alternativa elutasitasanak harom kritikus oka:

1. **Compliance / Profile A blokkolja**: az air-gapped, regulalt iparag deployment NEM
   TURI az opaque agentikus donteseket. Az `Workflow + Step + DAG` formalis modellje
   audit-keszhetelen, a CrewAI multi-agent reasoning **nem**.

2. **Migracios kockazat tul magas**: 1424 unit teszt + 104 E2E rewrite = ~6+ honap
   munka, magas regression risk, Sprint B (v1.3.0) deadline csuszas, ugyfél bizalmi
   kockazat. Az AIFlow mar mukodik production-ban.

3. **A CrewAI ertekei NEM core orchestratorhoz kotodnek**: az agentikus reasoning,
   multi-agent kollaboracio, knowledge management — ezek SIDECAR / SPECIALIST szinten
   ervenyesulnek. Core orchestratorhoz determinizmus kell, NEM agentikus reasoning.

### Mikor erdemes ujra felulvizsgalni?

- **HA** Phase 3 controlled experiment azt mutatja, hogy a CrewAI step-szintu adapter
  >10% jobb minoseggel + <50% drágább latency/cost-tal mukodik, **ÉS**
- **HA** a CrewAI ekkor mar tamogatja az idempotens replay + ACID state-et, **ÉS**
- **HA** megengedett egy uj sprint (>= v2.0.0) a teljes architektura ujragondolasara,
- **AKKOR** a B alternativa ujra felulvizsgalando — de mar nem core csere, hanem
  parhuzamos orchestrator opcio (`AIFlowOrchestrator` ill. `CrewAIOrchestrator`
  vegrehajtasi backend valasztast bevezetni a `pipeline/runner.py`-ban).

Ez a forgatokony **NEM blokkol jelenleg** semmit — a Hybrid (A+C) optimal a v1.4.0 → v2.0.0 sprintre.

### Kapcsolodo komponensek

- Lasd: `101_*.md` N22 — `agents/crewai_sidecar/CrewAIBoundedReasoningService`
- Phase 3 experiment terve: `103_*.md` (sign-off ciklusban reszletezve)

---

## 3. Cel Architektura — Madartavlat

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AIFlow v2 — Cel Architektura                     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ INTAKE LAYER (UJ)                                                │   │
│  │  ┌────────────┐ ┌────────────┐ ┌───────────┐ ┌──────────────┐   │   │
│  │  │ Email      │ │ File upload│ │ Folder /  │ │ Batch / API  │   │   │
│  │  │ (Unstruct.)│ │ (UI/CLI)   │ │ Object st.│ │ (S3/SharePt) │   │   │
│  │  └─────┬──────┘ └─────┬──────┘ └─────┬─────┘ └──────┬───────┘   │   │
│  │        └──────────────┴──────────────┴──────────────┘           │   │
│  │                          ▼                                       │   │
│  │           ┌────────────────────────────┐                         │   │
│  │           │  Source Adapter Layer      │                         │   │
│  │           │  (provider-szeru iface)    │                         │   │
│  │           └────────────┬───────────────┘                         │   │
│  │                        ▼                                          │   │
│  │           ┌────────────────────────────┐                         │   │
│  │           │  Intake Normalization      │                         │   │
│  │           │  + IntakePackage model     │                         │   │
│  │           │  + File ↔ Description map  │                         │   │
│  │           │  + Package context         │                         │   │
│  │           └────────────┬───────────────┘                         │   │
│  └────────────────────────┼─────────────────────────────────────────┘   │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ POLICY + PROVIDER LAYER (UJ)                                     │   │
│  │  ┌─────────────────┐ ┌────────────────┐ ┌─────────────────────┐  │   │
│  │  │ Policy Engine   │ │ Provider Reg.  │ │ Tenant Override     │  │   │
│  │  │ - cloud_allowed │ │ - parser       │ │ - per-tenant config │  │   │
│  │  │ - pii_embed     │ │ - classifier   │ │ - feature flags     │  │   │
│  │  │ - archival      │ │ - extractor    │ │ - fallback order    │  │   │
│  │  │ - default prov. │ │ - embedder     │ │                     │  │   │
│  │  └─────────────────┘ └────────────────┘ └─────────────────────┘  │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ ROUTING + PARSER LAYER (REFINED)                                 │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │  Multi-Signal Routing Engine                                │  │   │
│  │  │  signals: file_type, text_layer, OCR_need, image_dom,      │  │   │
│  │  │           table_susp, layout_complex, page_var,            │  │   │
│  │  │           pkg_ctx, src_text, tenant_policy, provider_avail,│  │   │
│  │  │           fallback_order                                    │  │   │
│  │  └─────────┬──────────────────────────────────────────────────┘  │   │
│  │            ▼                                                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌─────────────┐ ┌─────────────┐  │   │
│  │  │ PyMuPDF4LLM│ │ Docling Std│ │ Docling VLM │ │ Azure DI    │  │   │
│  │  │ (fast)     │ │ (default)  │ │ + vLLM      │ │ (Profile B) │  │   │
│  │  └────────────┘ └────────────┘ └─────────────┘ └─────────────┘  │   │
│  │                                       │                          │   │
│  │                                       ▼                          │   │
│  │                              ┌────────────────┐                  │   │
│  │                              │ Qwen2.5-VL-7B  │                  │   │
│  │                              │ visual classif │                  │   │
│  │                              │ + boundary det │                  │   │
│  │                              └────────────────┘                  │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ EXTRACTION + REASONING LAYER (REFINED)                           │   │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │   │
│  │  │ Field Extraction │ │ Boundary Detect  │ │ Schema Mgmt      │  │   │
│  │  │ (per-doc-type)   │ │ + Page Grouping  │ │ (versioned)      │  │   │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │ Confidence Layer (B3.5 mintat altalanositja)               │  │   │
│  │  │ - per-field, kalibralt, rule-based + ML + LLM blend        │  │   │
│  │  │ - confidence → routing (auto / review / reject)            │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────────────────┐  │   │
│  │  │ CrewAI Bounded Reasoning Sidecar (OPCIONALIS Phase 3)      │  │   │
│  │  │ - intake package interp / association / cross-doc reason   │  │   │
│  │  │ - structured output (Pydantic), validalt + audit           │  │   │
│  │  └────────────────────────────────────────────────────────────┘  │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ ARCHIVAL + STORAGE LAYER (REFINED)                               │   │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │   │
│  │  │ Gotenberg PDF/A  │ │ veraPDF Validate │ │ Object Storage   │  │   │
│  │  │ (UJ)             │ │ (UJ — explicit)  │ │ (local / S3 / Az)│  │   │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘  │   │
│  │  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐  │   │
│  │  │ Embedding Gate   │ │ Embedder         │ │ Vector Store     │  │   │
│  │  │ - PII redact     │ │ - BGE-M3 (A)     │ │ - pgvector (A)   │  │   │
│  │  │ - policy check   │ │ - e5-large (FB)  │ │ - Az.AI Search(B)│  │   │
│  │  │                  │ │ - Az.OpenAI (B)  │ │                  │  │   │
│  │  └──────────────────┘ └──────────────────┘ └──────────────────┘  │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ ORCHESTRATION + HITL LAYER (KEEP)                                │   │
│  │  - WorkflowRunner (DAG, checkpoint, resume, idempotency)         │   │
│  │  - JobQueue (arq + Redis prio)                                    │   │
│  │  - HumanReviewService + human_reviews tabla                       │   │
│  │  - NotificationService (multi-channel)                            │   │
│  │  - Quality Gates + budget enforcement                             │   │
│  │  - opt: LangGraph-compatible state machine adapter (Phase 3)      │   │
│  └────────────────────────┬─────────────────────────────────────────┘   │
│                           ▼                                              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ OBSERVABILITY + GOVERNANCE (REFINED)                             │   │
│  │  - Langfuse (LLM trace + prompt SSOT) — KEEP                     │   │
│  │  - structlog (JSON logging) — KEEP                                │   │
│  │  - Prometheus / OTel infra metrics + traces — UJ                  │   │
│  │  - Vault secret manager (production hvac) — UJ                    │   │
│  │  - Audit lineage (file→derivative→extraction→embedding) — UJ      │   │
│  │  - Provenance map (file ↔ description ↔ package) — UJ             │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Komponensek — Megtartas / Refinement / Csere / Hozzaadas

> Reszletes komponens-szintu indoklast es vegrehajtasi tervet a `101_*.md` tartalmaz.

### 4.1 MEGORZENDO (NO CHANGE)

| # | Komponens | Indoklas |
|---|-----------|----------|
| 1 | ExecutionContext + DI Container | Bizonyitott magkomponens, mindenen atfoly |
| 2 | Step + Workflow + DAG + Runner | 1424 unit teszt, kompiler+resume |
| 3 | Skill System (max 6 specialist) | Tudatos design constraint |
| 4 | PipelineRunner + Compiler | YAML→DAG, mar absztrakt |
| 5 | PostgreSQL + pgvector | Fixed irany, hybrid search mukodik |
| 6 | Redis + arq job queue | Fixed irany, prio + DLQ |
| 7 | JWT RS256 + bcrypt + RBAC | A3-ban hardenizalt |
| 8 | PromptManager (cache→Langfuse→YAML) | Release-mentes prompt swap |
| 9 | NotificationService | Multi-channel, mukodo |
| 10 | HumanReviewService + tabla | HITL kesz, B7 koveti |
| 11 | Resilience (retry / CB / timeout) | Per-step policy |
| 12 | Quality Gates + budget enforcement | Mukodo, dontespont |
| 13 | structlog JSON logging | Mukodo, observability alapja |
| 14 | Langfuse v4 (LLM trace + prompt SSOT) | Fixed irany |
| 15 | DoclingParser (mint **standard** parser) | Megorzendo, **multi-parser routing** ala kerul |
| 16 | Azure DI (mint **provider**, nem default) | Fixed irany, Profile B-ben opcio |

### 4.2 REFINEMENT (modositas/kiterjesztes meglevo komponenseken)

| # | Komponens | Aktualis | Cel | Indoklas |
|---|-----------|----------|-----|----------|
| R1 | `services/email_connector` (IMAP/Outlook COM) | Csak vegfelhasznalo email | Csak **egy** source adapter, az **Unstructured OSS-alapu** elsodleges email source mar uj | Multi-source intake; Unstructured egysegesen kezel EML/MSG/body/csatolmany — `document_pipeline.md` rogzitett irany |
| R2 | `ingestion/parsers/docling_parser.py` | Egyetlen univerzalis | A **multi-signal routing engine** alkomponensei kozul a "Docling standard" path | NEM csere — DoclingParser marad, csak nem default-as-only |
| R3 | `tools/azure_doc_intelligence.py` | Hardcoded fallback Docling-bol | Provider Registry-ben generikus parser provider | Tenant override, policy alapu valasztas |
| R4 | `services/document_extractor` | Document-centric | **Intake Package centric** + cross-document context | A baseline "package interpretation" elvarasa |
| R5 | `services/rag_engine` (embedding hardcoded `text-embedding-3-small`) | Egyetlen embedder | **Embedder provider abstraction** (BGE-M3 / Azure OpenAI / fallback) + redaction gate | Profile A nem engedelyez cloud embeddinget; PII embedding policy |
| R6 | `services/classifier` (ML+LLM hybrid) | Text alapu hibrid | + **VLM-alapu osztalyozasi opcio** (Qwen2.5-VL via vLLM) hard cases-re | Visual / scan / handwriting cases |
| R7 | `services/data_router` | Pipeline output filter | **Bovitett szabaly-alapu routing** + intake package context | Cross-document context handling |
| R8 | `security/secrets.py` (`VaultSecretProvider` STUB) | NotImplementedError | **Production `hvac`-alapu Vault provider** | DEVELOPMENT_ROADMAP v1.3.0+, prod-readiness |
| R9 | `observability/cost_tracker.py` (csak LLM koltseg) | Per-step LLM cost | + **Infra metrics (Prometheus / OTel)** | Fixed irany — DEVELOPMENT_ROADMAP v1.3.0+ |
| R10 | `observability/tracing.py` (csak Langfuse) | LLM trace | + **OTel distributed trace** | Fixed irany — multi-service tracing |
| R11 | `services/quality` | Eval metrics | + **Confidence calibration layer** (B3.5 minta kiterjesztese minden skill-re) | B3.5 lecserelte a ad-hoc confidence-eket; ezt altalanositani kell |
| R12 | `pipeline/builtin_templates/invoice_automation_v2.yaml` | Email→szamla pipeline | Pelda **multi-source intake package** pipeline (file upload + email + folder import) | Az osszes pipeline template at kell allitani intake package kontextusra |
| R13 | `skill_system/instance_*.py` | Multi-instance per skill | + **Tenant-szintu policy override** (cloud_allowed, embedding policy, ...) | Profile A vs B + policy engine kotes |
| R14 | `guardrails/` (Input/Output/Scope + LLM) | Per-skill guardrail config | + **PII redaction gate az embedding elott** | Embedding governance |
| R15 | `pipeline/adapters/*` (21 adapter) | Adapter per service | Egyseges **provider interface contract** (parser/classifier/extractor/embedder) | Provider registry, policy-driven valasztas |

### 4.3 UJ KOMPONENSEK (greenfield modulok)

| # | Komponens | Cel | Profile A | Profile B | Phase |
|---|-----------|-----|-----------|-----------|-------|
| N1 | `intake/package.py` — `IntakePackage` model | Multi-source intake unified domain entity | Kotelezo | Kotelezo | 1 |
| N2 | `intake/source_adapters/` — Email/File/Folder/Batch/API | Provider-szeru source absztrakcio | Kotelezo | Kotelezo | 1 |
| N3 | `intake/normalization.py` — IntakeNormalizationLayer | File → IntakePackage normalizacio | Kotelezo | Kotelezo | 1 |
| N4 | `intake/association.py` — File ↔ Description linker | Free-text + file kapcsolat (rule + LLM) | Kotelezo | Kotelezo | 1 |
| N5 | `policy/engine.py` — `PolicyEngine` | `cloud_ai_allowed`, `pii_embedding_allowed`, ... runtime check | Kotelezo | Kotelezo | 1 |
| N6 | `providers/registry.py` — `ProviderRegistry` + `ProviderInterface` | parser/classifier/extractor/embedder provider valaszto | Kotelezo | Kotelezo | 1 |
| N7 | `routing/multi_signal_router.py` — `MultiSignalRoutingEngine` | parser path valasztas (PyMuPDF4LLM/Docling/VLM/Azure DI) | Kotelezo | Kotelezo | 2 |
| N8 | `ingestion/parsers/pymupdf4llm_parser.py` — `PyMuPDF4LLMParser` | Born-digital PDF fast-path | Kotelezo | Opcio | 2 |
| N9 | `ingestion/parsers/docling_vlm_parser.py` — `DoclingVLMParser` | Hard-case parser via Docling VLM + vLLM | Kotelezo | Opcio | 2 |
| N10 | `services/visual_classifier/` — `Qwen25VLClassifier` | Self-hosted visual classification + boundary detection | Kotelezo | Opcio | 2 |
| N11 | `archival/gotenberg_adapter.py` — `GotenbergArchivalAdapter` | PDF → PDF/A konvertalas | Kotelezo (compliance) | Kotelezo (compliance) | 2 |
| N12 | `archival/verapdf_validator.py` — `VeraPDFValidator` | PDF/A explicit validacio (NEM assumalt) | Kotelezo (compliance) | Kotelezo (compliance) | 2 |
| N13 | `embeddings/bge_m3_provider.py` — `BGEM3EmbeddingProvider` | Self-hosted embedding | Kotelezo | Opcio (fallback) | 2 |
| N14 | `embeddings/e5_large_provider.py` — `E5LargeEmbeddingProvider` | Self-hosted fallback embedding | Opcio | Opcio | 2 |
| N15 | `embeddings/azure_openai_provider.py` — `AzureOpenAIEmbeddingProvider` | Cloud embedding (Profile B) | TILOS | Kotelezo | 2 |
| N16 | `embeddings/redaction_gate.py` — `EmbeddingRedactionGate` | PII redact / mask before embedding | Kotelezo | Kotelezo | 2 |
| N17 | `audit/lineage.py` — `LineageTracker` | file → derivative → extraction → embedding lineage | Kotelezo | Kotelezo | 3 |
| N18 | `provenance/map.py` — `ProvenanceMap` | file ↔ description ↔ package mapping | Kotelezo | Kotelezo | 3 |
| N19 | `observability/otel_tracer.py` — `OTelTracer` | OpenTelemetry distributed tracing | Kotelezo | Kotelezo | 3 |
| N20 | `observability/prometheus_metrics.py` — `PrometheusMetrics` | Infra metric exporter | Kotelezo | Kotelezo | 3 |
| N21 | `security/vault_provider_impl.py` — `VaultSecretProviderImpl` | hvac-alapu prod impl (a STUB ledobasa) | Kotelezo (prod) | Kotelezo (prod) | 3 |
| N22 | `agents/crewai_sidecar/` — `CrewAIBoundedReasoningService` | Opcionalis bounded reasoning sidecar | Opcio | Opcio | 3 |
| N23 | `cli/aiflow.py` — typer CLI bovites (prompt/eval/workflow) | Headless CLI hasznalat | Opcio | Opcio | 3 |
| N24 | `services/graph_rag/microsoft_lazygraphrag.py` — `LazyGraphRAGAdapter` | Multi-hop reasoning | Opcio | Opcio | 4 |
| N25 | `messaging/kafka_adapter.py` — `KafkaEventBus` | Cross-service event streaming | Opcio | Opcio | 4 |

### 4.4 KIVALTANDO ELEMEK (kiveheto / lecserelheto)

> A "kivaltando" itt **NEM toroles**, hanem **lecserelt szerep**: az adott komponens egy
> uj absztrakcio melle kerul, vagy el-veri annak a hasznalata az uj fo path-ban.

| # | Kivaltando elem | Kivaltja | Indoklas | Akcio |
|---|----------------|----------|----------|-------|
| K1 | `email_connector` IMAP/Outlook COM **kozvetlen** hasznalata pipeline-okban | `intake/source_adapters/email_source.py` (Unstructured OSS) | Multi-source unified intake; Unstructured az **egysegitett** EML/MSG parser | Email connector marad mint LOW-LEVEL **fetcher**, az **intake source adapter** wrappeli |
| K2 | `DoclingParser` mint **default univerzalis** parser | `routing/multi_signal_router.py` valasztja PyMuPDF4LLM / Docling / VLM / Azure DI kozul | Egyetlen parser nem optimalis minden esetre (sebesseg, OCR, layout) | DoclingParser marad — `Docling standard pipeline` reteg |
| K3 | `tools/attachment_processor.py` 3-retegu hardcoded routing (Docling→Azure→pypdfium2) | `routing/multi_signal_router.py` (multi-signal, policy-driven) | Hardcoded routing nem audit-friendly, nem profile-aware | AttachmentProcessor mar megorzendo, refactor a routing engine adapterrei |
| K4 | `text-embedding-3-small` hardcoded a `rag_engine`-ben | `embeddings/` provider abstraction | Profile A nem engedelyez cloud embeddinget | rag_engine `embedder=` parameter, registry-bol jon |
| K5 | `VaultSecretProvider` STUB (`security/secrets.py:107-125`) | `security/vault_provider_impl.py` hvac-alapu | Production-ready secret management, DEVELOPMENT_ROADMAP v1.3.0+ | STUB toroles uj impl letehet utan |
| K6 | Manualis "auto" parser dontes a `parser_factory.py`-ben | `routing/multi_signal_router.py` audit-trail-lel | Routing dontesnel kotelezo `RoutingDecision` rekord (signals + selected + reason) | parser_factory megorzendo mint factory, de routing engine fel hivja |
| K7 | Per-pipeline-template hardcoded `azure_enabled: true/false` | `policy/engine.py` + `tenant_override` | Tenant-szintu cloud allowed flag a policy-bol jon, NEM YAML template-bol | YAML template-ek `policy_aware: true` jelolessel, runtime felulir |
| K8 | `prometheus-client` deklaralt dep, **kod nincs** | `observability/prometheus_metrics.py` impl | Vagy hasznalod, vagy ledobod (stub-cleanup elv: 0 nem-tudatos stub) | Implementacio Phase 3 |
| K9 | `opentelemetry-sdk` deklaralt dep, **kod nincs** | `observability/otel_tracer.py` impl | Ugyanaz mint K8 | Implementacio Phase 3 |
| K10 | `services/graph_rag/` STUB | Phase 4-ben Microsoft LazyGraphRAG VAGY ledobas | Stub-cleanup elv | Phase 4 dontes |
| K11 | `cli/` szubmodul stub-jai (prompt/eval/workflow) | Tenyleges typer-alapu CLI vagy ledobas | Stub-cleanup elv (DEVELOPMENT_ROADMAP v1.3.0) | Phase 3 |
| K12 | Hardcoded confidence kuszobok a service-ekben (`>0.90 auto`, `>0.70 review`, `<0.50 reject`) | `services/quality/confidence_calibration.py` (B3.5 minta) + per-skill config | B3.5 mar megerositette: LLM self-report megbizhatatlan, per-field kell | B3.5 minta kiterjesztese minden skill-re |
| K13 | `pdf_parser.py`, `docx_parser.py` legacy stub-ok (mar v1.2.2-ben torolve) | `DoclingParser` + uj parserek | Mar megtortent | Megerositendo, hogy a torles stabil |

---

## 5. Single-Codebase + Two-Profile Elve

### 5.1 Profil definiciok

| Profile | Cloud AI | Cloud Storage | Document content | Embedding | Use case |
|---------|----------|---------------|------------------|-----------|----------|
| **A** | `cloud_ai_allowed=false` | `cloud_storage_allowed=false` | NEM hagyhatja el a tenant-et | Self-hosted ONLY (BGE-M3 / e5) | Air-gapped, on-prem, regulalt iparag |
| **B** | `cloud_ai_allowed=true` | `cloud_storage_allowed=true` | Lehet (Azure tenant) | Self-hosted **vagy** Azure OpenAI | Azure-tenant ugyfél, cost-optimized |

### 5.2 Hibrid kombinaciok (Profile B-n belul)

A Profile B nem "minden cloud" — tenant override-tal hibrid kombinaciok lehetsegesek:
- Azure parsing + self-hosted embedding (PII miatt)
- self-hosted parsing + Azure search (kis collection, gyors retrieval)
- Azure parsing + Azure search + embedding **disabled** PII-re

### 5.3 Egyetlen kodbazis

- **Kozos core**: minden komponens a `src/aiflow/`-ban van — NINCS ket repo, NINCS fork
- **Provider interfaces**: minden cloud/self-hosted komponens **kozos interface**-t implementál
- **Provider adapters**: konkret implementacio (BGE-M3 ill. Azure OpenAI ugyanazt az embedder interface-t)
- **Policy engine**: runtime dontesi pont, NEM build-time
- **Config profiles**: `config/profiles/profile_a.yaml` + `config/profiles/profile_b.yaml`
- **Tenant override**: `instances/{customer}/policy.yaml` felulirja a profile defaults-et
- **Feature flags**: env var / config kapcsolok funkciokra (`AIFLOW_FEATURE_VLM_PARSER=true`)
- **Deployment composition**: Docker Compose VAGY K8s overlay-ek (NEM kulonbozo image-ek)
- **No-code-fork rule**: TILOS `if profile == "a": import x_self ; else: import x_cloud` patternek a business logic-ban — provider interface-en kell jonnie

---

## 6. Policy Parameterek (kotelezo)

> Reszletes `meaning / allowed values / default / consumer / mandatory / pipeline impact` lista
> a `101_*.md`-ben. Itt csak a kotelezo parameter-szet:

```yaml
# config/profiles/profile_a.yaml (Cloud-disallowed default)
policy:
  cloud_ai_allowed: false                      # CSAK Profile B-ben true
  cloud_storage_allowed: false                 # CSAK Profile B-ben true
  document_content_may_leave_tenant: false     # Profile A: false
  embedding_enabled: true                       # opcionalis
  pii_embedding_allowed: false                  # ALAPERT: false
  self_hosted_parsing_enabled: true             # Profile A: true
  azure_di_enabled: false                       # Profile A: TILOS
  azure_search_enabled: false                   # Profile A: TILOS
  azure_embedding_enabled: false                # Profile A: TILOS
  archival_pdfa_required: true                  # compliance default
  pdfa_validation_required: true                # explicit veraPDF
  manual_review_confidence_threshold: 0.70      # B3.5 mintat altalanositja
  default_parser_provider: docling_standard     # routing engine kapja
  default_classifier_provider: hybrid_ml_llm    # vagy qwen25_vl
  default_extractor_provider: llm_field_extract # vagy regex / hibrid
  default_embedding_provider: bge_m3            # Profile A
  vector_store_provider: pgvector               # Profile A
  object_store_provider: local_fs               # vagy s3_compat
  tenant_override_enabled: true                 # multi-tenant
  fallback_provider_order:
    parser:
      - pymupdf4llm
      - docling_standard
      - docling_vlm
    embedder:
      - bge_m3
      - e5_large
  docling_vlm_enabled: true                     # GPU eseten true
  qwen_vllm_enabled: true                       # GPU eseten true
  self_hosted_embedding_model: BAAI/bge-m3
  azure_embedding_model: ""                      # Profile A: ures
  redaction_before_embedding_required: true     # PII gate
  source_adapter_type: unified                  # multi-source intake
  intake_package_enabled: true                  # multi-source unified
  source_text_ingestion_enabled: true           # free-text + case desc.
  file_description_association_mode: rule_first_llm_fallback
  package_level_context_enabled: true
  cross_document_context_enabled: true

# config/profiles/profile_b.yaml (Cloud-allowed Azure-optimized)
policy:
  cloud_ai_allowed: true
  cloud_storage_allowed: true
  document_content_may_leave_tenant: true
  azure_di_enabled: true
  azure_search_enabled: true
  azure_embedding_enabled: true
  default_parser_provider: docling_standard     # mar van Azure DI mint provider
  default_embedding_provider: azure_openai_embedding_3_small
  azure_embedding_model: text-embedding-3-small
  vector_store_provider: pgvector               # vagy azure_ai_search
  object_store_provider: azure_blob
  pii_embedding_allowed: false                  # alapert ITT IS false
  redaction_before_embedding_required: true
  # ... a tobbi orokli a profile_a defaultot vagy ezeken felul aktivalt
```

---

## 7. Fazis Tervezes — Prioritas Sorrend

> A folyamatban levo Sprint B (v1.3.0) **NEM blokkolodik** a refinement tervtol.
> Sprint B csak a meglevo komponensekre epul, a refinement v1.4.0 sprint-tel kezdodik.

### Phase 1 — Critical corrections (v1.4.0 - v1.4.5 cel)

> **FONTOS:** A Phase 1 bontasa (1a / 1b / 1c / 1.5) a `103_*` Section 3-ban reszletesen
> megtalalhato. Itt csak az osszefoglalot tartjuk — **a 103 a definitive**.

**Cel**: Multi-source intake + provider abstraction + policy engine + Profile A production-ready.

**Bontas 4 alfazisra** (a 102_* 1. ciklus MF4 kovetkeztetese alapjan):

| Sprint | Verzio | Cel |
|--------|--------|-----|
| **Phase 1a** | v1.4.0 | **Foundation** — IntakePackage (N1), state machine, PolicyEngine (N5, 30+ parameter), ProviderRegistry (N6, 4 ABC), tenant override (R13), `100_b/c` contractok + `100_d` backward compat shim, alembic 030-031 |
| **Phase 1b** | v1.4.1 | **Source adapters** — 5 source adapter (N2: email/file/folder/batch/api), File ↔ Description association (N4), `POST /api/v1/intake/upload-package` endpoint |
| **Phase 1c** | v1.4.2 | **Refactor + acceptance** — R4 document_extractor IntakePackage centric, R12 multi-source pipeline pelda, R15 adapter provider parameter, UI multi-file upload, 10 processing flow E2E (`document_pipeline.md` Section 8), alembic 033 |
| **Phase 1.5** | v1.4.5 | **Profile A production-ready** — Vault prod impl (R8/N21, `hvac`), self-hosted Langfuse, Profile A air-gapped E2E |

**Phase 1 acceptance** (lasd reszletes checklist `103_*` Section 9):
- [ ] IntakePackage modell betoltheto email + file + folder + free-text intake-bol
- [ ] Policy engine eldonti a provider valasztast minden pipeline-ban
- [ ] Profile A teljes pipeline (invoice_finder, advanced_rag_ingest) cloud nelkul fut
- [ ] Profile B ugyanaz a pipeline cloud-osan is fut, NEM modositott YAML-tal
- [ ] 0 hardcoded `if profile == "a"` pattern (CI lint ellenorizi)
- [ ] 10 processing flow E2E PASS
- [ ] Profile A air-gapped Vault + self-hosted Langfuse deploy mukodik
- [ ] Customer zero-downtime migracio backward compat shim-mel

### Phase 2 — Architectural refinements (v1.5.0 cel)

**Cel**: Multi-signal parser routing + archival + embedding governance + visual classifier.

| # | Feladat | Komponensek | Becsules |
|---|---------|------------|----------|
| P2.1 | `routing/multi_signal_router.py` engine + signals | N7 | L |
| P2.2 | `PyMuPDF4LLMParser` adapter | N8 | S |
| P2.3 | `DoclingVLMParser` (Docling VLM pipeline + vLLM runtime) | N9 | M |
| P2.4 | `Qwen25VLClassifier` self-hosted visual classifier | N10 | M |
| P2.5 | `archival/gotenberg_adapter.py` PDF/A generalas | N11 | S |
| P2.6 | `archival/verapdf_validator.py` explicit validacio | N12 | S |
| P2.7 | `embeddings/` provider abstraction (BGE-M3 + e5 + Azure) | N13, N14, N15 | M |
| P2.8 | `embeddings/redaction_gate.py` PII gate | N16 | S |
| P2.9 | `rag_engine` refactor: embedder= parameter (K4) | K4 | S |
| P2.10 | `data_router` cross-document context (R7) | R7 | S |
| P2.11 | `attachment_processor.py` refactor multi-signal routing-hoz (K3) | K3 | S |
| P2.12 | Phase 2 acceptance: 10 processing flow validacio | — | M |

**Phase 2 acceptance**:
- PyMuPDF4LLM/Docling/VLM/Azure DI parser routing dontesek **audit-trail-ben**
- Profile A teljes pipeline mukodik **GPU nelkul** (PyMuPDF4LLM + Docling standard + e5)
- Profile A pipeline GPU-val mukodik (+ Docling VLM + Qwen25 VL + BGE-M3)
- Profile B ugyanaz cloud providerekkel
- veraPDF validacio EXPLICIT, NEM assumalt PDF/A status
- 10 processing flow (`document_pipeline.md` Section 8) E2E PASS

### Phase 3 — Governance & operational hardening (v1.6.0 cel)

**Cel**: Compliance, audit lineage, production secret management, distributed tracing, opcionalis CrewAI.

| # | Feladat | Komponensek | Becsules |
|---|---------|------------|----------|
| P3.1 | `audit/lineage.py` lineage tracker | N17 | M |
| P3.2 | `provenance/map.py` provenance map | N18 | S |
| P3.3 | `observability/otel_tracer.py` (K9) | N19, K9 | M |
| P3.4 | `observability/prometheus_metrics.py` (K8) | N20, K8 | M |
| P3.5 | `security/vault_provider_impl.py` (K5) | N21, K5 | S |
| P3.6 | `cli/aiflow.py` typer CLI bovites (K11) | N23, K11 | M |
| P3.7 | `confidence_calibration.py` per-field, B3.5 generalizacio (K12) | K12 | M |
| P3.8 | `agents/crewai_sidecar/` opcionalis bounded reasoning (N22) | N22 | L |
| P3.9 | LangGraph-compatible state machine adapter (opt) | — | M |
| P3.10 | Phase 3 audit + sign-off | — | M |

**Phase 3 acceptance**:
- Vault prod kornyezetben mukodik (titok lekeres + cache + invalidate)
- OTel trace lefedi a teljes pipeline-t (intake → archival)
- Prometheus metric / `/metrics` endpoint
- Lineage rekordok minden file → derivative → embedding kapcsolatra
- CrewAI sidecar opcionalis (NEM blokkol semmit ha disabled)
- CLI: `aiflow prompt sync`, `aiflow workflow run`, `aiflow eval run`

### Phase 4 — Optional optimizations (v2.0.0+ cel)

**Cel**: Eros opcionalis fejlesztesek, melyek NEM kotelezok az alap multi-source intake plathez.

| # | Feladat | Komponensek | Becsules |
|---|---------|------------|----------|
| P4.1 | Microsoft GraphRAG / LazyGraphRAG (N24, K10) | N24, K10 | L |
| P4.2 | Kafka cross-service event bus (N25) | N25 | M |
| P4.3 | Multi-tenant SaaS hardening | — | L |
| P4.4 | Azure AI Search mint vector store provider | — | M |
| P4.5 | n8n vizualis workflow editor | — | M |

---

## 8. Acceptance Criteria — Magas Szinten

### 8.1 Single-codebase
- [ ] Egyetlen `src/aiflow/` repo, NINCS profile-specifikus fork
- [ ] Profile A es B ugyanazokat a YAML pipeline template-eket hasznalja
- [ ] 0 `if profile == "a"` business logic patternt
- [ ] CI/CD futtatja mindket profile suite-ot

### 8.2 Multi-source intake
- [ ] IntakePackage betoltheto: email, file, folder, batch, API source-bol
- [ ] Csomag-szintu free-text + file association rule + LLM fallback
- [ ] Cross-document context propagacio a downstream step-ekbe
- [ ] HITL aktivalva ambiguitas eseten

### 8.3 Provider abstraction
- [ ] Parser/classifier/extractor/embedder mind providers registry-bol jon
- [ ] Tenant override mukodik per-instance
- [ ] Provider switching NEM igenyel kod-modositast

### 8.4 Routing audit
- [ ] Minden parser dontes `RoutingDecision` rekorddal jar (signals + selected + reason)
- [ ] Routing dontesek queryelhetok (audit endpoint)

### 8.5 Embedding governance
- [ ] PII redaction gate KOTELEZO embedding elott (`redaction_before_embedding_required: true`)
- [ ] Profile A embedding **CSAK** self-hosted modell (BGE-M3 / e5)
- [ ] Profile B embedding hibrid lehet (Azure VAGY self-hosted)

### 8.6 Archival + veraPDF
- [ ] PDF/A generalas Gotenberg-tel (NEM Docling-bol)
- [ ] PDF/A status CSAK veraPDF VALIDATION utan jelolheto "archived"-kent
- [ ] Validacio failure → manual review aganra ag

### 8.7 Audit / lineage
- [ ] Minden file → derivative → extraction → embedding lineage rekord
- [ ] Provenance map: file ↔ description ↔ package ↔ tenant
- [ ] Audit log queryelhe Web UI-bol

### 8.8 Operations
- [ ] Vault impl mukodik prod-ban (titok rotation tesztelve)
- [ ] OTel trace exportalva OTLP collectorba
- [ ] Prometheus `/metrics` endpoint
- [ ] CI green minden profile-on, regression coverage gate >=80%

---

## 9. Open Questions (eldontendok a `103_*` ciklus elott)

> Az alabbi nyitott kerdesek a 102/103 felulvizsgalat elott uzleti / compliance / operations
> resztvevoket igenylik. Default valaszok feltuntetve, de modosithatok.

| # | Tema | Kerdes | Default valasz |
|---|------|--------|----------------|
| Q1 | Compliance | Profile A "air-gapped" eseten engedelyezhete a Langfuse SaaS prompt SSOT? | Self-hosted Langfuse opcio (Phase 3) |
| Q2 | Compliance | PII embedding `pii_embedding_allowed=true` mikor adhato meg? | CSAK explicit DPIA + tenant approval utan |
| Q3 | Tenant model | Multi-tenant deployment SaaS vagy on-prem per-customer? | On-prem per-customer (jelenlegi instance modell) |
| Q4 | Embedding policy | Free-text association eredmenyt embedjuk-e? | Default: NEM (csak struktura embeddingelve) |
| Q5 | Package interpretation | Multi-file package "elsodleges fajl" automatikus felfedezese? | Rule-first (largest+oldest+most-fields), LLM fallback |
| Q6 | GPU strategy | Profile A GPU-mentes default, GPU opt-in? | Igen — VLM + BGE-M3 GPU eseten aktivalando |
| Q7 | Cost | Cloud parser dontes per-document cost cap (Profile B)? | Default: $0.50/doc (configurable) |
| Q8 | Operations | Self-hosted Langfuse bevezetes Phase 3-ban? | Igen — production opt-in |
| Q9 | Operations | Azure-only profile (NEM hibrid) szukseges? | NEM — minden Profile B hibrid-kepes |
| Q10 | CrewAI | Sidecar deploy mode: in-process vs separate service? | Separate service (resilience + restart isolation) |

---

## 10. Mit NEM csinalunk

> Explicit non-goals — feleslegesen ne csabuljon el a terv.

1. **NEM ujraepitjuk a Step + Workflow + Skill System architekturat**
2. **NEM cseraljuk Postgres + pgvector kozponti adatbazist**
3. **NEM cseraljuk a Langfuse-t** prompt SSOT-kent (csak self-hosted opciot adunk)
4. **NEM cseraljuk a JWT RS256 + bcrypt + RBAC stack-et**
5. **NEM dobjuk el a meglevo 21 adapter implementaciot** — egyseges interface ala kerulnek
6. **NEM tesszuk koterelezve a CrewAI-t** — bounded sidecar marad
7. **NEM tesszuk koterelezve a GraphRAG-ot** — Phase 4 opcio
8. **NEM toroljuk a `services/email_connector`-t** — low-level fetcher marad, csak nem kozvetlen pipeline-bol
9. **NEM dobjuk el a confidence scoring B3.5 vivmanyait** — generalizaljuk minden skill-re
10. **NEM lopjuk el a Sprint B (v1.3.0) idejet** — refinement v1.4.0+ sprint-tel kezdodik

---

## 11. Hivatkozasok

### 11.1 v2 refinement dokumentum-set (jelen terv)

| # | Dokumentum | Szerep | Olvasasi sorrend |
|---|-----------|--------|-----------------|
| 1 | `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` | **MASTER INDEX — kezdd itt!** | 1. |
| 2 | `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` | Atfogo terv + ADR-1 (jelen dok.) | 2. |
| 3 | `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` | 13 Pydantic contract teljes definicio | 3. |
| 4 | `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` | 7 entitas allapotgep + atmenetek | 4. |
| 5 | `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` | Backward compat + rolling deploy | 5. |
| 6 | `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` | Komponensenkenti reszletes (R/N/K-szeria) | 6. |
| 7 | `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` | Enterprise review 1. ciklus | 7. (tortenetiseg) |
| 8 | `103_AIFLOW_v2_FINAL_VALIDATION.md` | 2. ciklus + Phase 1 sign-off | 8. (tortenetiseg) |

### 11.2 AIFlow baseline dokumentumok

| # | Forras | Fontos szakasz |
|---|--------|---------------|
| 1 | `01_ARCHITECTURE.md` | Section 2-9 (kernel, workflow, skill, prompt, ops) |
| 2 | `03_DATABASE_SCHEMA.md` | 46 tabla, 6 view, 29 migration |
| 3 | `05_TECH_STACK.md` | Mar deklaralt deps (otel, prometheus, hvac) |
| 4 | `22_API_SPECIFICATION.md` | 165 endpoint, 25 router |
| 5 | `28_*.md` (archive) | Modular Deployment, Skill Instance |
| 6 | `49_STABILITY_REGRESSION.md` | L1-L5 regression |
| 7 | `50_RAG_VECTOR_CONTEXT_SERVICE.md` | RAG Phase 7A-7G |
| 8 | `51_DOCUMENT_EXTRACTION_INTENT.md` | Document type config + intent schema |
| 9 | `58_POST_SPRINT_HARDENING_PLAN.md` | Sprint A COMPLETE + Sprint B (B0-B11) |
| 10 | `61_GUARDRAIL_PII_STRATEGY.md` | Per-skill PII strategy |
| 11 | `62_DEPLOYMENT_ARCHITECTURE.md` | Dev vs ops env, Docker compose |
| 12 | `DEVELOPMENT_ROADMAP.md` | Vault, OTel, Kafka, GraphRAG |
| 13 | `document_pipeline.md` | Multi-source intake target architecture |
| 14 | `CrewAI_development_plan.md` | Bounded agentic reasoning layer (forras-korlatozas) |
| 15 | `FEATURES.md` | v1.2.2 feature baseline |

---

## 12. Vegrehajtas Sorrend (rovid osszefoglalo)

```
v1.3.0 Sprint B (FOLYAMATBAN) — NEM blokkoljuk
   |
   ▼
v1.4.0 = REFINEMENT PHASE 1 (Critical corrections)
   - Multi-source intake (IntakePackage + Source Adapter Layer)
   - Provider Registry + interface contracts
   - Policy Engine + parameter binding
   - email_connector + document_extractor refactor
   - Profile A + Profile B config files
   |
   ▼
v1.5.0 = REFINEMENT PHASE 2 (Architectural refinements)
   - Multi-signal parser routing engine
   - PyMuPDF4LLM + Docling VLM + Qwen25 VL adapters
   - Gotenberg + veraPDF archival pipeline
   - BGE-M3 + e5 + Azure embedding providers
   - PII redaction gate
   - 10 processing flow E2E acceptance
   |
   ▼
v1.6.0 = REFINEMENT PHASE 3 (Governance & ops)
   - Audit lineage + provenance map
   - OTel + Prometheus
   - Vault prod impl
   - CLI bovites
   - Optional CrewAI sidecar
   - LangGraph-compatible state machine adapter
   - Confidence calibration generalizacio (B3.5 alapjan)
   |
   ▼
v2.0.0+ = REFINEMENT PHASE 4 (Optional)
   - GraphRAG (LazyGraphRAG)
   - Kafka event bus
   - Multi-tenant SaaS hardening
   - Azure AI Search mint vector store provider
```

---

## 13. Legkozelebbi lepes

A terv-set **ELFOGADVA** (a 103_* 2. ciklus sign-off elfogadta). A kovetkezo lepesek:

1. **Sprint B (v1.3.0) befejezese** — NEM blokkolt a refinement altal, kovetve a `58_*` tervet
2. **Phase 1a kickoff** (v1.4.0 sprint) — `01_PLAN/session_XX_v1_4_0_phase_1a_kickoff.md` letrehozas
3. **Customer notification** — pre-migration uzenet kuldese 1 sprint elott (lasd `100_d` Section 9.1)
4. **CI/CD per-profile suite** konfiguracio (Profile A vs B kulon teszt run)
5. **`100_e_AIFLOW_v2_CAPACITY_PLANNING.md`** (Should fix, Phase 2 elott)
6. **`100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md`** (Should fix, Phase 1 acceptance utan)

### Olvasasi sorrend uj olvasohoz:

1. **`104_AIFLOW_v2_FINAL_MASTER_INDEX.md`** — kezdd itt! (master index)
2. `100_*` (jelen dok.) — atfogo kep + ADR-1
3. `100_b_*` — domain contracts (Phase 1a foundation)
4. `100_c_*` — state lifecycle
5. `100_d_*` — migration playbook
6. `101_*` — komponensenkenti reszletes terv
7. `103_*` — Phase 1 sign-off + kibovitesek (routing, provider, isolation)
8. (opcionalis) `102_*` — review elozmeny

---

> **Vegig:** ez a terv **NEM** redesign — refinement. A meglevo komponensek 80%+ orzendo,
> 15% refactoring (interface-en keresztul), 5% uj komponens (greenfield).
>
> **Readiness (ketlepcsos):**
>
> 1. **Phase 1 implementation-ready (NOW)** — A teljes terv-set (100_ + 100_b/c/d + 101_ + 103_ + 104_)
>    **Phase 1a (v1.4.0) sprint indulasra kesz**. A meglevo dokumentumok biztositjak a contract + state + migration
>    szinten minden szukseges inputot az implementacios csapat szamara.
>
> 2. **Full operational readiness (Phase 2 elott)** — A teljes customer production deployment
>    csak akkor tekintheto "customer-deployable" minositesnek, ha a `100_e_AIFLOW_v2_CAPACITY_PLANNING.md`
>    es `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` dokumentumok is lezarulnak (P1 hardening
>    a `105_*`-ben rogzitve).
