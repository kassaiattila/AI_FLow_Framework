# AIFlow Sprint D — Session 44 Prompt (D0: Phase 1a Kickoff — Contracts + State Machines)

> **Datum:** 2026-04-15
> **Branch:** `feature/v1.4.0-ui-refinement` → merge to `main` → create `feature/v2.0.0-phase-1a-foundation`
> **HEAD:** `3e75ca2` (S43 + claude modernization)
> **Port:** API 8102 (dev), Frontend 5174 (dev)
> **Elozo session:** S43 — Sprint C COMPLETE + .claude/ modernization (DOHA-aligned)
> **Terv:** `01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md` (Week 1, Day 1-2)
> **Session tipus:** KICKOFF — v2 Phase 1a foundation sprint indulas
> **Workflow:** Merge → Branch → Scaffold → Contracts → State Machines → Tests

---

## KONTEXTUS

### Honnan jottunk
```
Sprint A (v1.2.2): Infra + security + guardrails + audit           ✅ DONE
Sprint B (v1.3.0): E2E service excellence, 17 session              ✅ DONE
Sprint C (v1.4.0): UI Journey-First Refinement, 7 session          ✅ DONE
  → .claude/ modernization: DOHA-aligned (6 skill, 4 agent, 25 cmd) ✅ DONE
```

### Hova tartunk — v2 Phase 1a (106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md)
```
Week 1: Contracts + State Machines (Day 1-5) ← EZ A SESSION: Day 1-2
Week 2: Policy + Provider Registry (Day 6-10)
Week 3: SkillInstance + Backward Compat (Day 11-15)
Week 4: Acceptance E2E + Docs + Demo (Day 16-20)
```

### Jelenlegi allapot
```
27 service | 175 endpoint | 48 DB tabla | 31 Alembic migration
1443 unit test | 169 E2E | 7 skill | 23 UI oldal
v1.4.0 kod kész, nincs merge main-re
```

---

## ELOFELTETELEK (ELLENORIZNI ELOSZOR!)

### 0a. Sprint C merge
```bash
# HA meg nincs mergelve:
git checkout main
git pull
git merge feature/v1.4.0-ui-refinement --no-ff -m "feat: Sprint C v1.4.0 — UI Journey-First Refinement"
git tag -a v1.4.0 -m "v1.4.0 — Sprint C UI Journey-First Refinement"
git push origin main --tags
```

### 0b. v2 Phase 1a branch letrehozas
```bash
git checkout main
git checkout -b feature/v2.0.0-phase-1a-foundation
```

### 0c. Baseline smoke
```bash
python -m pytest tests/unit/ -x -q          # 1443+ PASS
python -m ruff check src/ tests/             # 0 error
cd aiflow-admin && npx tsc --noEmit          # 0 error
PYTHONPATH=src alembic current               # 031 head
```

---

## S44 FELADATOK: Day 1-2 (106_ Section 4.1-4.3)

### LEPES 1: Intake modul scaffolding (Day 1, 4.1.1)

```
Cel: src/aiflow/intake/ modul letrehozasa.

Fajlok:
  src/aiflow/intake/__init__.py
  src/aiflow/intake/package.py        — IntakePackage + IntakeFile + IntakeDescription
  src/aiflow/intake/state_machine.py  — IntakePackageSM + IntakeFileSM
  src/aiflow/intake/exceptions.py     — IntakeError, InvalidTransitionError

Forras: 100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md Section 1-3
  → IntakeSourceType enum (6 ertek)
  → IntakePackageStatus enum (13 allapot)
  → DescriptionRole enum (5 ertek)
  → IntakeFile BaseModel (sha256, mime_type, size_bytes, metadata)
  → IntakeDescription BaseModel (role, content, source_ref)
  → IntakePackage BaseModel (files, descriptions, source_type, tenant_id, policy_snapshot)

FONTOS:
  - Copy-paste a 100_b_ dokumentumbol — NE modositsd a tipusokat!
  - __all__ exports MINDEN publikus nevvel
  - UUID4 default az ID mezokre
  - tenant_id KOTELEZO (multi-tenant boundary)
```

