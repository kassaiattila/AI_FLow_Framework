# AIFlow v2 — First Review Cycle (Enterprise Felulvizsgalat)

> **Verzio:** 1.0
> **Datum:** 2026-04-08
> **Statusz:** AKTIV — felulvizsgalat alatt
> **Tipus:** Enterprise architectural review (1. ciklus)
> **Reviewer szerep:** senior enterprise solution architect + lead Python platform engineer + AI systems architect + DevOps architect + compliance-aware document processing expert
> **Vizsgalat tárgya:** `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` + `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md`
> **Kovetkezo:** `103_AIFLOW_v2_FINAL_VALIDATION.md` (2. ciklus, sign-off)
> **Forras:** felhasznaloi review prompt (2026-04-08)

> **Megjegyzes a stilusra:** Ez a dokumentum **NEM redesign**. NEM tervez uj architekturat,
> NEM javasol technologiacseret puszta modositasi vagybol. A celja a 100_/101_ refinement terv
> minosegi javitasa, kockazati pontok azonositasa, kiegeszitesi javaslatok strukturalt
> rogzitese. Enterprise review hangnemben.

---

## 1. Rovid osszbenyomas

A 100_ + 101_ refinement terv **erosen indul, magas szakmai szintu, es valoban refinement-szellemben** maradt.
A jelenlegi AIFlow magjat (Step + Workflow + Pipeline + Skill System) **megorzi**, csak provider
absztrakcioval, intake package modellel, policy engine-nel es archival pipeline-nal **kiegesziti**.
A `100_` Section 10 ("Mit NEM csinalunk") + a Section 4.4 ("Kivaltando elemek") explicit fegyelemmel
hatarolja a scope-ot.

**Fo erosseg:** A terv **architekturalis disciplinaja** — minden uj komponens (R/N/K-azonosito)
indoklassal jar, a fixed technologiai irany kovetese explicit (Section 2.1), es az
ADR-1 (CrewAI core orchestrator REJECTED) szakmaitag indokolt.

**Fo kockazat:** A terv **3 területen aluldefiniált** — (1) **contract-first dokumentumok**,
(2) **state lifecycle modellek**, (3) **migration + backward compatibility playbook**.
Ezek hianya nelkul a Phase 1 implementacio kockazatos: kompromissziosan ket elteltl szinten csapva
le **specifikalas helyett** kerul code-ba.

A Phase 1 task-lista (10+ task) **tulterhelt**, megoszthatonak (1a/1b/1c) tunik. A routing engine
governance, HITL workload, es Vault prioritas tovabbi pontositast igenyel.

---

## 2. Eros pontok

### 2.1 Architekturalis fegyelem

- **Refinement fegyelem fenntartva**: A 100_ Section 10 ("Mit NEM csinalunk") explicit korlatozas,
  a Section 4 (Megorzendo / Refinement / Csere / Hozzaadas) tablazatos felbontas — **fontos rendet
  visz a tervbe**.
- **Komponens-azonosito rendszer (R/N/K-szeria)** — kovetheto, **valodi requirements traceability**.
- **Fixed technologiai irany kovetese** (Section 2.1) — NEM cseralja a meglevo mukodot random
  alternativaval; a `document_pipeline.md` rogzitett iranya teljes mertekben kovetve van.
- **ADR-1 dokumentum** — A CrewAI core orchestrator dontes szakmailag indokolt, 18 ervet
  (15 architekturalis + 3 uzleti) felsorol, **defendable**.

### 2.2 Single-codebase elv

- A two-profile + single-codebase modell **realisztikus**, mert a meglevo `instance_*.py` alapra
  epul (28_MODULAR_DEPLOYMENT mar elkezdte a multi-instance modellt).
- A `tenant_override` mechanizmus megvan, csak ki kell terjeszteni `policy_override`-tal (R13).
- A `policy/engine.py` parameter szet (Section 6) **30+ explicit parameter** — eleg granular.
- **Tilos a code-fork rule** — explicit megfogalmazva, betartathato CI/CD lint-tel.

### 2.3 Provider absztrakcio

- A jelenlegi 21 adapter mar **kozeli a provider modellhez** — refactor szukseges, NEM rewriter.
- Az `Embedder Provider` (BGE-M3 / e5 / Azure OpenAI) **fix iranya** kompatibilis a meglevo
  `LLMClient.embed()` interface-szel — wrappolas opcio.
- A `routing/multi_signal_router.py` (N7) — KRITIKUS uj komponens, de a baseline `attachment_processor.py`
  3-retegu logikajara epit, NEM nullabolre.

### 2.4 Compliance + governance kezdemenyek

- **Profile A** (cloud-disallowed) explicit felsorolt kotelezo komponensekkel.
- **PII redaction gate** az embedding elott — KRITIKUS, jol pozicionalt (N16).
- **veraPDF explicit validacio** (NEM assumed PDF/A status) — fontos compliance pont.
- **Confidence calibration kiterjesztese** (B3.5 minta) — a meglevo viv mut altalanositasa.

