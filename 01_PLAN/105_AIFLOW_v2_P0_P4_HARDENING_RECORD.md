# AIFlow v2 — P0-P4 Hardening Record (Zaró Javitasi Csomag)

> **Verzio:** 1.0 (FINAL)
> **Datum:** 2026-04-09
> **Statusz:** AKTIV — Phase 1a kickoff elotti zaro hardening lezarasa
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
> **Forras:** Felhasznaloi korrigalo terv (2026-04-09)

> **Cel:** Rogziteni a `102_*` elso review ciklus utani zaro hardening es dokumentum-
> konzisztencia javitasokat (P0-P4). **Ez NEM uj terv**, hanem a meglevo dokumentumokba
> tett javitasok **letterlistája** es hivatkozasi pontja.

---

## 0. Hatter

A `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` 1. review ciklus **Must fix** teteleit a `103_*`
lezarta (`103_*` Section 3-6). A `103_*` sign-off ota azonban a felhasznalo 2026-04-09-en
tovabbi korrigalasi tervet adott **hardening + dokumentumkonzisztencia** cellel.

Ezek nem uj szakmai tervek, hanem:
- **P0**: Gyors dokumentumallapot javitas (status → FINAL)
- **P1**: Ket hianyzo dokumentum (100_e + 100_f)
- **P2**: Multi-tenant isolation + rollback decision matrix formalizalas
- **P3**: Archival failure path (quarantine + retention) formalizalas
- **P4**: Acceptance + CI hardening (test suite kiterjesztes)

Ez a dokumentum rogziti, hogy mely javitasok **hol** (a terv-set melyik dokumentumaban)
lettek megvalositva.

---

## 1. P0 — Dokumentumstatuszok + ketlepcsos readiness

### 1.1 Statuszegyseges (FINAL / SIGNED OFF)

| Dokumentum | Elozo status | Uj status | Hely |
|-----------|-------------|-----------|------|
| `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` | AKTIV — Phase 1 elott sign-off | **FINAL — SIGNED OFF (v2.0)** | Fejlec (2026-04-09) |
| `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` | AKTIV — Phase 1 elott sign-off | **FINAL — SIGNED OFF (v2.0)** | Fejlec (2026-04-09) |
| `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` | AKTIV — Phase 1 elott sign-off | **FINAL — SIGNED OFF (v2.0)** | Fejlec (2026-04-09) |

A `100_`, `101_`, `103_`, `104_` mar `FINAL` / `ELFOGADVA` statuszban voltak — nem igenyelt
modositast.

### 1.2 Ketlepcsos readiness megfogalmazas

Minden readiness allitas a terv-setben **ket szakaszba** lett valasztva:

1. **Phase 1 implementation-ready (NOW)** — Az osszes 100_/100_b/c/d/101_/103_/104_ dokumentum
   lehetove teszi a Phase 1a (v1.4.0) sprint inditasat.
2. **Full operational readiness (Phase 2 elott)** — A teljes customer production deployment
   csak a `100_e_*` + `100_f_*` sign-off utan tekintheto "customer-deployable" minositesnek.

**Beepitve az alabbi helyekre**:

| Dokumentum | Hely | Valtozas |
|-----------|-----|---------|
| `100_*` | Vegleges osszefoglalo (vege) | Ketlepcsos readiness bekerult |
| `103_*` | Vegleges allaspont (vege) | Ketlepcsos readiness bekerult |
| `104_*` | Vegleges (vege) | Ketlepcsos readiness bekerult |

**P0 statusz**: ✅ **TELJESITVE**

---

## 2. P1 — Ket kotelezo zaro dokumentum (Phase 2 elott)

### 2.1 `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` (uj)

**Letrehozva**: 2026-04-09

