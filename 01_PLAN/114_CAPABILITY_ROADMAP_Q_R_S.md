# AIFlow capability-first roadmap — Sprint Q / R / S (2026-05-07 →)

> **Status:** APPROVED 2026-05-07, cut from `main` @ `390d4d5` (Sprint P close).
> **Predecessor:** Sprint P (v1.4.12) delivered UC3 intent classification at 4% misclass.
> **Orientation shift:** functional-operational capability tiers, not follow-up lists. Written after the Sprint P post-mortem found that UC3 intent is solved but **UC3 extraction + UC1 end-to-end + prompt-workflow ergonomy + cost-aware routing** are the next customer-visible wins.

---

## 0. Capability inventory (baseline)

| # | Capability | Ma | Operációs érettség |
|---|---|---|---|
| **A** | Funkcionális vector DB + RAG chat | `rag_engine` + pgvector + 3 embedder, **ingest** provider-aware, **query** hardcoded, 1024-dim BGE-M3 nem queryable | 🟡 részben éles |
| **B** | Számla adatpont-felismerés | `invoice_finder` + `invoice_processor` skill + Phase 1d adapter orchestration, skill-szintű teszt van, **full golden-path E2E nincs** | 🔴 működik, nincs ügyfél-oldali bizonyíték |
| **C** | Email + csatolmány intent + adatpont | Intent Sprint P után **4% misclass** ✅, **extraction pipeline nem wired** — az `invoice_processor` nem fut a UC3-ban a classifier után | 🟡 intent kész, extraction hiányzik |
| **D** | Prompt workflow (több UC, paraméterezhető) | Langfuse sync, `PromptManager` + YAML per-skill, **nincs workflow-komponálás**, **nincs UI-ból per-tenant override** | 🟡 plumbing van, ergonómia nincs |
| **E** | Költséghatékony pipeline | Cost cap (L) + pre-flight guardrail (N) + per-attachment cost (O-FU7) + docling warmup (O-FU4) + early-return (P-S132). **Routing még nem minden szinten cost-aware**. | 🟢 érett, egy finomítás van hátra |

Kulcsmegállapítás: **B és C összeköthető** az `invoice_processor` UC3-ba wiring-elésével (egyetlen új extraction step + UI card). Ez a **Q1 fő deliverable**.

---

## 1. Sprint ütemezés — fél éves ablak

```
Sprint Q (v1.5.0)  — Intent + extraction unification (C + B bridge)
Sprint R (v1.5.1)  — PromptWorkflow alapok (D)
Sprint S (v1.5.2)  — Functional vector DB teljes kör (A)
Sprint T (v1.5.3)  — Cost-aware routing escalation (E finish)
Sprint U (v1.5.4)  — Operational hardening & régi carryk (opcionális)
```

Q a legfontosabb, Q-R-S párhuzamosítható ahol a tenant-flag-ek elkülönülnek. T E-closer. U opcionális.

---

## 2. Sprint Q — Intent + extraction unification (v1.5.0 target)

### 2.1 Miért most

Sprint P UC3 intent-elt elért 4% misclass-ra (96% accuracy). A classifier tudja "ez egy `invoice_received`", **de a UC3 pipeline nem hívja meg utána az `invoice_processor`-t**, ami kinyerné az `invoice_number`, `total_amount`, `due_date`, `supplier_name`, `iban` mezőket. Az `invoice_processor` mint self-contained skill létezik, tesztelve van, de nincs wiring a UC3 adattal.

Egyetlen Q sprint két use case-t hoz látható állapotba:
- **C teljesül**: email → intent + kinyert mezők → UI kártya
- **B bebizonyosul**: a meglévő `invoice_processor` a UC1 core logikája — golden-path E2E ráfuttatva megadja UC1 first green.

### 2.2 Session terv