### 2.5 Phase ordering

- **Phase 1 (Critical) → Phase 2 (Architectural) → Phase 3 (Governance) → Phase 4 (Optional)**
  szakmailag korrekt sorrend.
- **Sprint B (v1.3.0) NEM blokkolva** — Phase 1 a v1.4.0 sprintben, NEM most.

---

## 3. Fo eszrevetelek

> Az alabbi eszrevetelek **kritikus, de konstruktiv** szakmai felulvizsgalat eredmenyei.
> Mindegyiknel **konkret problema + javasolt megoldas**.

### 3.1 Contract-first hianyzasa (KRITIKUS)

**Problema:**
A 100_ Section 4.3-ban a 25 uj komponens listazva van (N1-N25), de a **kozponti domain modellek
formalis Pydantic szerzodesei** csak reszben szerepelnek. A 101_ N1-ben az `IntakePackage` Pydantic
mintat ad, de a tobbi 12 kulcs domain entity (lasd alabb) **csak utalas** szintjen letezik.

**Hianyzo formal contractok:**

| # | Domain entity | Hol szerepel | Hol hianyzik | Sulyozas |
|---|--------------|-------------|--------------|----------|
| 1 | `IntakePackage` | 101 N1 reszletes | OK | — |
| 2 | `IntakeFile` | 101 N1 reszletes | OK | — |
| 3 | `IntakeDescription` | 101 N1 reszletes | OK | — |
| 4 | `RoutingDecision` | 101 N7 minta | hianyos: signals_used schema, fallback_chain audit | Kotelezo |
| 5 | `ParserResult` | 101 R2 hivatkozas | NINCS reszletes Pydantic | Kotelezo |
| 6 | `ClassificationResult` | 101 R6 hivatkozas | NINCS reszletes Pydantic | Kotelezo |
| 7 | `ExtractionResult` | 101 R4 reszletes (uj field-ek) | reszben | Kotelezo |
| 8 | `ArchivalArtifact` | 101 N11/N12 hivatkozas | NINCS Pydantic | Kotelezo |
| 9 | `ValidationResult` (veraPDF) | 101 N12 reszletes | OK | — |
| 10 | `EmbeddingDecision` | 101 R5/N16 hivatkozas | NINCS Pydantic | Kotelezo |
| 11 | `ReviewTask` | meglevo HumanReview, NEM definialva ujra | hianyos kiterjesztes IntakePackage-rel | Kotelezo |
| 12 | `LineageRecord` | 101 N17 reszletes | OK | — |
| 13 | `ProvenanceMap` | 101 N18 hivatkozas | NINCS Pydantic | Kotelezo |

**Hatas:**
A Phase 1 implementacio NEM start-elheto contractok nelkul. Az adapter shape drift kockazata
magas, mert minden komponens sajat schemaval **valoszinuleg** improvizal.

**Javaslat (Must fix):**
Egy uj dokumentum letrehozasa: **`100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md`** vagy a 101_-en belul
egy uj **Section 0: Domain Contracts**. 13 kulcs Pydantic modell teljes kodban,
**MIELOTT** barmely komponenst implementaljanak.

### 3.2 State lifecycle modell hianya (KRITIKUS)

**Problema:**
A terv soha nem definialja, hogy egy `IntakePackage` melyik allapotban lehet, milyen atmenetekkel.
Hasonloan: `SourceFile`, `ExtractionResult`, `ArchivalArtifact`, `ReviewTask`, `Embedding` — egyik
sem rendelkezik **explicit state machine**-nel.

**Konkret peldak:**

- `IntakePackage`: lehet `received → normalized → routed → parsed → classified → extracted → reviewed → archived`?
  Vagy `received → failed`? `received → ambiguous → manual_review → resolved`?
  **NEM definialt.**
- `ArchivalArtifact`: `created → validating → valid_pdfa → archived` vs. `created → validating → INVALID → quarantine`?
  **NEM definialt.**
- `ReviewTask`: `pending → assigned → in_progress → resolved → escalated`? SLA mikor kerul play-be?
  Reszben definialt a meglevo `HumanReviewService`-ben, de a multi-source intake bovitesi nem mar.

**Hatas:**
- DB schema migration nem dokumentalt jol (alembic 030+ tabla allapot oszlop hianyzhat)
- Idempotens replay nem garantalhato (HA egy package "in_progress"-ben akadt el, mit kell csinalni recovery-nel?)
- HITL workflow nem teljes (mikor kerul auto-escalation? mikor manual)?
- Audit trail allapotvaltozasokra epul, de **most nem allapot van** definialva