**Tartalom** (13 szekcio):
- Hardware profil kategoriak: Profile A GPU-mentes + Profile A GPU-val + Profile B
- Benchmark target matrix: parser, embedder, E2E pipeline
- Profile A GPU-mentes maximum volumen (500 dok/day soft cap, 1800 dok/day hard cap)
- Koltsegmodell: Profile A CAPEX vs Profile B OPEX, break-even analysis
- Benchmark target Phase 2c acceptance (100 HU invoice, 10K HU chunks, 1K packages)
- Capacity monitoring Prometheus metricok
- Scale-out guidance (horizontal + vertical)
- Risk items (C1-C5)
- Sign-off checklist
- Open items (C-Q1 — C-Q4)

**Hatas**: Phase 2 indulas elott **kotelezo sign-off** az architect + ops altal.

### 2.2 `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` (uj)

**Letrehozva**: 2026-04-09

**Tartalom** (13 szekcio):
- Review queue volumetria: 30-66% a multi-source intake utan (~47% atlag)
- Customer sizing guide: 100-5000 dok/day → 0.3-12 reviewer FTE
- Prioritas rendszer: CRITICAL / HIGH / MEDIUM / LOW
- Per-prioritas SLA: 5 min → 72 h resolution
- Assignment algoritmus: skill-aware round-robin
- Reviewer skill taxonomy (5 skill tag)
- Escalation rules + auto-escalation background job
- **Bulk review UI minimum kovetelmenyek** (10 MUST/SHOULD/NICE funkcio)
- UI wireframe (queue view + task detail)
- Reviewer fatigue / cognitive load management
- Training data collection
- Customer onboarding (HITL setup)
- Risk items (H1-H5)
- Sign-off checklist
- Open items (H-Q1 — H-Q4)

**Hatas**: Phase 2 indulas elott **kotelezo sign-off** az architect + product + customer
success altal.

**P1 statusz**: ✅ **TELJESITVE**

---

## 3. P2 — Multi-tenant isolation + rollback hardening

### 3.1 Multi-tenant isolation formalizalas

**Hely**: `103_AIFLOW_v2_FINAL_VALIDATION.md` Section 6 kibovites

**Uj szakaszok (6.6 - 6.10)**:
- **6.6 Object storage naming + path isolation**
  - Path format: `{tenant_id}/intake/{package_id}/files/{file_id}__{sha256}__{name}`
  - `TenantAwarePathBuilder` class
  - Cross-tenant access `PermissionDeniedError`
- **6.7 Audit log tenant filter (formalizalva)**
  - Repository layer enforcement
  - Super-admin mode explicit audit log
  - PostgreSQL row-level security policy
- **6.8 Review task query tenant scope (formalizalva)**
  - Tenant-scoped repository
  - Multi-tenant reviewer context switching
- **6.9 Admin UI scope (formalizalva)**
  - `TenantContext` + `TenantGuard` frontend
  - Tenant-aware UI oldal lista
  - `X-Tenant-ID` header minden API call-on
- **6.10 Multi-tenant isolation acceptance checklist**
  - 11 item acceptance criteria

### 3.2 Rollback decision matrix

**Hely**: `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` Section 12 (uj)

**Tartalom**:
- **12.1 Decision matrix**: 18 hibaszituacio → rollback strategy
- **12.2 Decision criteria**: 6 kerdes a strategy kivalasztasahoz
- **12.3 Decision tree**: ASCII flowchart
- **12.4 Write freeze procedure**: 5 lepes + 30 perc cap
- **12.5 Backup restore procedure**: 8 lepes + verify integrity
- **12.6 Rollback rehearsal (P4 acceptance)**: staging rehearsal elvarasok

**P2 statusz**: ✅ **TELJESITVE**

---

## 4. P3 — Archival/compliance failure path (N11b/N11c)

### 4.1 `101_` N11b — QuarantineManager (uj)

**Hely**: `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` N12 utan beepitve

