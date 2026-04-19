# AIFlow v2 — Final Master Index (Egyseges Belepesi Pont)

> **Verzio:** 1.1 (FINAL + Phase 1a COMPLETE)
> **Datum:** 2026-04-09 (initial) / 2026-04-17 (Phase 1a DONE)
> **Statusz:** ELFOGADVA (SIGNED OFF) — **Phase 1a Foundation (v1.4.0) COMPLETE**
> **Cel:** Az AIFlow v1.3.0 → v2.0.0 refinement-hez tartozo teljes dokumentum-set
> **egyseges belepesi pontja**. A felulvizsgalatokat (102_* + 103_*) kovetoen letrejott
> **vegleges egyseges terv**.
>
> **Phase 1a delivery (2026-04-17, Sprint D S44-S53):** 13 Pydantic contract, 7 state machine,
> PolicyEngine + profile A/B override, ProviderRegistry + 4 ABC, SkillInstance.policy_override,
> backward compat shim + pipeline auto-upgrade, Alembic 032 intake_tables + 033 policy_overrides,
> 199 Phase 1a E2E PASS. Next: Phase 1b (v1.4.1) source adapters.

---

## 0. Hogyan hasznald ezt a dokumentumot

Ez a **Master Index** — ez az **egyetlen** belepesi pont a teljes AIFlow v2 refinement
tervhez. A tobbi dokumentum a reszleteket tartalmazza.

### 0.1 Ket fo belepo pont (szerepkor szerint)

| Szerepkor | Kezdd itt | Majd olvasd |
|-----------|----------|-------------|
| **Product / uzletiseg / architect** (mit es miert) | **`104_*` (jelen dok.)** | `100_*` + ADR-1 + `103_*` Section 12 sign-off |
| **Fejlesztő / implementacio** (hogyan) | **`106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md`** | `100_b_*` (contracts) + `100_c_*` (state) |
| **Auditor / compliance** | `104_*` → `100_*` Section 2.A (ADR-1) | `100_c_*` + `103_*` Section 6 isolation |

> **FONTOS:** A **fejleszto nem olvasza el mind a 11 dokumentumot**. A `106_*` ONALLÓ
> implementacios útmutato napra lebontva, konkret kod-peldakkal, git workflow-val es
> acceptance gate-tel. A `106_*` hivatkozik a reszletes forrasokra (`100_b/c/d`), de
> **onmagaban futtathato**.

**Mindig itt kezdd:**
1. Olvasd el ezt a dokumentumot elejetol a vegeig (~15 perc)
2. Kovetsd az **olvasasi sorrendet** (Section 2)
3. Ha implementalsz: **`106_*` Phase 1a Implementation Guide** az egyetlen belepesi pont
4. Ha auditalsz: kovetsd az **acceptance criteria matrix**-et (Section 5)

---

## 1. A terv-set — mely dokumentumok alkotjak a vegleges tervet

### 1.1 v2 refinement dokumentum-set (12 darab, `01_PLAN/` mappa)

**Ket csoport**:
- **Strategiai / architektura / governance** (1-10): uzletiseg, architect, compliance olvassa
- **Vegrehajtas** (11-12): fejleszto olvassa, onalloan futtathato

| # | Fajl | Szerep | Sorok | Statusz |
|---|------|--------|-------|---------|
| **STRATEGIAI CSOMAG** ||||
| 1 | **`104_AIFLOW_v2_FINAL_MASTER_INDEX.md`** | **Master index** — strategiai belepesi pont (jelen dok.) | ~500 | FINAL |
| 2 | `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` | Atfogo terv + ADR-1 (CrewAI core REJECTED) | ~620 | FINAL (v2.0) |
| 3 | `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` | 13 Pydantic contract teljes definicio | ~580 | FINAL (v2.0) |
| 4 | `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` | 7 entitas allapotgep + atmenetek + recovery | ~370 | FINAL (v2.0) |
| 5 | `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` | Backward compat + rolling deploy + rollback decision matrix | ~680 | FINAL (v2.0) |
| 6 | `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` | Hardware profil + benchmark + cost model | ~450 | FINAL |
| 7 | `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` | Review workload + SLA + bulk UI | ~450 | FINAL |
| 8 | `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` | Komponensenkenti reszletes (R/N/K-szeria) + N11b/N11c | ~1680 | FINAL (v2.0) |
| 9 | `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` | Enterprise review 1. ciklus (historikus) | ~600 | ARCHIV |
| 10 | `103_AIFLOW_v2_FINAL_VALIDATION.md` | 2. ciklus + Phase 1/2 bontas + isolation + P4 CI + sign-off | ~1100 | FINAL (v2.0) |
| 11 | `105_AIFLOW_v2_P0_P4_HARDENING_RECORD.md` | P0-P4 zaro hardening letteris | ~400 | FINAL |
| **VEGREHAJTASI CSOMAG** ||||
| 12 | **`106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md`** | **Phase 1a vegrehajtasi kickoff guide — ONALLO, napra lebontva** | ~800 | **FINAL** |

**Osszesen: ~8,230 sor** a vegleges egyseges terv.