| Session | Scope | Acceptance |
|---|---|---|
| **S135** | Kickoff + Q scope + baseline: `invoice_processor.extract(attachment_path)` direct hívás az UC3 orchestrator-ból, ha `intent_class == "EXTRACT"` + van PDF/DOCX attachment. `workflow_runs.output_data.extracted_fields` új JSONB kulcs. Flag: `AIFLOW_UC3_EXTRACTION__ENABLED` default=false. 10+ unit + 1 integration (real PG + real docling + real OpenAI — fixture `001_invoice_march`). Plan doc `01_PLAN/115_SPRINT_Q_*`. | `extracted_fields` jelen van a flag-on path-on, 4-5 mező kinyerve, integration test zöld. |
| **S136** | UI: `EmailDetail.tsx` új **"Kinyert adatok"** card (`ExtractedFieldsCard.tsx`) + EN/HU locale. `EmailDetailResponse.extracted_fields` (optional). 1 Playwright E2E valós live stack-en (no route mock): seed → view → assert mezők láthatók. | Vizuális E2E green, tsc+ruff clean, valós dev stack ellenőrizve. |
| **S137** | UC1 `invoice_finder` golden-path E2E: 10-fixture számla korpusz (anonimizált), teljes pipeline (email/file intake → classifier → invoice_processor → HITL queue). `docs/uc1_golden_path_report.md` kép accuracy-vel. | Accuracy ≥ 80% a 10-fixture korpuszon, HITL queue megtöltődik a < threshold esetekre, E2E green. |
| **S138** | Sprint Q close — retro, PR description, CLAUDE.md numbers bump, tag `v1.5.0` queued. | PR cut `main`-re, CI 6/6 zöld, squash merge. |

### 2.3 STOP conditions

- **HARD**: Sprint P UC3 golden-path E2E regresszió (4% misclass-t ne rontsuk) → halt.
- **HARD**: `invoice_processor.extract()` költsége > $0.05 / számla a live futtatáson → rescope tenant-gated-re.
- **HARD**: S137 accuracy < 60% → UC1 korpusz kurálás szükséges, külön session.
- **SOFT**: HITL queue design skálázódik-e — dokumentálni retro-ban, ne halt-oljon.

### 2.4 Rollback

Q scope additív: 1 új flag, 1 új DB kulcs (JSONB, no migration), 1 új UI card. `AIFLOW_UC3_EXTRACTION__ENABLED=false` = Sprint P tip behaviour. S137 új E2E fixture, nincs prod hatás. Tag visszavétel egyszerű revert.

### 2.5 Success metrics

| Metric | Target |
|---|---|
| `extracted_fields` accuracy a 10-fixture számla korpuszon | ≥ 80% |
| Cost per invoice (docling + extraction LLM) | < $0.02 |
| Latency p95 per invoice extraction | < 15 s |
| UC3 4% misclass nem regreszál | `= 4% ± 0` |
| Playwright E2E live-stack-en (no route mock) | 3 új teszt (S135 integr + S136 UI + S137 golden) |

---

## 3. Sprint R — PromptWorkflow alapok (v1.5.1)

### 3.1 Mit old meg

A UC3, UC2, UC1, jövő UC4-5 skill-ek mind-mind saját prompt YAML-ekbe copy-paste-elik ugyanazokat a prompt patternt (system intro, user context, few-shot block, JSON output format). Nincs:
- workflow-komponálás (step → prompt → output → next step)
- per-tenant prompt override UI-ból
- A/B testing struktúra
- prompt-level cost tracking

### 3.2 Session terv (vázlat, részletes Sprint R kickoff-kor)

- **S139** `PromptWorkflow` Pydantic model + YAML loader + Langfuse lookup integráció
- **S140** Admin UI `/prompts/workflows` listing + detail + "test run" gomb
- **S141** 3 skill migrációja (`email_intent_processor`, `invoice_processor`, `aszf_rag_chat`) backward-compat shim-mel
- **S142** Sprint R close + tag `v1.5.1`

### 3.3 STOP conditions

- Migráció breaking-e a Sprint K UC3 golden-path-t → backward-compat shim kötelező.
- Langfuse v3 kliens kompatibilis-e a workflow bundle lookup-pal → ha nem, migráció előbb (v3→v4).

---

## 4. Sprint S — Functional vector DB teljes kör (v1.5.2)

### 4.1 Mit zár

UC2 RAG. Sprint J carry FU-1 (query-path provider registry) megoldva + per-tenant kollekció regiszter. 1024-dim BGE-M3 queryable. Heti MRR@5 mérés fixture korpuszon + dashboard.

### 4.2 Session terv (vázlat)