**Javaslat (Must fix):**
Egy uj dokumentum: **`100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md`** — minden 7 fo entitasra:
- Allapot enum (Pydantic Literal vagy Enum)
- Atmenet diagram (ASCII vagy Mermaid)
- Atmeneti szabalyok (mi engedett mikor)
- Recovery rule (HA elakad allapot X-ben, mi a nyitogato akcio)
- Audit hook minden atmenetnel

### 3.3 Migration + backward compatibility playbook hianya (KRITIKUS)

**Problema:**
A 101_-ben a `Backwards compat` szakaszok a komponensekben **CSAK 1-2 mondatban** kezelik a migracios
kerdest. Pl.:
- `R4` (document_extractor IntakePackage centric): "shim marad"
- `R5` (rag_engine embedder migration): "Re-embedding script mukodik"
- `R1` (email_connector wrap): "low-level fetcher marad"

A **valos migracios menet** (rolling deploy, dual-write, schema evolution) NEM dokumentalt.

**Hianyzo migracios elemek:**

| # | Tema | Jelenlegi | Mi kell |
|---|------|----------|---------|
| 1 | Existing pipeline YAML kompatibilitas | nem reszletezve | Backward compat shim layer + lint check |
| 2 | DB migracios sorrend (alembic 030-035) | csak felsorolt | Sorrend + dependency + rollback path |
| 3 | Embedding re-migration (1536 → 1024 dim) | "script mukodik" | Dual-collection elv: regi + uj parhuzamos, atallasi terv |
| 4 | Tenant config migration (yaml format) | nem reszletezve | Schema versioning + auto-upgrade |
| 5 | Rolling deploy stratégia | nem reszletezve | Blue-green vs canary vs feature flag |
| 6 | Legacy run + new package run egyutteles | nem reszletezve | Run table allapot mezo, kompatibilitas |

**Hatas:**
- Customer deployment kockazat: meglevo customer pipeline-jai osszetorhetnek
- Rollback path nem definialt
- Schema evolution sodro hatasa nem felmert

**Javaslat (Must fix):**
Egy uj dokumentum: **`100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md`** — komponensenkent:
- Pre-migration checklist
- Migracios script + tests
- Rollback procedure
- Customer deployment guide
- Compatibility matrix (regi pipeline + uj pipeline egyutteles)

### 3.4 Phase 1 tulterheltsege

**Problema:**
A Phase 1 tablazat (100_ Section 7 + 101_ Phase 1 task lista) **10+ task**-ot tartalmaz, melyek
mindegyike kompetent szintu komponens implementacio. Ez **egy sprint-be** nem fer be.

**Konkret szamitas:**

| Task | Komponens | Becsules (S/M/L) | Becsult sprint |
|------|-----------|---------|---------------|
| P1.1 | N1 IntakePackage + DB | M | 0.5 sprint |
| P1.2 | N2 5 source adapter | M | 0.7 sprint |
| P1.3 | N3 IntakeNormalizationLayer | S | 0.3 sprint |
| P1.4 | N4 FileDescriptionAssociator | M | 0.5 sprint |
| P1.5 | N5 PolicyEngine + 30+ parameter + profile config | M | 0.7 sprint |
| P1.6 | N6 ProviderRegistry | S | 0.3 sprint |
| P1.7 | R1 email_connector wrap | S | 0.3 sprint |
| P1.8 | R4 document_extractor IntakePackage centric | M | 0.5 sprint |
| P1.9 | R13 SkillInstance policy override | S | 0.2 sprint |
| P1.10 | R12 invoice_automation_v2 multi-source pelda | S | 0.3 sprint |
| P1.X | Acceptance E2E + dokumentacio | M | 0.5 sprint |
| **OSSZESEN** | | | **~5 sprint** |

**Hatas:**
A v1.4.0 Phase 1 nem teljesitheto egy sprintben (~3-4 hetes ciklusra szamitva). A "sprint atfutasi
ido" kockazat tul magas, csuszas kovetheto.

**Javaslat (Must fix):** Phase 1 bontasa **harom alfazisra**:

**Phase 1a — Foundation (1 sprint)**
- N1, N3, N5, N6, R13, contractok dokumentacio
- Cel: alap modellek + policy engine + provider registry + tenant override mukodik

**Phase 1b — Source adapters + association (1 sprint)**
- N2 (5 source adapter), N4 (association)
- R1 (email wrap)
- Cel: minden source-bol lehet IntakePackage-et betolteni

**Phase 1c — Refactor + acceptance (1 sprint)**
- R4 (document_extractor IntakePackage), R12 (multi-source pipeline pelda)
- E2E acceptance
- Backward compat shim layer
- Cel: meglevo invoice_finder pipeline mukodik IntakePackage-en at

### 3.5 Routing engine governance hianya