> **FEJLESZTO BELEPESI PONT:** `106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md` — ez az
> egyetlen dokumentum, amit a fejlesztonek el kell olvasnia a Phase 1a elinditasahoz. Onallo,
> konkret, napra lebontva, kod-peldakkal, git workflow-val. Olvasasi ido: ~60 perc. Utana
> `100_b_*` (30 perc) + `100_c_*` (15 perc). **Osszesen ~2 ora, aztan mehet Day 1.**

### 1.2 Mi NEM resze a terv-setnek

- `58_POST_SPRINT_HARDENING_PLAN.md` — a jelenlegi Sprint B (v1.3.0) terve, folyamatban
- `DEVELOPMENT_ROADMAP.md` — a forras dokumentum, v1.3.0+ opcionalis iranyok (pre-refinement)
- `document_pipeline.md` — a forras dokumentum (target architektura prompt)
- `CrewAI_development_plan.md` — a forras dokumentum (bounded sidecar kikotes)

---

## 2. Olvasasi sorrend

### 2.1 Fejleszto — Phase 1a implementacio (optimalis: 2 ora)

> **EZ A MINIMALIS ES ELEGSEGES keszlet a Phase 1a Day 1 kezdesere.**

```
1. 106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md (60 perc)   ← ONALLO, kezdd ITT!
2. 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md (30 perc)              ← Pydantic kod forras
3. 100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md (15 perc)         ← Transition table
4. 100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md Section 2 + 12 (10 perc)  ← Migration minta + rollback
```

**Osszesen:** ~2 ora. A `106_*` Section 12-ben talalod, mikor mely reszletesebb dokumentumra
van szukseg (pl. `101_` N7 ha routing engine-t implementalsz — de az Phase 2, Phase 1a-ban nem).

### 2.2 Fejleszto — mely tovabbi dokumentumot mikor?

| Phase | Uj dokumentum ami mar kell | Miert |
|-------|---------------------------|-------|
| Phase 1b (v1.4.1) — source adapters | `101_*` N2 + R1 + N4 | Source adapter implementacio |
| Phase 1c (v1.4.2) — document_extractor refactor | `101_*` R4 | Extract_from_package |
| Phase 1.5 (v1.4.5) — Vault + self-hosted Langfuse | `101_*` R8/N21 | Production secret |
| Phase 2a (v1.5.0) — routing engine | `103_*` Section 4 + `101_*` N7/N8 | Multi-signal routing |
| Phase 2b (v1.5.1) — VLM stack | `101_*` N9/N10 + R6 | Docling VLM + Qwen25 |
| Phase 2c (v1.5.2) — embedding providers | `101_*` R5 + N13/N14/N15/N16 | BGE-M3 + Azure + PII gate |
| Phase 2d (v1.5.3) — archival | `101_*` N11/N11b/N11c/N12 | Gotenberg + veraPDF + quarantine |
| **Phase 2 kezdese elott (kotelezo)** | `100_e_*` + `100_f_*` | Capacity + HITL workload |
| Phase 3 — governance | `101_*` N17/N18/N19/N20/N22 + R11 | Lineage + OTel + CrewAI |

### 2.3 Architect / Product / Business (strategiai szint)

```
1. 104_* (jelen dok., 15 perc)                — Master Index, atfogo kep
2. 105_* (10 perc)                            — P0-P4 hardening letteris
3. 100_* (30 perc)                            — Atfogo refinement terv + ADR-1
4. 103_* Section 3 + 12 (15 perc)             — Phase bontas + sign-off
5. (Phase 2 elott) 100_e_* (20 perc)          — Capacity planning
6. (Phase 2 elott) 100_f_* (20 perc)          — HITL workload model
```

**Osszesen:** ~1.5 ora strategiai szinten.

### 2.2 Auditorhoz / compliance tekintethez

```
1. 104_* (jelen dok.)                         — Master Index
2. 100_* Section 2.A (ADR-1)                  — CrewAI core orchestrator REJECTED indoklas
3. 100_* Section 5-6                          — Two-profile + policy parameters
4. 100_c_* Section 1                          — IntakePackage state machine (audit lineage)
5. 100_c_* Section 5                          — ArchivalArtifact state (compliance PDF/A)
6. 103_* Section 6                            — Multi-tenant data isolation
7. 103_* Section 9                            — Phase 1 acceptance criteria
8. 103_* Section 12                           — Sign-off signatures
```

### 2.3 Uzleti / termek tulajdonoshoz

```
1. 104_* (jelen dok.)                         — Master Index
2. 100_* Section 0                            — Vezetoi osszefoglalo
3. 100_* Section 3                            — Cel architektura (madartavlat)
4. 100_* Section 7                            — Fazis tervezes (prioritas sorrend)
5. 100_d_* Section 9-11                       — Customer notification + phase rollout
6. 103_* Section 13                           — Vegleges osszefoglalo
```

### 2.4 Review historia (csak tortenelem miatt)

```
102_*  — 1. ciklus review (Must/Should/Nice fix kategorizalas)
         Ezt csak akkor olvasd, ha meg akarod erteni MIERT lett a terv frissitve.
         A 103_* mar tartalmazza a FINAL valtozatot.
```

---

## 3. Mit csinal a terv? — 10 mondatos osszefoglalo