### LEPES 2: State machine implementacio (Day 1-2, 4.2)

```
Cel: IntakePackage es IntakeFile allapotgepek implementalasa.

Forras: 100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md Section 1-2

IntakePackageSM allapotok (13):
  RECEIVED → NORMALIZING → NORMALIZED → ROUTING → ROUTED →
  PARSING → PARSED → CLASSIFYING → CLASSIFIED → EXTRACTING →
  EXTRACTED → COMPLETED | FAILED | QUARANTINED

IntakeFileSM allapotok (7):
  PENDING → ROUTING → ROUTED → PROCESSING → PROCESSED → ARCHIVED | FAILED

Implementacio minta:
  - StateMachine class: transitions dict, validate_transition(), apply_transition()
  - Idempotens: ugyan az az atmenetet tobbszor alkalmazni safe (no-op ha mar az allapotban)
  - Audit hook: minden atmenetre LineageRecord generalas (kesobb)
  - Recovery: resume_from_checkpoint() — utolso ismert allapotbol ujrainditas

FONTOS:
  - Nincs definialt atmenet = TILTOTT (InvalidTransitionError)
  - Terminal allapotok: COMPLETED, FAILED, QUARANTINED — nem lehet tovabblepni
  - Minden transition-hoz timestamp + actor_id
```

### LEPES 3: Unit tesztek (Day 2, 4.3)

```
Cel: Teljes unit teszt lefedettség az uj modulra.

Fajlok:
  tests/unit/test_intake_package.py     — IntakePackage validation tesztek
  tests/unit/test_intake_state_machine.py — State machine transition tesztek

Minimum tesztek:
  Package:
    - valid package letrehozas (min 1 file VAGY 1 description)
    - invalid: ures files + ures descriptions → ValidationError
    - tenant_id kotelezo
    - sha256 format validation
    - source_type enum validation

  State Machine:
    - RECEIVED → NORMALIZING: valid
    - RECEIVED → COMPLETED: INVALID (nincs definialva)
    - COMPLETED → barmit: INVALID (terminal)
    - Idempotens replay: NORMALIZING → NORMALIZING = no-op
    - Teljes happy path: RECEIVED → ... → COMPLETED
    - Recovery: resume from PARSING → continues

Elvaras: min 20 teszt, 90%+ coverage az intake/ modulon
```

### LEPES 4: Lint + Regresszio + Commit

```
# Lint
python -m ruff check src/aiflow/intake/ tests/unit/test_intake_*
cd aiflow-admin && npx tsc --noEmit

# Regresszio
python -m pytest tests/unit/ -x -q   # 1443 + ~20 uj = ~1463 PASS

# Commit
git add src/aiflow/intake/ tests/unit/test_intake_*
git commit -m "feat(intake): D0 — IntakePackage domain contracts + state machines

Phase 1a Week 1 Day 1-2:
- IntakePackage, IntakeFile, IntakeDescription Pydantic models
- IntakePackageSM, IntakeFileSM state machines (13+7 states)
- IntakeError, InvalidTransitionError exceptions
- 20+ unit tests (package validation + state transitions)

Source: 100_b Section 1-3, 100_c Section 1-2

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## KOD REFERENCIAK

```
# OLVASA! — Ezeket a dokumentumokat KELL elolvasni a session elott:

01_PLAN/106_AIFLOW_v2_PHASE_1a_IMPLEMENTATION_GUIDE.md   — Section 4 (Week 1)
01_PLAN/100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md              — Section 1-3 (contracts)
01_PLAN/100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md          — Section 1-2 (state machines)

# Meglevo architektura referenciak:
src/aiflow/core/errors.py          — AIFlowError base class
src/aiflow/core/types.py           — Kozos tipusok
src/aiflow/services/base.py        — BaseService minta
src/aiflow/engine/step.py          — @step decorator
```

---

## SESSION VEGEN

```
1. /smoke-test               — API health + lint + tsc + E2E collect
2. /session-close S44         — validacio + commit + NEXT.md generalas
```

---

*Sprint D elso session: S44 = D0 (Phase 1a kickoff — IntakePackage contracts + state machines)*