**Tartalom**:
- `QuarantineReason` enum (6 ertek)
- `QuarantineRecord` Pydantic modell
- `QuarantineManager.quarantine()` + `release()` metodusok
- Compliance retention per reason (30 nap — 7 ev)
- Auto ReviewTask letrehozas
- Auto notification compliance officer-nek
- Lepesenkenti vegrehajtas + acceptance criteria

### 4.2 `101_` N11c — RetentionPolicy + PDFAProfileSelector (uj)

**Hely**: `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` N11b utan beepitve

**Tartalom**:
- `RetentionTier` enum (SHORT / STANDARD / LONG / PERMANENT)
- `RetentionRule` Pydantic modell + default rules (4 db)
- Legal basis per rule (HU Tax Act §169, GDPR, stb.)
- `RetentionPolicy.get_retention()` per tenant + doc_type override
- Background `retention_enforcement_job` (napi 2 AM cron)
- **PDF/A profile override** per-tenant + per-doc-type
  - `PDFAProfileSelector` class
  - Config: `instances/{customer}/archival_policy.yaml`
- **Intermediate artifact kezeles** (Gotenberg cleanup)
- Lepesenkenti vegrehajtas + acceptance criteria

**P3 statusz**: ✅ **TELJESITVE**

---

## 5. P4 — Acceptance + CI hardening

### 5.1 `103_` Section 9.5 kibovites (uj)

**Hely**: `103_AIFLOW_v2_FINAL_VALIDATION.md` Section 9.5 (uj szakasz)

**Tartalom**:

#### 9.5.1 Backward compat regression suite
- 6+ teszt file: `tests/regression/backward_compat/`
- CI workflow: `.github/workflows/ci-backward-compat.yml`
- Legacy pipeline YAML-ok + extraction outputs + collection snapshots fixtures

#### 9.5.2 Tenant isolation integration test suite
- 15+ teszt file: `tests/integration/security/tenant_isolation/`
- Vector store, object storage, audit log, review task, admin UI, policy, provider,
  lineage, provenance, cost, notification, HITL notification, secret manager, cache,
  rate limiter — mind tenant-scoped
- CI workflow: `.github/workflows/ci-security.yml`

#### 9.5.3 Schema migration dry-run + rollback rehearsal
- 8 teszt file: `tests/integration/migration/`
- 029 → 036 full chain upgrade + downgrade
- Seed data integrity preservation
- Staging rehearsal script: `./scripts/staging_migration_rehearsal.sh`
- CI workflow: `.github/workflows/ci-migration.yml`

#### 9.5.4 Routing decision reproducibility test
- 5+ teszt file: `tests/integration/routing/reproducibility/`
- Golden dataset: `fixtures/routing_snapshots/` (10+ szcenario)
- Determinism teszt: ugyanaz az input → ugyanaz a decision (+/- 0.01 confidence)
- Golden dataset assertion teszt

#### 9.5.5 CI orchestration
- `ci-v1-4-0.yml` master workflow
- 7 job: lint-type-unit → backward-compat → tenant-isolation → migration-rehearsal →
  routing-reproducibility → profile-a-e2e → profile-b-e2e → phase-1a-gate

#### 9.5.6 P4 acceptance checklist
- 9 item acceptance criteria

**P4 statusz**: ✅ **TELJESITVE**

---

## 6. Egyseges valtozasnaplo

### 2026-04-09 — Zaro hardening (P0-P4)