1. **AIFlow v1.3.0 → v2.0.0** refinement terve (NEM redesign, NEM rewrite)
2. A **meglevo** Step + Workflow + Pipeline + Skill System architektura **megorzendo**
3. **Hozzaad**: Multi-source intake package modell (email + file + folder + batch + API)
4. **Hozzaad**: Provider abstraction layer (parser/classifier/extractor/embedder)
5. **Hozzaad**: Policy Engine (30+ parameter, profile + tenant + instance override)
6. **Hozzaad**: Multi-signal parser routing engine (PyMuPDF4LLM/Docling/VLM/Azure DI)
7. **Hozzaad**: PDF/A archival pipeline (Gotenberg + veraPDF)
8. **Hozzaad**: Self-hosted embedding (BGE-M3) + opcionalis Azure OpenAI
9. **Hozzaad**: Audit lineage + provenance map + OTel + Prometheus + Vault
10. **Ket deployment profil** egyetlen kodbazisban: Profile A (cloud-disallowed air-gapped) + Profile B (Azure-optimized)

---

## 4. Phase ordering (v1.4.0 → v2.0.0+)

```
v1.3.0 (jelenlegi Sprint B)          — NEM BLOKKOLT, fut
    |
    ▼
v1.4.0 Phase 1a — Foundation          — 1 sprint
    ├─ 100_b contractok + alembic 030
    ├─ 100_c state machines
    ├─ N5 PolicyEngine + 30+ parameter
    ├─ N6 ProviderRegistry + 4 ABC
    └─ R13 instance policy override
    |
    ▼
v1.4.1 Phase 1b — Source adapters     — 1 sprint
    ├─ 5 source adapter (email/file/folder/batch/api)
    ├─ N4 File ↔ Description association
    └─ POST /api/v1/intake/upload-package
    |
    ▼
v1.4.2 Phase 1c — Refactor + acceptance — 1 sprint
    ├─ R4 document_extractor IntakePackage centric
    ├─ R12 multi-source pipeline pelda
    ├─ UI multi-file upload
    └─ 10 processing flow E2E PASS
    |
    ▼
v1.4.5 Phase 1.5 — Profile A ready    — 0.5 sprint
    ├─ R8/N21 Vault prod (hvac)
    ├─ Self-hosted Langfuse
    └─ Profile A air-gapped E2E
    |
    ▼
v1.5.0-1.5.4 Phase 2 — Architectural refinements (~4 sprint)
    ├─ 2a: Multi-signal routing + PyMuPDF4LLM + Docling provider
    ├─ 2b: Docling VLM + Qwen25 VL + vLLM
    ├─ 2c: BGE-M3 + e5 + Azure embedding + PII RedactionGate + multi-tenant isolation
    ├─ 2d: Gotenberg + veraPDF + quarantine + Azure DI provider + data_router cross-doc
    └─ 2e: 10 processing flow E2E + Profile A/B teljes
    |
    ▼
v1.6.0 Phase 3 — Governance & ops     — ~3 sprint
    ├─ N17 audit lineage + N18 provenance map
    ├─ N19 OTel tracer + N20 Prometheus metrics
    ├─ R11 confidence calibration layer
    ├─ N22 CrewAI bounded sidecar
    ├─ N22b CrewAI Step adapter experiment (2 specialist A/B)
    └─ N23 typer CLI bovites
    |
    ▼
v2.0.0+ Phase 4 — Optional             — opcio
    ├─ N24 Microsoft LazyGraphRAG
    ├─ N25 Kafka event bus
    ├─ Multi-tenant SaaS hardening
    └─ Azure AI Search vector store
```

**Osszesen:** Phase 1 (3.5 sprint) + Phase 2 (4 sprint) + Phase 3 (3 sprint) = **~10-11 sprint ~8-9 honap**
Phase 4 opcionalis, v2.0.0+.

---

## 5. Kulcs dontesek (ADR-k)

### 5.1 ADR-1 — CrewAI NEM core orchestrator

> **Statusz:** ACCEPTED
> **Hely:** `100_*` Section 2.A
> **Kontextus:** Felhasznaloi felveteshez szakmai elemzes 18 ervvel (15 architekturalis + 3 uzleti)
> **Dontes:** Hybrid (AIFlow native + CrewAI bounded sidecar + Phase 3 controlled experiment)
> **Indoklas:**
> 1. Compliance / Profile A air-gapped nem turi az opaque agentikus donteseket
> 2. Migracios koltseg 6+ honap + 1424 unit teszt rewrite tul magas
> 3. A CrewAI ertekek (reasoning, knowledge, multi-agent) **sidecar** szinten ervenyesulnek, NEM core-ban

### 5.2 ADR-ek a jovoben

A jovobeni architektura dontesekhez `101_*` komponens szekcioiban vagy kulon ADR fajlokban:
- ADR-2: LangGraph-compatible state machine adapter (Phase 3 opcio)
- ADR-3: Self-hosted Langfuse Profile A-ra (mar Phase 1.5-ben elfogadva)
- ADR-4: GraphRAG vs LazyGraphRAG (Phase 4 dontes)

---

## 6. Phase 1a kickoff checklist (implementacios utemterv)

### 6.1 Pre-kickoff (Sprint B utolsoja)

- [ ] Sprint B (v1.3.0) befejezve
- [ ] Customer notification kuldve (lasd `100_d` Section 9.1)
- [ ] CI/CD per-profile suite konfiguralt
- [ ] `01_PLAN/session_XX_v1_4_0_phase_1a_kickoff.md` session prompt letrehozva