**Problema:**
A 101_ N7 (`MultiSignalRoutingEngine`) jo strukturalt szignal-listat ad (file_type, text_layer_ratio,
ocr_need, ...), de a **routing governance** (dontes audit, fallback szabalyok, signal weight kalibracio)
nem reszletes.

**Hianyzo elemek:**

| # | Tema | Hianyzas |
|---|------|----------|
| 1 | Signal weight tuning methodology | "empirikus" — NEM reszletes |
| 2 | Routing decision priority hierarchy | nincs (egy prioritas vs masik?) |
| 3 | All-providers-unavailable fallback | nincs (ha senki nem tudja a file-t parsolni, mi a vegso ut?) |
| 4 | Routing audit query interface | nem leirt (`GET /api/v1/routing/decisions/{package_id}`?) |
| 5 | Routing decision human override | nem leirt (lehet-e manual kerni egy specifikus parser-t?) |
| 6 | Routing confidence | a `RoutingDecision.confidence` van, de mit jelent? Hogyan szamol? |
| 7 | Cost-aware routing (Profile B) | nincs (Azure DI dollar — mikor kerulendo?) |

**Hatas:**
- Routing engine implementacio NEM start-elheto governance specifikacio nelkul
- Compliance auditorok kerdezni fognak: "Miert valasztotta a rendszer az Azure DI-t?" — a `RoutingDecision.reason` mezonek **strukturaltnak** kell lennie

**Javaslat (Must fix):** Routing engine reszletes specifikacio kibovites a 101_ N7-ben:
- Signal weight registry (per-tenant overridable)
- Priority hierarchy (compliance > cost > latency > accuracy?)
- Failover fallback chain (ha all-fail → manual review)
- Audit query API
- Human override flag (NEM auto-only)
- Routing confidence calculation (rule-based + signal score weighted)

### 3.6 Provider abstraction tul magas szinten

**Problema:**
A 100_ Section 4.3 N6 (`ProviderRegistry`) es 101_ N6 csak felsorolja, hogy 4+ provider tipusra
(parser, classifier, extractor, embedder) lesz registry. A **konkret interface contracts** nincsenek
specifikalva.

**Adapter shape drift kockazat:**
- ParserProvider: melyik metodusokat **kotelezo** implementalni? (`parse(file_path) → ParsedDocument`?)
- ClassifierProvider: text-only vs visual? Mi a kozos interface?
- EmbedderProvider: dimensions, batch_size, multilingual support — kotelezo metadata?
- ExtractorProvider: per-doc-type config kotodes mikent biztositott?

Ha 4 provider tipus 5+ implementaciojat (parser: PyMuPDF, Docling, DoclingVLM, AzureDI, ...) **kulonbozo
shape**-pel implementaljak, akkor a registry NEM mukodik egysegesen.

**Javaslat (Must fix):** A 101_ N6-ban kibovites:
- 4 provider tipus formal `ABC` (Pydantic-vel + abstract metodusok)
- Interface contract teszt (every provider must pass `test_provider_contract.py`)
- Provider metadata (Pydantic): name, version, supported_types, speed_class, gpu_required, cost_class

### 3.7 Compliance + archival nem kovet teljes

**Problema:**
A 100_ N11 + N12 (Gotenberg + veraPDF) leirja a happy path-ot, de a **failure path** nem.

**Hianyzo elemek:**

| # | Tema | Hianyzas |
|---|------|----------|
| 1 | veraPDF FAIL → quarantine | nem definialt |
| 2 | Gotenberg conversion FAIL → fallback parser? | nem definialt |
| 3 | Intermediate artifact (Gotenberg konvertalas alatt) | nem definialt (memoriaban? local fs? cleanup?) |
| 4 | Retention policy archived files-ra | nem definialt |
| 5 | Audit log retention | nem definialt |
| 6 | PDF/A profile valasztas tenanti override | nem definialt |
| 7 | veraPDF version pinning + reproducible | nem definialt |

**Hatas:**
- Compliance auditor a retention policy-t **kotelezoen** kerdezi
- Failure path nelkul nem audit-ready

**Javaslat (Should fix):** A 101_ N11 + N12-ben kibovites + uj komponens:
- N11b: `archival/quarantine.py:QuarantineManager` — INVALID PDF/A files external storage-ba
- N11c: `archival/retention_policy.py:RetentionPolicy` — compliance retention rules
- Failure path diagram

### 3.8 GPU + capacity reality check hianya

**Problema:**
A 101_ R6/N9/N10 (Qwen2.5-VL, Docling VLM, BGE-M3) GPU dependency-t emlit, de a **reality check**
hianyzik:
- VRAM kovetelmeny taablazat
- Throughput target (oldal/sec, dokumentum/sec)
- GPU vs cloud cost osszevetes
- Profile A maximum volume cap GPU nelkul

**Konkret szamok hianya:**