| # | Fajl | Valtozas | Szakasz |
|---|------|---------|---------|
| 1 | `100_b_*` | Status FINAL + v2.0 | Fejlec |
| 2 | `100_c_*` | Status FINAL + v2.0 | Fejlec |
| 3 | `100_d_*` | Status FINAL + v2.0 | Fejlec |
| 4 | `100_d_*` | Rollback decision matrix | Section 12 (uj) |
| 5 | `100_d_*` | Sign-off checklist bovites | Section 13 |
| 6 | `100_e_*` | **UJ dokumentum** — Capacity Planning | 13 szekcio |
| 7 | `100_f_*` | **UJ dokumentum** — HITL Workload Model | 13 szekcio |
| 8 | `100_*` | Ketlepcsos readiness | Vege |
| 9 | `101_*` | N11b QuarantineManager | N12 utan |
| 10 | `101_*` | N11c RetentionPolicy + PDFAProfileSelector | N11b utan |
| 11 | `103_*` | Multi-tenant isolation Section 6.6-6.10 | Section 6 kibov. |
| 12 | `103_*` | P4 Acceptance + CI hardening Section 9.5 | Section 9 kibov. |
| 13 | `103_*` | Ketlepcsos readiness | Vege |
| 14 | `104_*` | Ketlepcsos readiness + 100_e + 100_f + 105_ bekotes | Vege + Section 1 |
| 15 | `105_*` | **UJ dokumentum** — P0-P4 Hardening Record (jelen dok.) | Teljes |

---

## 7. Teljes terv-set vegleges allapota

### 7.1 Dokumentum-set (10 darab)

| # | Fajl | Statusz | Szerep |
|---|------|--------|--------|
| 1 | `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` | FINAL | Master index |
| 2 | `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md` | FINAL (v2.0) | Atfogo terv + ADR-1 |
| 3 | `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` | FINAL (v2.0) | 13 Pydantic contract |
| 4 | `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` | FINAL (v2.0) | 7 entitas state machine |
| 5 | `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` | FINAL (v2.0) | Migration + rollback matrix |
| 6 | `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` | **FINAL (uj)** | Hardware + cost model |
| 7 | `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` | **FINAL (uj)** | Review workload |
| 8 | `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` | FINAL (v2.0) | Komponens reszletes |
| 9 | `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` | ARCHIV | Review 1. ciklus (historikus) |
| 10 | `103_AIFLOW_v2_FINAL_VALIDATION.md` | FINAL (v2.0 + P2 + P4 kibov.) | 2. ciklus + sign-off |
| 11 | `105_AIFLOW_v2_P0_P4_HARDENING_RECORD.md` | **FINAL (uj, jelen dok.)** | Zaro hardening letteris |

**Osszesen: 11 dokumentum a vegleges terv-setben** (10 aktiv + 1 historikus).

### 7.2 Readiness status

| Szint | Statusz | Dokumentumok |
|-------|--------|--------------|
| **Phase 1 implementation-ready** | ✅ **NOW** | 100_, 100_b, 100_c, 100_d, 101_, 103_, 104_, 105_ |
| **Full operational readiness (Phase 2 elott)** | ✅ **NOW** (100_e + 100_f lezarva) | + 100_e, 100_f |
| **Phase 2 kickoff elott** | Customer compliance officer + legal + ops sign-off | Open items |
| **Phase 3 kickoff elott** | Phase 2 acceptance | — |

---

## 8. Sign-off elvarasok per dokumentum

### 8.1 Phase 1a indulas elott (most)

- [x] `100_*` architect + lead engineer sign-off
- [x] `100_b_*` architect + lead engineer sign-off
- [x] `100_c_*` architect + lead engineer sign-off
- [x] `100_d_*` architect + lead engineer sign-off
- [x] `101_*` lead engineer sign-off
- [x] `103_*` architect + compliance officer sign-off
- [ ] Customer account manager pre-migration notification sign-off
- [ ] Ops team Docker compose + CI workflow review

### 8.2 Phase 2 indulas elott (v1.5.0 elott, ~3 ho)

- [ ] `100_e_*` architect + ops sign-off (hardware procurement)
- [ ] `100_f_*` architect + product + customer success sign-off (HITL model)
- [ ] Customer compliance officer interview (Profile A)
- [ ] Legal DPIA (Profile A)
- [ ] License check (PyMuPDF4LLM AGPL, Gotenberg, veraPDF)
- [ ] GPU vendor/procurement (Profile A GPU-val deploy-ok)

---