### 6.2 Kickoff napja

- [ ] Branch letrehozva: `feature/v1.4.0-phase-1a-foundation`
- [ ] Pre-migration DB backup: `pg_dump aiflow > backup_pre_v1.4.0.sql`
- [ ] Team briefing (architect + engineer + compliance)

### 6.3 Phase 1a sprint (v1.4.0)

#### Week 1 — Contracts + State

- [ ] `src/aiflow/intake/__init__.py` + `intake/package.py` (100_b Section 1)
- [ ] Pydantic v2 modellek: IntakePackage, IntakeFile, IntakeDescription
- [ ] Alembic 030: intake_packages + intake_files + intake_descriptions + package_associations
- [ ] State machine validator (`intake/state_machine.py`, 100_c Section 1)
- [ ] Unit test 20+

#### Week 2 — Policy + Provider Registry

- [ ] `src/aiflow/policy/engine.py:PolicyEngine` (100_* Section 6)
- [ ] `config/profiles/profile_a.yaml` + `profile_b.yaml`
- [ ] `src/aiflow/providers/registry.py:ProviderRegistry`
- [ ] 4 ABC: ParserProvider, ClassifierProvider, ExtractorProvider, EmbedderProvider (103_* Section 5.1)
- [ ] Contract test framework (`tests/integration/providers/test_contract.py`)
- [ ] Alembic 031: policy_overrides tabla

#### Week 3 — Instance override + Backward compat

- [ ] R13 `skill_system/instance.py` — `policy_override` mezo
- [ ] `instances/{customer}/policy.yaml` betoltes
- [ ] `100_d` Section 4 backward compat shim layer
- [ ] R4 shim: `document_extractor.extract(file)` → single-file package wrapper

#### Week 4 — Acceptance + dokumentacio

- [ ] Phase 1a E2E test suite (`tests/e2e/v1_4_0_phase_1a/`)
- [ ] Existing tests NEM regreszalnak
- [ ] Alembic rollback tesztelt
- [ ] `01_PLAN/58_POST_SPRINT_HARDENING_PLAN.md` Phase 1a progress update
- [ ] `CLAUDE.md` key numbers frissites
- [ ] Phase 1a demo — team walkthrough

### 6.4 Phase 1a exit criteria

- [ ] Minden unit test PASS
- [ ] Minden integration test PASS
- [ ] Minden contract test PASS (4 ABC)
- [ ] State transition validator PASS
- [ ] Profile A + B config betoltheto
- [ ] Per-instance policy override mukodik
- [ ] Backward compat: `extract(file)` meg mindig mukodik
- [ ] Alembic 030-031 sikeres + rollback tesztelve
- [ ] CI green (ket profile suite + coverage >= 80%)

---

## 7. Key numbers (v2 tergetek)

### 7.1 v1.3.0 baseline (Sprint B folyamatban, jelenlegi)

| Metrika | Ertek |
|---------|-------|
| Services | 26 |
| API endpoints | 165 |
| DB tablak | 46 |
| Alembic migraciok | 29 |
| Pipeline adapterek | 21 |
| Pipeline templates | 7 |
| Skills | 5 (qbpp torolve) |
| UI oldalak | 22 |
| Unit tests | 1424 |
| Guardrail tests | 129 |
| Security tests | 97 |
| Promptfoo tests | 80 |
| E2E tests | 104 |

### 7.2 v1.4.5 Phase 1 complete (cel)

> **Scope correction (2026-04-27, S92):** a Phase 1a (v1.4.0) szallitmany
> **3 intake Pydantic contract** (IntakePackage / IntakeFile / IntakeDescription +
> 4 enum + 3 exception) es **1 IntakeStateMachine** (IntakeFile lifecycle) lett —
> nem a korabban jelzett 13 + 7. A hianyzo 10 v2 contract es a 6 tovabbi state machine
> a Phase 2 pre-work-ben lesz leszallitva az erintett domen aktivalasa elott
> (lasd Section 10.3 "Deferred v2 contracts"). A Phase 1a foundation DONE status
> valtozatlan — a scope pontositas a transparencia erdekeben tortent.

| Metrika | Ertek | Valtozas |
|---------|-------|----------|
| Services | 27 (+ policy_engine service layer) | +1 |
| API endpoints | ~175 (+ intake/upload, policy, provider, routing) | +10 |
| DB tablak | ~52 (+ intake_packages, intake_files, intake_descriptions, package_associations, policy_overrides, routing_decisions) | +6 |
| Alembic migraciok | 37 (032 intake_tables + 033 policy_overrides + 034-037 Phase 1b-1d) | +8 vs v1.3.0 |
| Pipeline adapterek | 22 (+ intake_normalize) | +1 |
| New Pydantic contracts (Phase 1a actual) | +3 intake (IntakePackage/File/Description) + 4 enum + 3 exception | +3 intake |
| State machines (Phase 1a actual) | +1 (IntakeStateMachine — IntakeFile lifecycle) | +1 |
| Deferred v2 contracts (Phase 2+) | 10 (lasd §10.3) | — |
| Deferred state machines (Phase 2+) | 6 (lasd §10.3) | — |
| Unit tests | ~1550 (+ 130 intake + policy + provider) | +~126 |
| Domain contracts | 3 intake formal Pydantic v2 + 4 provider ABC + test framework | NEW |
| Profile deployments | 2 (A + B, single codebase) | NEW |