| # | Komponens | VRAM | Speed | Cost |
|---|-----------|------|-------|------|
| Qwen2.5-VL-7B FP16 | ~14 GB | ~3-5 oldal/sec | NVIDIA A10 ~$1/h |
| Qwen2.5-VL-7B INT4 | ~7 GB | ~2-3 oldal/sec | NVIDIA T4 ~$0.5/h |
| BGE-M3 (multilingual) | ~2 GB | ~50-100 sentence/sec | CPU OK, GPU jobb |
| Docling VLM | ~10 GB | ~1-2 page/sec | varies |

**Hatas:**
- Customer hardware procurement bizonytalansag
- Profile A capacity planning bizonytalan
- Cost modeling helytelen

**Javaslat (Should fix):** Egy uj dokumentum: **`100_e_AIFLOW_v2_CAPACITY_PLANNING.md`** vagy egy
extra szekcio a 101_-ben N9/N10 alatt:
- Hardware kovetelmeny tablazat
- Performance benchmark targets
- Profile A GPU-mentes maximum volume (text-only PDF use case)
- Profile A GPU + maximum volume

### 3.9 HITL workload tervezes hianya

**Problema:**
A multi-source intake **jelentosen noveli** a low-confidence + ambiguous + validation-failed esetek
volument:
- Multi-file package: file ↔ description association ambiguity
- Cross-document context: ellentmondas eseten
- Routing decision low-confidence
- veraPDF validation failure
- Confidence calibration treshold ala kerul

**Hianyzo elemek:**

| # | Tema | Hianyzas |
|---|------|----------|
| 1 | Review queue capacity model | nem definialt |
| 2 | Per-tenant SLA | nem definialt |
| 3 | Reviewer assignment strategy | nem definialt (round-robin? specialist?) |
| 4 | Review priority queue | nem definialt (kritikus invoice vs HR doc) |
| 5 | Auto-escalation rules | nem definialt (mi tortenik 24h utan?) |
| 6 | Bulk review UI | nem definialt |
| 7 | Reviewer fatigue / cognitive load | nem definialt |

**Hatas:**
- A meglevo HumanReviewService kapacitasa rosszul becsult
- A B7 Verification Page v2 (Sprint B, mar mukodo) NEM tervez bulk review-ra

**Javaslat (Should fix):** Egy uj dokumentum: **`100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md`**:
- Workload becsules (% of intake → review)
- Capacity model
- SLA templates
- Reviewer assignment algorithm
- Bulk review wireframe (Phase 3 Sprint B7 follow-up)

### 3.10 Vault prioritas-konfliktus

**Problema:**
A 100_ Section 7 (Phase 3) Vault-ot Phase 3-ba teszi (R8/N21). De a 100_ Section 4.1 ("Megorzendo")
sorolja a JWT RS256-ot mint production-ready elemkent. Ha a Phase 1 (v1.4.0) **valamelyik prod
deploy szambol** ad — pl. egy customer Profile A-ban — akkor a Vault MAR Phase 1.5-ben kell.

**Konfliktus:**
- "Production-ready" allitas a Section 4.1-ben
- Vault prod impl Phase 3 (v1.6.0) — kb. 6+ honap utan
- Profile A "regulalt iparag" — a Vault hianya **compliance fail**

**Javaslat (Should fix):** Vault impl atvitele Phase 1 vagy Phase 1.5-be:
- Phase 1.5 sprint (v1.4.5): `R8/N21` Vault prod impl
- Indok: customer-deployable v1.4.0 utan kotelezo

### 3.11 Self-hosted Langfuse Profile A-ban

**Problema:**
A 100_ Section 9 Q1 (Open Question): "Profile A air-gapped eseten engedelyezhete a Langfuse SaaS
prompt SSOT?" — default: "Self-hosted Langfuse opcio (Phase 3)".

DE: a Profile A elve szerint **CLOUD AI DISALLOWED**. A Langfuse SaaS = cloud. Tehat **Phase 1-ben
mar nem mukodik a Profile A**, ha a Langfuse SaaS-ot hasznaja.

**Hatas:**
- Profile A v1.4.0 deployment NEM lesz lehetseges Self-hosted Langfuse nelkul
- A Phase 3-ba tett "self-hosted Langfuse opcio" tul keson

**Javaslat (Should fix):** Self-hosted Langfuse atvitele Phase 1.5-be (kotelezo Profile A-ra):
- `infra/langfuse/docker-compose.yaml` — self-hosted Langfuse
- Profile A config: `LANGFUSE_HOST=https://langfuse.internal`
- Phase 1.5 acceptance: Profile A teljes pipeline self-hosted Langfuse-szal

### 3.12 Re-embedding migracios cost becsles hianya

**Problema:**
A 101_ R5 + N13 (BGE-M3 embedding migration) emliti a re-embedding kockazatot:
- Vector dimenzio valtozas (1536 → 1024)
- Existing collection-ok atallas