## 9. Megoldott vs nyitott gap-ok

### 9.1 Megoldott (102_* Must + Should fix)

| Kategoria | Gap | Hol megoldva |
|-----------|-----|--------------|
| Must fix | MF1 contract-first | `100_b_*` |
| Must fix | MF2 state lifecycle | `100_c_*` |
| Must fix | MF3 migration playbook | `100_d_*` |
| Must fix | MF4 Phase 1 bontas | `103_*` Section 3 |
| Must fix | MF5 routing governance | `103_*` Section 4 |
| Must fix | MF6 provider ABC | `103_*` Section 5 |
| Must fix | MF7 multi-tenant isolation (vector store) | `103_*` Section 6.1-6.5 |
| Should fix | SF1 archival failure path | `101_*` N11b + N11c (P3 hardening) |
| Should fix | SF2 GPU + capacity reality check | `100_e_*` (P1 hardening) |
| Should fix | SF3 HITL workload tervezes | `100_f_*` (P1 hardening) |
| Should fix | SF4 Vault Phase 1.5 | `103_*` Section 3.4 |
| Should fix | SF5 Self-hosted Langfuse Phase 1.5 | `103_*` Section 3.4 |
| P2 | Multi-tenant isolation formalizalas | `103_*` Section 6.6-6.10 (P2 hardening) |
| P2 | Rollback decision matrix | `100_d_*` Section 12 (P2 hardening) |
| P4 | Backward compat regression suite | `103_*` Section 9.5.1 |
| P4 | Tenant isolation integration tests | `103_*` Section 9.5.2 |
| P4 | Schema migration dry-run | `103_*` Section 9.5.3 |
| P4 | Routing decision reproducibility | `103_*` Section 9.5.4 |

### 9.2 Nyitott (Phase 2 + Phase 3 elott megoldando)

| Kategoria | Gap | Jelenlegi allapot | Deadline |
|-----------|-----|------------------|---------|
| Should fix | SF6 Cost attribution per-tenant | DB schema kibovites (alembic 037) | Phase 3 |
| Open Q | Customer compliance officer interview | Customer account manager felelossege | Phase 1 acceptance |
| Open Q | DPIA Profile A-ra | Legal felelossege | Phase 1 acceptance |
| Open Q | License check (AGPL, Gotenberg) | Legal felelossege | Phase 2a elott |
| Open Q | BGE-M3 benchmark valos HU adattal | AI engineer felelossege | Phase 2c elott |
| Open Q | vLLM vs alternative choice | Platform team felelossege | Phase 2b elott |

Ezek **NEM blokkoljak** a Phase 1a indulast, csak a Phase 2-t.

---

## 10. Vegleges osszefoglalo

A P0-P4 hardening lezarta az osszes **102_* Must fix** tetelt es a felhasznalo **2026-04-09
korrigalo tervet**. A terv-set **Phase 1a (v1.4.0) indulasra kesz** es Phase 2-ig (v1.5.0)
**full operational readiness**-t elerte.

**Kovetkezo lepes**: Sprint B (v1.3.0) befejezese utan Phase 1a kickoff session prompt
letrehozasa es a customer notification draft kuldese.

---

## 11. Hivatkozasok

- `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` — Must/Should/Nice fix forras
- `103_AIFLOW_v2_FINAL_VALIDATION.md` — Sign-off + P2/P4 kibovitesek
- `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md` — Rollback decision matrix (Section 12)
- `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` — Hardware + cost (P1)
- `100_f_AIFLOW_v2_HITL_WORKLOAD_MODEL.md` — Review workload (P1)
- `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` — N11b + N11c komponensek (P3)
- `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` — Master index (105_ bekotve)

---

> **Vegleges:** Ez a hardening record lezarja a `102_*` + felhasznaloi 2026-04-09 korrigalo
> terv minden tetelet. A terv-set Phase 1a indulasra kesz, full operational readiness-t
> ert el.