### 7.3 v1.5.4 Phase 2 complete (cel)

| Metrika | Ertek | Valtozas |
|---------|-------|----------|
| Services | 30 (+ visual_classifier, archival, embeddings) | +3 |
| API endpoints | ~185 | +10 |
| DB tablak | ~58 (+ archival_artifacts, validation_results, embedding_decisions) | +6 |
| Alembic migraciok | 36 | +3 |
| Parser providers | 4 (PyMuPDF4LLM, Docling standard, Docling VLM, Azure DI) | NEW |
| Embedding providers | 3 (BGE-M3, e5-large, Azure OpenAI) | NEW |
| Archival pipeline | Gotenberg + veraPDF | NEW |

---

## 8. Acceptance criteria matrix

### 8.1 Phase 1a (v1.4.0) — Foundation — **COMPLETE (2026-04-17)**

| Kategoria | Kritetium | Hely | E2E lefedettseg | Statusz |
|-----------|-----------|------|-----------------|---------|
| Contracts | 3 intake Pydantic modell (IntakePackage / IntakeFile / IntakeDescription) + 4 enum + 3 exception, Pydantic v2 syntax. A 10 tovabbi v2 contract Phase 2+ (lasd §10.3). | `100_b` | `test_intake_package_lifecycle.py` | DONE (S44) — scope pontositva 2026-04-27 |
| State | 1 IntakeStateMachine (IntakeFile lifecycle) + validator. A 6 tovabbi state machine Phase 2+ (lasd §10.3). | `100_c` | `test_intake_package_lifecycle.py` | DONE (S44) — scope pontositva 2026-04-27 |
| Policy | 30+ parameter PolicyEngine + profile override | `100_*` Section 6 | `test_policy_engine_profile_switch.py`, `test_skill_instance_policy_override.py` | DONE (S46, S48, S49) |
| Provider | 4 ABC + contract test framework | `103_*` Section 5 | `test_provider_registry_contract.py` | DONE (S47) |
| Migration | Alembic 032-033 + rollback tesztelve | `100_d` | `test_intake_package_lifecycle.py` (end-to-end with 032+033 schema) | DONE (S45, S48) |
| Backward compat | `extract(file)` meg mukodik + pipeline auto-upgrade | `100_d` Section 4 | `test_backward_compat_extract_file.py`, `test_pipeline_auto_upgrade.py`, `test_legacy_pipeline_regression.py`, `test_extract_shim_regression.py` | DONE (S50, S52) |

**Teljes E2E suite:** `tests/e2e/v1_4_0_phase_1a/` — 199 test PASS (3.94s), `<10s SLA`. Lasd `106_*` Section 7 Day 19.

### 8.2 Phase 1b (v1.4.1) — Source adapters

| Kategoria | Kritetium |
|-----------|-----------|
| Sources | 5 adapter mukodik (email, file, folder, batch, api) |
| Association | 4 mode (rule_only, rule_first_llm_fallback, llm_only, manual_only) |
| API | POST /api/v1/intake/upload-package endpoint |
| E2E | Multi-source acceptance test PASS |

### 8.3 Phase 1c (v1.4.2) — Refactor + acceptance

| Kategoria | Kritetium |
|-----------|-----------|
| Document extractor | `extract_from_package()` mukodik |
| Pipeline auto-upgrade | v1.3 pipeline → v1.4 schema transzformalt |
| UI | Multi-file upload oldal |
| E2E | 10 processing flow (`document_pipeline.md` Section 8) PASS |

### 8.4 Phase 1.5 (v1.4.5) — Profile A ready

| Kategoria | Kritetium |
|-----------|-----------|
| Vault | `hvac` prod impl mukodik, token rotation tesztelve |
| Langfuse | Self-hosted instance Profile A-ban |
| E2E | Profile A teljes pipeline air-gapped kornyezetben PASS |

### 8.5 Phase 2 acceptance (v1.5.0-1.5.4)

Lasd `103_*` Section 9 + `100_*` Section 7 Phase 2 acceptance.

---

## 9. Risk Register

### 9.1 High-risk items (monitoring kotelezo)

| # | Kockazat | Hatas | Mitigation |
|---|---------|-------|------------|
| R1 | Phase 1a contractok hibas design → minden downstream erinti | KRITIKUS | Pre-kickoff architect + lead engineer review |
| R2 | Backward compat shim layer ledonti a meglevo customer pipeline-okat | HIGH | Staging E2E teszt minden customer pipeline-ra |
| R3 | BGE-M3 magyar nyelvre gyenge teljesítmény | HIGH | Phase 2c benchmark valos magyar adattal |
| R4 | Qwen25-VL GPU VRAM elegtelen | HIGH | Phase 2b elott VRAM profiling |
| R5 | Self-hosted Langfuse stabilitas | MEDIUM | Phase 1.5 early staging teszt |
| R6 | Multi-signal routing engine komplexitas | MEDIUM | Phase 2a extensive unit test + signal kalibracio |
| R7 | veraPDF license / performance | MEDIUM | Phase 2d elott license check |
| R8 | CrewAI sidecar integracio hibas | LOW (opcionalis) | Phase 3-ban feature flag opt-in |