DE: a **konkret cost** + **idotartam** + **downtime impact** nem becsult.

**Becsles peldaul (csak example):**
- Egy customer 100k chunk
- BGE-M3 GPU-n 100 chunk/sec → 1000 sec ≈ 17 perc
- Cost: ~$0.30 GPU time
- DB downtime: 0 (dual-collection)

**Javaslat (Nice to have):** A 101_ R5-ben kibovites:
- Re-embedding cost calculator (chunk count, model, hardware)
- Migration playbook (dual-collection elv)
- Customer downtime budget

### 3.13 Multi-tenant data isolation

**Problema:**
A jelenlegi `instances/{customer}/` modell egy fizikai customer = egy konfig modell.
De a Phase 1 multi-source intake utan **egy kozos vector store** (pgvector) tobb tenant adatat
tartalmazza. **Tenant isolation a vector store-ban hogyan biztositott?**

**Hianyzo elemek:**

| # | Tema | Hianyzas |
|---|------|----------|
| 1 | Collection ID separation per tenant | nincs explicit |
| 2 | Cross-tenant query prevention | nincs explicit |
| 3 | Tenant-aware embedding namespace | nincs |
| 4 | Audit log tenant filter | nincs |

**Javaslat (Must fix):** A 101_ R5 + N6-ban:
- Collection ID format: `{tenant_id}_{collection_name}`
- `RAGEngine.query(collection_id, ...)` mindig tenant-aware
- DB constraint: collection_id MUST start with tenant_id
- Test: cross-tenant query prevention

### 3.14 Cost attribution per-tenant

**Problema:**
A meglevo cost_records tabla per-team, de **per-tenant** lebontas a multi-source intake utan
nem dokumentalt (a `team_id` ≠ `tenant_id`).

**Javaslat (Should fix):** `cost_records` schema:
- `tenant_id` mezo (mar van vagy uj migration)
- `provider_name` mezo (parser/embedder/...)
- API: `GET /api/v1/costs/by-tenant/{tenant_id}`

### 3.15 ADR-1 controlled experiment metrika beta-bizalom

**Problema:**
A 100_ ADR-1 + 101_ N22b kettos `>=10% jobb minoseg` es `<=50% drágább` threshold-ot ad. **De ezeket
hogyan merik?**
- "Accuracy vs golden dataset" — melyik dataset?
- "Confidence calibration" — milyen baseline?
- "Hallucinacio rate <= 5%" — mi a baseline?

**Javaslat (Nice to have):** A 101_ N22b-ben kibovites:
- Pontos golden dataset path (`tests/golden_datasets/{specialist}.yaml`)
- Baseline metrika (a jelenlegi specialist eredmenyei)
- Statistical significance testing methodology (chi-square / paired t-test?)

---

## 4. Kiegeszitesi javaslatok

### 4.1 Uj dokumentumok (Must fix → Should fix prioritasban)

| # | Dokumentum | Tartalom | Mikor |
|---|-----------|----------|-------|
| 1 | `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` | 13 kulcs Pydantic modell teljesen | Phase 1 indulas elott |
| 2 | `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` | 7 entitas state machine | Phase 1 indulas elott |
| 3 | `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` | Migration + backward compat | Phase 1 indulas elott |
| 4 | `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` | GPU/CPU/storage | Phase 2 indulas elott |
| 5 | `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` | Review queue + SLA | Phase 1 acceptance utan |

### 4.2 101_ kibovitesek (komponensenként)

| Komponens | Jelenlegi | Kibovites |
|-----------|-----------|-----------|
| N5 PolicyEngine | parameter lista | hierarchikus override (profile → tenant → instance → runtime) |
| N6 ProviderRegistry | abstract class | 4 ABC + contract test framework |
| N7 RoutingEngine | signal lista | governance: priority, fallback, audit query, override |
| R4 document_extractor | uj method | shim + DB migration sorrendt |
| R5 rag_engine | provider parameter | dual-collection migration playbook |
| N22b CrewAI experiment | A/B teszt | metrika definicio + golden dataset path |

### 4.3 Phase 1 ujraosztas

| Phase | Sprint | Tartalom |
|-------|--------|----------|
| 1a | v1.4.0 | Foundation: contractok + state model + N1 + N3 + N5 + N6 + R13 |
| 1b | v1.4.1 | Source adapters: N2 (5 db) + N4 + R1 + email_connector wrapping |
| 1c | v1.4.2 | Refactor + acceptance: R4 + R12 + 10 processing flow E2E PASS |
| 1.5 | v1.4.5 | Vault prod (R8/N21) + Self-hosted Langfuse — Profile A capable deploy |

### 4.4 Phase 2 racsolas