- **S143** `RagEngineService.query()` refaktor `ProviderRegistry`-re, `rag_collections` Alembic migration (additív, tenant_id + embedder_profile_id oszloppal)
- **S144** `/rag/collections` admin UI, per-tenant kollekció lista + MRR metric
- **S145** Scheduled nightly MRR@5 measurement script + dashboard integration
- **S146** Sprint S close + tag `v1.5.2`

---

## 5. Sprint T — Cost-aware routing escalation (v1.5.3)

### 5.1 Mit zár

E capability utolsó darabja. A meglévő plumbing már érett; a router-döntéseknek kell cost-ot nézniük.

- **S147** `PolicyEngine.pick_model_tier()` per-use-case: olcsó first (haiku / gpt-4o-mini), confidence-drop → drágább fallback
- **S148** Pipeline-szintű kumulatív budget tracker (a per-call `CostPreflightGuardrail`-en túl)
- **S149** Sprint N FU-2 (`model-tier fallback ceilings → CostGuardrailSettings`) finomítás + Grafana panel
- **S150** Sprint T close + tag `v1.5.3`

---

## 6. Sprint U — Operational hardening (opcionális, v1.5.4)

A retrospective carry-forward-ok csokorban:

- `/status` OpenAPI drift CI step (`scripts/check_openapi_drift.py` már él, csak CI-be kötni)
- Weekly 4-combo matrix measurement mint GitHub Action (Sprint P FU-2)
- `CostAttributionRepository` ↔ `record_cost` consolidation
- `CostSettings` umbrella class
- Soft-quota / over-draft semantics
- Langfuse v3→v4 server migration
- Sprint M live Vault rotation E2E

---

## 7. Validation round — kockázatok és sanity checks

| # | Kockázat | Enyhítés |
|---|---|---|
| R1 | Q1 `invoice_processor` wiring ütközhet UC3 body-label gate-tel | ✅ Nem — `attachment_features` már `output_data`-ban, extraction csak downstream step |
| R2 | R2 PromptWorkflow migráció breaking | ⚠️ Backward-compat shim kötelező + `AIFLOW_PROMPT_WORKFLOW__ENABLED` flag |
| R3 | S query-path registry visszafelé kompatibilis-e | ✅ Igen — jelenlegi hardcoded query egy alap-embedder-rel megy, registry kiterjeszti |
| R4 | Q extraction cost regresszió (minden UC3 email + extra LLM call) | ⚠️ Flag-gated + budget HARD STOP |
| R5 | Q UC3 classification regresszió | ⚠️ S135 integration test fixture 001_invoice_march misclass gate |
| R6 | Külső dep: Azure OpenAI Profile B credit blokkolt | S nem blocker (Profile A BGE-M3 működik) |
| R7 | Langfuse v4 server migration szükségessége | Csak S149 után dönthető — v3 elég Q/R/S-re |

## 8. Tech stack — mi van, mi kell

**Meglévő (nincs új adósság)**: Pydantic contracts, ProviderRegistry 5 slot, `@step` + workflow_runs, Langfuse prompt sync, Cost recorder + attribution, Alembic, 3-tier attachment processor, pgvector hybrid.

**Újonnan bevezetendő**:
- `ExtractedFields` Pydantic model + `invoice_processor.extract()` UC3 bekötése (Q)
- `ExtractedFieldsCard.tsx` UI komponens (Q)
- UC1 golden-path fixture korpusz + accuracy report (Q)
- `PromptWorkflow` Pydantic + YAML loader (R)
- `rag_collections` tábla + Alembic 046 migration (S)
- `PolicyEngine.pick_model_tier()` helper (T)

**Nincs új framework, nincs architekturális törés.**

---

## 9. Autonomous execution

Sprint Q sessions-ek `session_prompts/S135_*` → `S138_*`. Auto-sprint mode-ban egyetlen `/auto-sprint` indítja a teljes Sprint Q-t, minden session külön PR-t kap, CI-vel, squash-merge main-re a sikeres build után.

Valós tesztelési követelmény **minden session-re**:
- Unit tesztek (mockolt LLM-mel OK)
- Integration tesztek **real PostgreSQL + real OpenAI + real docling** — SOHA mock!
- Playwright E2E **valós dev stack-en** (no route-mock) — ahol UI érintett

Sprint Q close (S138) után auto-sprint megáll, és user dönt Sprint R indításáról.