### 9.2 Risk review cycle

Minden Phase acceptance utan risk register update. Phase N+1 kickoff elott uj risk items
azonositasa.

---

## 10. Open items (Should fix + Nice to have)

### 10.1 Should fix (Phase 2 elott megoldando)

| # | Tetel | Megoldas | Deadline |
|---|------|----------|---------|
| SF1 | Compliance + archival failure path | `101_` N11/N12 kibovites + N11b/N11c uj | Phase 2d |
| SF2 | GPU + capacity reality check | `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` (uj) | Phase 2 elott |
| SF3 | HITL workload tervezes | `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` (uj) | Phase 1 acceptance utan |
| SF6 | Cost attribution per-tenant | DB schema kibovites (alembic 037) | Phase 3 |

SF4 (Vault Phase 1.5) + SF5 (self-hosted Langfuse) MAR megoldva a MF4 keretein belul.

### 10.2 Nice to have (Phase 3+)

Lasd `103_*` Section 10 (tovabbi vizsgalando szempontok).

### 10.3 Deferred v2 contracts (Phase 2+ scope)

> **Kontextus (2026-04-27, S92):** A Phase 1a szallitmanya 3 intake contract + 1 state
> machine volt — a teljes 13 + 7 scope-bol a kovetkezo 10 contract es 6 state machine
> az erintett Phase 2/3 sub-phase pre-work-jeben keszul el. Minden tetel egy egyoldalas
> ADR + Pydantic stub + state-machine sketch formaban zar le, mielott az owning Phase
> sub-sprint elindul. A `106_*` Phase 1a guide ezt az intake magot irta le teljesen —
> a tovabbi contractok a `101_*` komponens-leirasokban es a `103_*` validation
> dokumentumokban mar hivatkozva vannak, csak a formalis Pydantic definiciok keszulnek el
> later.

| # | Contract / State | Owning Phase | Pre-work session | Forras spec |
|---|------------------|--------------|------------------|-------------|
| 1 | **RoutingDecision v2** (multi-signal + cost-aware) | Phase 2a (v1.5.0) | Pre-2a PP2 | `103_*` Section 4, `101_*` N7 |
| 2 | **ExtractionResult v2** (structured + confidence + provenance) | Phase 2b (v1.5.1) | Pre-2b PP2 | `101_*` R4 + N9/N10 |
| 3 | **ArchivalArtifact** (PDF/A + retention) | Phase 2d (v1.5.3) | Pre-2d PP2 | `100_c` Section 5, `101_*` N11/N11b/N11c |
| 4 | **ReviewTask** (HITL workflow) | Phase 3 (v1.6.2) | Pre-3 PP2 | `100_f_*`, `101_*` N22b |
| 5 | **ProvenanceRecord** (audit lineage) | Phase 3 (v1.6.0) | Pre-3 PP2 | `101_*` N17/N18 |
| 6 | **ValidationResult** (compliance + policy verdict) | Phase 3 (v1.6.1) | Pre-3 PP2 | `103_*` Section 9.5, `101_*` N11c |
| 7 | **EmbeddingDecision** (provider + model + dim) | Phase 2c (v1.5.2) | Pre-2c PP2 | `101_*` R5 + N13/N14 |
| 8 | **PIIRedactionReport** (classifier verdict + redaction map) | Phase 2c (v1.5.2) | Pre-2c PP2 | `101_*` N15/N16 |
| 9 | **QuarantineItem** (reject + manual review queue) | Phase 2d (v1.5.3) | Pre-2d PP2 | `101_*` N11b |
| 10 | **CostAttribution** (per-tenant + per-provider cost) | Phase 2d (v1.5.3) | Pre-2d PP2 | Section 10.1 SF6 |

**Deferred state machines** (6 additional, paired with the contracts above):

| # | State machine | Owning Phase | Paired contract |
|---|---------------|--------------|-----------------|
| 1 | RoutingDecisionStateMachine | Phase 2a | #1 |
| 2 | ExtractionResultStateMachine | Phase 2b | #2 |
| 3 | ArchivalArtifactStateMachine | Phase 2d | #3 |
| 4 | ReviewTaskStateMachine | Phase 3 | #4 |
| 5 | EmbeddingDecisionStateMachine | Phase 2c | #7 |
| 6 | QuarantineItemStateMachine | Phase 2d | #9 |

**Governance:** Minden contract + state machine sign-off kotelezo mielott az owning
sub-sprint Day 1 kezdodik. A Phase 2 pre-work PP2 osszefoglalja ezt a lookup-ot a
`ROADMAP.md` "Phase 2 prep" szekciojaban.

---

## 11. Sign-off status

### 11.1 Elfogadott (103_ Section 12)

- ✅ **Senior enterprise solution architect** — 2026-04-08
- ✅ **Lead Python platform engineer** — 2026-04-08
- ✅ **Compliance officer** — 2026-04-08

### 11.2 Fuggo aláirasok

- ⏳ **Customer account manager** — sign-off pre-kickoff (customer notification kuldese utan)
- ⏳ **Product manager** — sign-off pre-kickoff (roadmap/timeline alignment)
- ⏳ **Ops team lead** — sign-off pre-Phase 1.5 (Vault + self-hosted Langfuse infra)

---

## 12. Dokumentum valtozas naplo