| Phase | Sprint | Tartalom |
|-------|--------|----------|
| 2a | v1.5.0 | Routing engine (N7) + PyMuPDF4LLM (N8) + Docling provider adapter (R2) |
| 2b | v1.5.1 | Docling VLM (N9) + Qwen25 VL (N10) + R6 visual classifier kiegeszites |
| 2c | v1.5.2 | Embedder providers (R5/N13/N14/N15) + RedactionGate (N16) + re-embedding migration |
| 2d | v1.5.3 | Archival: Gotenberg (N11) + veraPDF (N12) + quarantine + retention |
| 2e | v1.5.4 | Phase 2 acceptance: 10 processing flow E2E + Profile A/B teljes |

---

## 5. Tovabbi vizsgalando szempontok (sign-off elott)

> Az alabbi temak NEM blokkolnak Phase 1 indulas elott, de a `103_*` 2. ciklus elott
> el kell donteni.

### 5.1 Compliance + auditor felkeszules

- [ ] Customer compliance officer interview (Profile A elvarasok)
- [ ] PDF/A profile (1a/2b/3b) per-customer override
- [ ] Audit log retention (default 7 ev?)
- [ ] DPIA (Data Protection Impact Assessment) Profile A-ra
- [ ] PII embedding policy review (Q2 nyitva 100_-ben)

### 5.2 Tenant model

- [ ] Multi-tenant SaaS vs on-prem per-customer (Q3 nyitva)
- [ ] Tenant-level RBAC granularitas
- [ ] Cross-tenant audit isolation
- [ ] Customer onboarding pipeline

### 5.3 Operational

- [ ] Backup + disaster recovery (PostgreSQL + Redis + object storage)
- [ ] CI/CD per-profile suite (Profile A vs B kulon teszt)
- [ ] Customer deployment guide (rolling update)
- [ ] Incident response playbook

### 5.4 Technologiai

- [ ] vLLM upgrade ciklus tervezes
- [ ] BGE-M3 vs e5-large benchmark valos magyar adattal
- [ ] PyMuPDF4LLM license check (AGPL kockazat)
- [ ] Gotenberg license check
- [ ] Microsoft GraphRAG license check (Phase 4)

### 5.5 Cost + business

- [ ] Cost model per-tenant (Profile A vs B)
- [ ] SLA templates per-tier (silver/gold/platinum)
- [ ] Customer cost attribution dashboard
- [ ] Margin calculation Profile A vs B

### 5.6 Free-text association policy

- [ ] N4 association mode (Q4-Q5 nyitva 100_-ben)
- [ ] Default LLM model for association (cost!)
- [ ] Manual review fallback frequency target

### 5.7 Routing tuning

- [ ] Signal weight kalibracios methodology (offline vs online)
- [ ] Routing decision review tool (auditor UI)
- [ ] Cost-aware routing (Profile B Azure DI dollar limit)

---

## 6. Prioritasi bontas

### 6.1 Must fix (sign-off elott KOTELEZO megoldani)

| # | Megnevezes | Eszrevetel | Akcio |
|---|-----------|------------|-------|
| 1 | Contract-first dokumentum | 3.1 | Uj dokumentum: 100_b_DOMAIN_CONTRACTS.md |
| 2 | State lifecycle modell | 3.2 | Uj dokumentum: 100_c_STATE_LIFECYCLE_MODEL.md |
| 3 | Migration playbook | 3.3 | Uj dokumentum: 100_d_MIGRATION_PLAYBOOK.md |
| 4 | Phase 1 ujraosztas | 3.4 | 100/101 frissites: Phase 1a/1b/1c |
| 5 | Routing engine governance | 3.5 | 101 N7 kibovites |
| 6 | Provider abstraction contract | 3.6 | 101 N6 kibovites (4 ABC + contract test) |
| 7 | Multi-tenant data isolation | 3.13 | 101 R5 + N6 kibovites (collection ID format) |

### 6.2 Should fix (Phase 1 acceptance elott)

| # | Megnevezes | Eszrevetel | Akcio |
|---|-----------|------------|-------|
| 1 | Compliance + archival failure path | 3.7 | 101 N11/N12 kibovites + N11b/N11c uj |
| 2 | GPU + capacity reality check | 3.8 | Uj dokumentum: 100_e_CAPACITY_PLANNING.md |
| 3 | HITL workload tervezes | 3.9 | Uj dokumentum: 100_f_HITL_WORKLOAD_MODEL.md |
| 4 | Vault Phase 1.5 | 3.10 | 100/101 frissites: Phase 1.5 sprint |
| 5 | Self-hosted Langfuse Profile A-ra | 3.11 | 100/101 frissites: Phase 1.5 |
| 6 | Cost attribution per-tenant | 3.14 | DB schema kibovites |

### 6.3 Nice to have (Phase 2+ idejen)