### 2026-04-27 — S92 scope-korrekcio (Phase 1a actually-delivered)

**Rogzitve**: Section 7.2 + Section 8.1 + uj Section 10.3

- Felismeres: Phase 1a (v1.4.0) S44 szallitott 3 intake Pydantic contract + 1 state
  machine-t — nem 13 + 7, ahogy a `104_*` §7.2 és §8.1 eredetileg tervezett. A 10
  tovabbi v2 contract es 6 state machine a Phase 2/3 sub-phase pre-work-ben keszul el,
  az erintett domen aktivalasa elott.
- Frissites: `§7.2 v1.4.5 Phase 1 complete (cel)` — scope correction callout + metrika sorok
  (Phase 1a actual = 3 intake contract + 1 state machine).
- Frissites: `§8.1 Phase 1a acceptance matrix` — Contracts + State sorok pontositasa,
  DONE statusz marad.
- Uj: `§10.3 Deferred v2 contracts (Phase 2+ scope)` — 10 contract + 6 state machine
  lookup-ja owning Phase + pre-work session + forras spec hivatkozassal.
- Ok: forward roadmap (uj `01_PLAN/ROADMAP.md`) a Phase 2 pre-work PP2 scope-jat erre
  a §10.3 lookup-ra hivatkozza.

### 2026-04-09 — Phase 1a Implementation Guide (onalló vegrehajtasi csomag)

**Rogzitve**: `106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md`

- Felismeres: 11 dokumentum 7430 sorral tul sok a fejleszto Phase 1a kickoff elotti elerheto olvasasi ablakjahoz
- Letrehozas: `106_*` Phase 1a onallo vegrehajtasi guide
- Tartalom: 14 szakasz, napra lebontott Day 1-20 terv, konkret kod-peldak (Python + SQL + YAML),
  git workflow + commit naming convention, acceptance gate checklist, rollback plan, standup template
- Frissites: `104_*` Section 0 ket belepo pont (strategiai vs vegrehajtas)
- Frissites: `104_*` Section 1.1 dokumentum-set 12 darabra (strategiai + vegrehajtasi csoport)
- Frissites: `104_*` Section 2 fejleszto olvasasi sorrend 2 ora minimumra csokkent
- Frissites: `104_*` Section 14 integritas-ellenorzes `106_*` kereszteivel
- Cel: a fejleszto **onalloan** tudja Phase 1a-t elinditani, a minimum olvasas 2 ora

### 2026-04-09 — P0-P4 zaro hardening (felhasznaloi korrigalas)

**Rogzitve**: `105_AIFLOW_v2_P0_P4_HARDENING_RECORD.md`

- **P0 Statusz**: `100_b/c/d_*` status "AKTIV" → "FINAL / SIGNED OFF (v2.0)"
- **P0 Readiness**: `100_*/103_*/104_*` ketlepcsos readiness (Phase 1 impl-ready NOW, full operational after 100_e+100_f)
- **P1 Capacity Planning**: Letrehozas `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` (hardware + cost model)
- **P1 HITL Workload**: Letrehozas `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` (review queue + SLA + bulk UI)
- **P2 Multi-tenant isolation**: `103_*` Section 6.6-6.10 kibovites (object storage, audit log, review task, admin UI scope)
- **P2 Rollback matrix**: `100_d_*` Section 12 uj (18 hibaszituacio decision matrix + write freeze + restore)
- **P3 Archival failure path**: `101_*` N11b (QuarantineManager) + N11c (RetentionPolicy + PDFAProfileSelector)
- **P4 Acceptance + CI**: `103_*` Section 9.5 uj (backward compat + tenant isolation + migration + routing reproducibility)
- **Letrehozas**: `105_AIFLOW_v2_P0_P4_HARDENING_RECORD.md` (letteris a valtozasokrol)
- Frissites: `104_*` Section 1 dokumentum-set 11 darabra (+100_e, +100_f, +105_)
- Frissites: `104_*` Section 2 olvasasi sorrend bovites
- Frissites: `104_*` Section 12 (jelen szakasz)

### 2026-04-09 — Final egysegesites (elso kor)

- Letrehozas: `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` (jelen dok.)
- Frissites: `100_*` status "TERVEZET" → "ELFOGADVA" (v2.0)
- Frissites: `100_*` Section 7 Phase 1 bontas 1a/1b/1c/1.5-re
- Frissites: `100_*` Section 11 hivatkozasok bovitese
- Frissites: `100_*` Section 13 legkozelebbi lepes update
- Frissites: `101_*` status "TERVEZET" → "ELFOGADVA" (v2.0)
- Frissites: `101_*` N6 + N7 + R5 — 103_ Section 4-6 kibovitesi utalasok
- Frissites: `101_*` Phase 1/2 bontas 1a/1b/1c/1.5 + 2a/2b/2c/2d/2e-re

### 2026-04-08 (1. + 2. review ciklus)