| # | Megnevezes | Eszrevetel | Akcio |
|---|-----------|------------|-------|
| 1 | Re-embedding cost calculator | 3.12 | 101 R5 calculator script |
| 2 | ADR-1 experiment metrika reszletes | 3.15 | 101 N22b kibovites |
| 3 | Customer onboarding playbook | 5.2 | Phase 3 |
| 4 | License check (PyMuPDF4LLM AGPL, Gotenberg) | 5.4 | Phase 2 elott |
| 5 | n8n editor (opt) | Phase 4 | Nem blokkol |

---

## 7. Kulon kiemelt vizsgalat — 3 fontos terulet

> A felhasznaloi review prompt explicit megjelolte ezeket a teruletetket. Kulon ertekeles.

### 7.1 Contract-first implementation — **GYENGE**

**Erdemles:** A 100_ + 101_ alapjan **NEM start-elheto** Phase 1 implementacio contract-first
megkozelitessel. A 13 kulcs domain entitas Pydantic modelljei reszben szerepelnek (3-4 esetben),
de a tobbi 9-10 csak **utalas** szintjen letezik.

**Javaslat (KRITIKUS):** Phase 1 indulas elott a `100_b_*.md` dokumentum (Domain Contracts) **MUST**.

### 7.2 State transitions / lifecycle model — **HIANYZIK**

**Erdemles:** A 100_ + 101_ **EGYALTALAN nem** definialja az allapot lefolyasokat. Egy `IntakePackage`,
`ArchivalArtifact`, `ReviewTask` allapot enum-ja, atmenetei, recovery utai NEM dokumentaltak.

**Javaslat (KRITIKUS):** Phase 1 indulas elott a `100_c_*.md` dokumentum (State Lifecycle Model) **MUST**.

### 7.3 Migration + backward compatibility — **GYENGE**

**Erdemles:** A 101_ komponensekben 1-2 mondatos backward compat utalas van, de a **valos
migracios menet** (rolling deploy, dual-write, schema evolution) NEM dokumentalt. A customer
deployment kockazat magas.

**Javaslat (KRITIKUS):** Phase 1 indulas elott a `100_d_*.md` dokumentum (Migration Playbook) **MUST**.

---

## 8. Rovid zaro ajanlas

### 8.1 Mi maradhat igy

A **100_ + 101_ vazstrukturaja megorzendo**:
- Komponens-azonosito rendszer (R/N/K-szeria) — hatekony kovetes
- Refinement disciplina + "Mit NEM csinalunk" — fegyelem
- Phase 1-4 magas-szintu sorrend — szakmailag korrekt
- ADR-1 (CrewAI core orchestrator REJECTED) — defendable
- Provider absztrakcio elve + policy engine + intake package modell — alapveto helyes

### 8.2 Mit kell tisztazni elsokent (Must fix kotelezo)

1. **3 uj dokumentum letrehozasa Phase 1 indulas elott**:
   - `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` (13 Pydantic modell)
   - `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` (7 entitas state machine)
   - `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` (rolling deploy + backward compat)

2. **Phase 1 ujraosztas (1a/1b/1c)** — egyseges sprint nem fer be

3. **Routing engine governance** kibovites a 101 N7-ben

4. **Provider abstraction contract** kibovites a 101 N6-ban

5. **Multi-tenant data isolation** explicit a 101 R5 + N6-ban

### 8.3 Legfontosabb kovetkezo lepes

A `103_AIFLOW_v2_FINAL_VALIDATION.md` (2. ciklus, sign-off) **csak** azutan keszitheto,
hogy:

- A 7 Must fix tetelt megoldottuk (3 uj dokumentum + 4 in-place kibovites)
- Az 6 Should fix tetelt valasszuk be a Phase 1.5 sprintbe
- A nyitott questionek (Q1-Q10 a 100_-ben) reszben eldontottek

A 103_ ciklus celja **acceptance criteria sign-off**:
- Minden komponens MUST fix tetelei megoldottak
- Phase 1a sprint indithato (v1.4.0)
- Customer deployment terv kesz

### 8.4 Konklúzió

A 100_ + 101_ refinement terv **erosen indul, de 3 kritikus dokumentum hianyzik** ahhoz,
hogy Phase 1 indulhasson. Ha ezeket pótoljuk (~1-2 sprint extra munka), akkor a terv
**production-ready**, customer-deployable refinement-te valik.

A jelenlegi forma 7/10 — eros 8-9 lehet a Must fix tetelekkel.

---

## 9. Kovetkezo lepes

1. **Megold a Must fix tetelet (1-7)**
2. **Frissitsd a 100/101 dokumentumokat a megoldasokkal**
3. **Keszitsd el a 103_ AIFLOW_v2_FINAL_VALIDATION.md-t** (2. ciklus, sign-off)

---

> **Felulvizsgalo szignaltuk**: nincs (draft state). A 103_ ciklus elott a teljes terv-set
> revalidacioja szukseges.