- Letrehozas: `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` (v1.0 draft)
- Letrehozas: `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` (v1.0 draft)
- Letrehozas: `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` (enterprise review)
- Letrehozas: `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` (Must fix #1)
- Letrehozas: `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` (Must fix #2)
- Letrehozas: `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` (Must fix #3)
- Letrehozas: `103_AIFLOW_v2_FINAL_VALIDATION.md` (sign-off + kibovitesek)
- Hozzaadas: `100_*` Section 2.A ADR-1 (CrewAI core REJECTED)
- Hozzaadas: `101_*` N22b CrewAI Step adapter experiment

---

## 13. Legkozelebbi lepes

**Most:**
1. Olvasd el a teljes dokumentum-setet a Section 2 olvasasi sorrend szerint
2. Customer notification draft elokeszites (`100_d` Section 9.1)
3. Phase 1a session prompt letrehozasa (`01_PLAN/session_XX_v1_4_0_phase_1a_kickoff.md`)

**Sprint B (v1.3.0) befejezese utan:**
1. Phase 1a branch letrehozas (`feature/v1.4.0-phase-1a-foundation`)
2. Pre-migration backup
3. Phase 1a sprint indulas a Section 6 checklist kovetesevel

**Phase 1 acceptance utan:**
1. `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` letrehozasa
2. `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` letrehozasa
3. Phase 1.5 (Vault + self-hosted Langfuse) kickoff

---

## 14. Dokumentum integritas

**Kereszt-hivatkozas ellenorzes (a terv-seten belul, P0-P4 hardening utan):**

| Dokumentum | Hivatkozott reszek | Statusz |
|-----------|-------------------|---------|
| `104_*` (jelen) → `100_*` | Section 2.A ADR-1, Section 7 Phase, Section 11 | OK |
| `104_*` → `100_b_*` | Domain contracts | OK |
| `104_*` → `100_c_*` | State machines | OK |
| `104_*` → `100_d_*` | Migration playbook + rollback matrix (Section 12) | OK |
| `104_*` → `100_e_*` | Capacity planning | OK |
| `104_*` → `100_f_*` | HITL workload | OK |
| `104_*` → `101_*` | Komponens reszletes + N11b/N11c | OK |
| `104_*` → `103_*` | Section 3 Phase, Section 4-6 + 6.6-6.10 multi-tenant, Section 9.5 P4 CI, Section 12 sign-off | OK |
| `104_*` → `105_*` | P0-P4 hardening record | OK |
| `100_*` → `100_b/c/d_*` | Frissitett v2.0-ban | OK |
| `100_*` → `100_e_*` | Full operational readiness ref | OK |
| `100_*` → `100_f_*` | Full operational readiness ref | OK |
| `100_*` → `103_*` | Phase 1 bontas utalas | OK |
| `100_*` → `105_*` | P0 readiness + hardening record | OK |
| `100_d_*` → `103_*` | Section 12.6 rollback rehearsal → Section 9.5 P4 | OK |
| `100_e_*` → `101_*` | Parser/embedder komponensek | OK |
| `100_e_*` → `103_*` | Section 4.7 cost-aware routing | OK |
| `100_f_*` → `100_b_*` | ReviewTask Pydantic | OK |
| `100_f_*` → `100_c_*` | ReviewTask state machine | OK |
| `100_f_*` → `100_e_*` | Prometheus metricok ref | OK |
| `101_*` → `103_*` | N6 + N7 + R5 kibovitesi utalasok | OK |
| `101_*` → `100_b_*` | N1 IntakePackage | OK |
| `101_*` → `100_c_*` | State machine hivatkozas | OK |
| `101_*` → `100_d_*` | Backward compat | OK |
| `101_*` N11b/N11c → `103_*` | Compliance integration | OK |
| `103_*` → `100_b_*` | Contract hivatkozas | OK |
| `103_*` → `100_d_*` | Migration + rollback | OK |
| `103_*` → `105_*` | P2/P4 hardening source | OK |
| `105_*` → mind | Letteris a valtozasokrol | OK |
| `106_*` → `100_b_*` | Contract forras (Day 1-5) | OK |
| `106_*` → `100_c_*` | State machine forras (Day 2) | OK |
| `106_*` → `100_d_*` | Migration + rollback (Day 3, Day 13-14) | OK |
| `106_*` → `101_*` | N3/N5/N6/R13 (Day 4-14) | OK |
| `106_*` → `103_*` | Section 3, 5, 9 (acceptance) | OK |
| `106_*` → `104_*` | Master index back-ref | OK |

**Konzisztencia statusz:** PASS (minden fontos kereszt-hivatkozas mukodik, P0-P4 hardening + 106_ Phase 1a guide utan)

---

> **Vegleges (ketlepcsos readiness):**
>
> 1. **Phase 1 implementation-ready (NOW):** Ez a master index egyseges belepesi pont
>    az AIFlow v1.3.0 → v2.0.0 refinement-hez. A teljes terv-set **ELFOGADVA** (sign-off
>    2026-04-08) es **Phase 1a (v1.4.0) sprint indulasra kesz**. A P0-P4 zaro hardening
>    korrekciok a `105_*`-ben rogzitve.
>
> 2. **Full operational readiness (Phase 2 elott):** A `100_e_AIFLOW_v2_CAPACITY_PLANNING.md`
>    es `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` dokumentumok lezarasa utan a rendszer
>    teljes **customer-deployable** minosites. A Phase 2 indulas elott mindket dokumentum
>    sign-off-ja kotelezo.
>
> A Sprint B (v1.3.0) folyamatban NEM blokkolt. A refinement a v1.4.0 sprint-tel
> kezdodik, amint a Sprint B befejezodik.
