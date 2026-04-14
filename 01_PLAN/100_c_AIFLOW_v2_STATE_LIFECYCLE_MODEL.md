# AIFlow v2 — State Lifecycle Model (Allapotgep Specifikacio)

> **Verzio:** 2.0 (FINAL — SIGNED OFF)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — `103_*` 2. ciklus + `105_*` P0-P4 hardening utan
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md` (kezdd itt az olvasast!)
> **Szulo:** `100_AIFLOW_v2_ARCHITECTURE_REFINEMENT_OVERVIEW.md`
> **Rokon:** `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md`, `100_d_AIFLOW_v2_MIGRATION_PLAYBOOK.md`
> **Forras:** `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` Section 3.2 (Must fix)
>
> **Valtozas naplo:**
> - **v2.0 (2026-04-09):** Status "AKTIV" → "ELFOGADVA (SIGNED OFF)". Sign-off `103_*` utan,
>   P0 hardening korrekcio (`105_*`-ben rogzitve).
> - **v1.0 (2026-04-08):** Initial draft, 7 entitas state machine.

> **Cel:** Minden kulcs domain entitas formal allapotgepe — allapot enum, atmenetek,
> recovery utak, audit hookok. Idempotens replay garantalasa. Phase 1 implementacio
> NEM start-elheto state machine specifikacio nelkul.

---

## 0. Tartalomjegyzek

| # | Entitas | Allapot szam | Recovery |
|---|---------|-------------|---------|
| 1 | `IntakePackage` | 11 | Resume mechanizmus |
| 2 | `IntakeFile` (per-file) | 7 | Re-route |
| 3 | `RoutingDecision` | 6 | Fallback chain |
| 4 | `ExtractionResult` | 5 | Re-extract |
| 5 | `ArchivalArtifact` | 8 | Re-convert / quarantine |
| 6 | `ReviewTask` | 6 | Escalation |
| 7 | `EmbeddingDecision` | 4 | Re-embed |

---

## 1. `IntakePackage` State Machine

### 1.1 Allapot enum

```
RECEIVED         — package megerkezett, NEM normalizalt
NORMALIZED       — IntakePackage felepitve, files + descriptions normalizalt
ROUTED           — minden file-ra megvan a RoutingDecision
PARSING          — parser fut (legalabb 1 file)
PARSED           — minden file-ra megvan a ParserResult
CLASSIFYING      — classifier fut
CLASSIFIED       — minden file osztalyozva
EXTRACTING       — extractor fut (per-file vagy package-szintu)
EXTRACTED        — minden ExtractionResult kesz
REVIEW_PENDING   — legalabb 1 ReviewTask aktiv
REVIEWED         — minden ReviewTask resolved/escalated
ARCHIVING        — Gotenberg + veraPDF folyamatban
ARCHIVED         — minden ArchivalArtifact valid PDF/A
COMPLETED        — package teljes feldolgozas, vegallapot
FAILED           — nem-resumeable hiba
QUARANTINED      — compliance / validation FAIL → karanten
```

### 1.2 Allapot atmenetek

```
                 ┌──────────┐
                 │ RECEIVED │
                 └────┬─────┘
                      │ normalize()
                      ▼
                 ┌──────────────┐
                 │  NORMALIZED  │
                 └────┬─────────┘
                      │ route()
                      ▼
                 ┌──────────────┐
                 │   ROUTED     │
                 └────┬─────────┘
                      │ parse()
                      ▼
                 ┌──────────────┐
                 │   PARSING    │ ──┐
                 └────┬─────────┘   │ on_error → FAILED (resumeable)
                      │ parse_done()
                      ▼
                 ┌──────────────┐
                 │   PARSED     │
                 └────┬─────────┘
                      │ classify()
                      ▼
                 ┌──────────────┐
                 │ CLASSIFYING  │
                 └────┬─────────┘
                      │ classify_done()
                      ▼
                 ┌──────────────┐
                 │ CLASSIFIED   │
                 └────┬─────────┘
                      │ extract()
                      ▼
                 ┌──────────────┐
                 │ EXTRACTING   │ ──┐
                 └────┬─────────┘   │ low_confidence → REVIEW_PENDING
                      │ extract_done()
                      ▼
                 ┌──────────────┐
                 │  EXTRACTED   │ ───┐
                 └────┬─────────┘    │ requires_review → REVIEW_PENDING
                      │ archive()
                      ▼
                 ┌──────────────┐
                 │  ARCHIVING   │ ──┐
                 └────┬─────────┘   │ verapdf_fail → QUARANTINED
                      │ archive_done()
                      ▼
                 ┌──────────────┐
                 │   ARCHIVED   │
                 └────┬─────────┘
                      │ finalize()
                      ▼
                 ┌──────────────┐
                 │  COMPLETED   │  (vegallapot)
                 └──────────────┘

         Mellekagak:
                   │  REVIEW_PENDING ──→ REVIEWED ──→ (vissza az eredeti agba)
                   │  FAILED       ──→ resume() ──→ (utolsó sikeres allapot)
                   │  QUARANTINED  ──→ vegallapot (manual unblock)
```

### 1.3 Atmeneti szabalyok

| From | To | Trigger | Allowed by | Idempotent? |
|------|-----|---------|------------|------------|
| `RECEIVED` | `NORMALIZED` | `IntakeNormalizationLayer.normalize()` | system | Yes |
| `NORMALIZED` | `ROUTED` | `MultiSignalRoutingEngine.route()` | system | Yes (per-file) |
| `ROUTED` | `PARSING` | parser worker pickup | system | Yes |
| `PARSING` | `PARSED` | all files parsed | system | Yes |
| `PARSING` | `FAILED` | non-recoverable parser error | system | NA |
| `PARSED` | `CLASSIFYING` | classifier worker pickup | system | Yes |
| `CLASSIFYING` | `CLASSIFIED` | all files classified | system | Yes |
| `CLASSIFIED` | `EXTRACTING` | extractor worker pickup | system | Yes |
| `EXTRACTING` | `EXTRACTED` | all extractions done, all >threshold | system | Yes |
| `EXTRACTING` | `REVIEW_PENDING` | low_confidence detected | system | Yes |
| `EXTRACTED` | `REVIEW_PENDING` | flagged after extract | system | Yes |
| `REVIEW_PENDING` | `REVIEWED` | all ReviewTasks resolved | reviewer | NA |
| `REVIEW_PENDING` | `FAILED` | SLA expired + no escalation | system | NA |
| `REVIEWED` | `EXTRACTING` | reviewer requested re-extract | reviewer | Yes |
| `REVIEWED` | `ARCHIVING` | proceed | reviewer or auto | Yes |
| `EXTRACTED` | `ARCHIVING` | auto-approved | system | Yes |
| `ARCHIVING` | `ARCHIVED` | all artifacts validated | system | Yes |
| `ARCHIVING` | `QUARANTINED` | veraPDF FAIL | system | NA |
| `ARCHIVED` | `COMPLETED` | finalize | system | Yes |
| `FAILED` | `RECEIVED..ARCHIVING` | resume() | admin | Yes |
| `QUARANTINED` | `RECEIVED..ARCHIVING` | manual unblock + reroute | admin | Yes |

### 1.4 Recovery rules

| Statusz | Recovery akcio |
|---------|---------------|
| `PARSING` (akadt el) | `WorkflowRunner.resume(package_id)` — re-route minden file-t, ahol nincs ParserResult |
| `EXTRACTING` (akadt el) | `WorkflowRunner.resume()` — re-extract minden file-t, ahol nincs ExtractionResult |
| `REVIEW_PENDING` (SLA expired) | Auto-escalation `escalation_target`-ra |
| `ARCHIVING` (akadt el) | Re-convert (Gotenberg) + re-validate (veraPDF) |
| `FAILED` (root cause known) | Manual fix + `resume()` |
| `QUARANTINED` | Manual review az auditor altal |

### 1.5 Audit hooks

Minden allapot atmenet automatikusan emit egy `LineageRecord`-ot:

```python
LineageRecord(
    event_type=LineageEventType.from_status_transition(from_state, to_state),
    package_id=package.package_id,
    component="package_state_machine",
    metadata={
        "from_status": from_state,
        "to_status": to_state,
        "trigger": trigger,
        "user_id": user_id_or_system,
    },
)
```

---

## 2. `IntakeFile` State Machine (per-file)

### 2.1 Allapot enum

```
PENDING       — file felvett, NEM routelt
ROUTED        — RoutingDecision kesz
PARSED        — ParserResult kesz
CLASSIFIED    — ClassificationResult kesz
EXTRACTED     — ExtractionResult kesz
ARCHIVED      — ArchivalArtifact + ValidationResult kesz
FAILED        — file-szintu vegleges hiba (skip)
```

### 2.2 Atmenetek

```
PENDING → ROUTED → PARSED → CLASSIFIED → EXTRACTED → ARCHIVED
                                   │                  │
                                   ▼                  ▼
                              FAILED             QUARANTINED (mint melleagrol)
```

A file-szintu allapot **fuggetlen** a package allapotat, de a package allapota
**aggregalja** a file-szinteket: `package.status = max_lifecycle_step(file.status for file in package.files)`.

### 2.3 Recovery rule

Egy file FAILED-elhet (pl. corrupted PDF), de a package mehet tovabb a tobbi file-javal. A package
csak akkor lesz `COMPLETED`, ha legalabb 1 file `ARCHIVED` allapotban van. Minden file egyenkent
re-tryelheto.

---

## 3. `RoutingDecision` State Machine

### 3.1 Allapot enum

```
PENDING            — szignal extrakcio folyamatban
ACCEPTED           — score-ok kalkulalva, selected_provider kivalasztva
EXECUTED           — selected_provider sikeresen lefutott
FALLBACK_USED      — selected fail, fallback chain valamelyik used
ALL_FAILED         — minden provider FAIL
HUMAN_OVERRIDE     — admin manualis kivalasztas
```

### 3.2 Atmenetek

```
PENDING → ACCEPTED → EXECUTED       (happy path)
                  ↓
                  → FALLBACK_USED   (selected fail → next in chain)
                  ↓
                  → ALL_FAILED      (entire chain exhausted)

PENDING → HUMAN_OVERRIDE → EXECUTED  (admin override)
```

### 3.3 Recovery

- `ALL_FAILED` → kotelezo `ReviewTask` letrehozas (`ambiguous_provider`), package `REVIEW_PENDING`
- `EXECUTED` → final, no recovery
- `FALLBACK_USED` → audit log warning, manual review opt

---

## 4. `ExtractionResult` State Machine

### 4.1 Allapot enum

```
PENDING        — extractor meg nem futott
EXTRACTING     — folyamatban
EXTRACTED      — kesz, confidence calibration utan
APPROVED       — auto-approved (>= threshold)
REJECTED       — auto-rejected (<reject_threshold)
REVIEW_PENDING — review queue-ban
REVIEWED       — reviewer dontes (approve / reject / re-extract)
```

### 4.2 Atmenetek

```
PENDING → EXTRACTING → EXTRACTED ──→ APPROVED       (confidence >= 0.90)
                              │
                              ├──→ REVIEW_PENDING   (0.70 <= confidence < 0.90)
                              │       │
                              │       └──→ REVIEWED → APPROVED | REJECTED | re-extract (PENDING)
                              │
                              └──→ REJECTED         (confidence < 0.70)
```

### 4.3 Recovery

- `EXTRACTING` (akadt el) → re-extract (vissza `PENDING`)
- `REVIEW_PENDING` SLA expired → escalation
- `REJECTED` → final, manual override szukseges hogy reset

### 4.4 Per-field state

Minden `FieldConfidence` is rendelkezik state-tel:

```
EXTRACTED → APPROVED | NEEDS_REVIEW | REJECTED
```

A package-szintu `ExtractionResult.routing_decision` az ossz field statuszok aggregaltja.

---

## 5. `ArchivalArtifact` State Machine

### 5.1 Allapot enum (lasd 100_b 6. fejezet)

```
PENDING        — meg nem konvertalt
CONVERTING     — Gotenberg konvertalas
CONVERTED      — PDF/A elkeszult, NEM validalva
VALIDATING     — veraPDF futtatas
VALID          — veraPDF PASS
INVALID        — veraPDF FAIL
QUARANTINED    — INVALID + audit-required
FAILED         — Gotenberg vagy veraPDF crash (NEM dontes alapu)
```

### 5.2 Atmenetek

```
PENDING → CONVERTING ──→ CONVERTED ──→ VALIDATING ──→ VALID
                  │                            │
                  │                            └──→ INVALID ──→ QUARANTINED
                  │
                  └──→ FAILED  (Gotenberg crash)
```

### 5.3 Recovery rules

- `FAILED` (Gotenberg crash) → re-convert ujraprobalas, max 3
- `INVALID` → automatikus `QUARANTINED` + `ReviewTask(quarantine_reason)`
- `QUARANTINED` → admin manual unblock vagy compliance dontes

### 5.4 Compliance constraint

**KRITIKUS:** Az `is_validated=True` mezo CSAK a `VALID` allapotbol erheto el. Egy `CONVERTED`
ArchivalArtifact NEM tekintheto archivaltak ig veraPDF nem futott. Ezt egy DB constraint
biztositja:

```sql
ALTER TABLE archival_artifacts
ADD CONSTRAINT validated_only_when_valid
CHECK (
    (is_validated = TRUE AND status = 'valid')
    OR (is_validated = FALSE AND status != 'valid')
);
```

---

## 6. `ReviewTask` State Machine

### 6.1 Allapot enum (lasd 100_b 9. fejezet)

```
PENDING       — letrehozott, NEM kiosztott
ASSIGNED      — reviewerre kiosztott
IN_PROGRESS   — reviewer dolgozik rajta
RESOLVED      — reviewer dontest hozott
ESCALATED     — SLA expired + escalation_target-re kioszott
EXPIRED       — SLA expired + nincs escalation
```

### 6.2 Atmenetek

```
PENDING → ASSIGNED → IN_PROGRESS → RESOLVED
   │         │              │           │
   │         │              │           └──→ (package allapot vissza folytatja)
   │         │              │
   │         │              └──→ EXPIRED  (timeout)
   │         │
   │         └──→ EXPIRED  (no engagement)
   │
   └──→ ESCALATED  (sla_deadline lejart, has escalation_target)
        ESCALATED → ASSIGNED  (uj reviewer)
```

### 6.3 SLA + escalation logika

Minden `ReviewTask` `sla_deadline` mezovel jon. Egy background scheduler 1 percenkent ellenorzi:

```python
async def check_sla_expirations():
    expired_tasks = await db.fetch_all(
        "SELECT * FROM review_tasks WHERE sla_deadline < NOW() AND status NOT IN ('resolved', 'expired', 'escalated')"
    )
    for task in expired_tasks:
        if task.escalation_target:
            await reassign_task(task.task_id, task.escalation_target)
            await update_status(task.task_id, ReviewStatus.ESCALATED)
        else:
            await update_status(task.task_id, ReviewStatus.EXPIRED)
            # package stays in REVIEW_PENDING — admin must intervene
```

### 6.4 Recovery

- `EXPIRED` → manual admin akcio (re-assign vagy resolve)
- `ESCALATED` → reset ASSIGNED
- `RESOLVED` → final

---

## 7. `EmbeddingDecision` State Machine

### 7.1 Allapot enum

```
PENDING        — chunk varakozik
REDACTED       — PII gate lefutott
EMBEDDED       — vector store-ban
BLOCKED        — policy block (PII embedding NOT allowed)
```

### 7.2 Atmenetek

```
PENDING → REDACTED ──→ EMBEDDED       (happy path)
              │
              └──→ BLOCKED            (policy block)
```

### 7.3 Recovery

- `BLOCKED` → tartos final, kotelezo audit log
- `EMBEDDED` → final

---

## 8. Lifecycle Audit View

A teljes package allapot 1 query-vel megnezheto:

```sql
SELECT
    p.package_id,
    p.status as package_status,
    array_agg(DISTINCT f.status) as file_statuses,
    array_agg(DISTINCT r.status) as routing_statuses,
    array_agg(DISTINCT e.routing_decision) as extraction_decisions,
    array_agg(DISTINCT a.status) as archival_statuses,
    array_agg(DISTINCT t.status) as review_statuses,
    p.created_at,
    p.updated_at
FROM intake_packages p
LEFT JOIN intake_files f ON f.package_id = p.package_id
LEFT JOIN routing_decisions r ON r.package_id = p.package_id
LEFT JOIN extraction_results e ON e.package_id = p.package_id
LEFT JOIN archival_artifacts a ON a.package_id = p.package_id
LEFT JOIN review_tasks t ON t.package_id = p.package_id
WHERE p.package_id = $1
GROUP BY p.package_id;
```

A `aiflow-admin` UI Audit oldalan ez egy timeline-szeruen vizualizaltat.

---

## 9. State Transition Auditability

### 9.1 Kotelezo audit per atmenet

Minden allapot atmenet **automatikusan** kifejti a kovetkezoket:

1. **DB update** (atomic)
2. **LineageRecord emit** (Phase 3 N17)
3. **Langfuse trace span** (mar van)
4. **Notification trigger** (ha relevant: pl. REVIEW_PENDING → notification a reviewerhez)
5. **Metric counter** (Prometheus, Phase 3 N20)

### 9.2 Idempotens replay garancia

Minden allapot atmenet **idempotens**: ha ugyanazt az inputtal kepest valamelyik step
mar elerte, akkor NEM ismetli, hanem visszater az eredmennyel.

```python
async def transition(package_id: UUID, to_status: IntakePackageStatus, ...) -> bool:
    package = await get_package(package_id)
    if package.status == to_status:
        logger.info("idempotent_skip", from_status=package.status, to_status=to_status)
        return False
    if not is_valid_transition(package.status, to_status):
        raise InvalidStateTransitionError(...)
    await db.update(package_id, status=to_status, updated_at=now())
    await emit_lineage(...)
    return True
```

### 9.3 Resume mechanizmus

A `WorkflowRunner.resume(package_id)` az utolso ismert `step_runs` allapotbol indul:

```python
async def resume(package_id: UUID) -> WorkflowRun:
    package = await get_package(package_id)
    if package.status not in {RECEIVED, NORMALIZED, ROUTED, PARSED, CLASSIFIED, EXTRACTED}:
        raise ValueError(f"Cannot resume from {package.status}")
    last_step = await get_last_step_run(package_id)
    next_step = determine_next_step(last_step.step_name)
    return await runner.run_from_step(workflow, next_step, package=package)
```

---

## 10. Sign-off Checklist (Phase 1 indulas elott)

- [ ] Minden 7 allapotgep code review
- [ ] Allapot atmenet diagram elfogadva (Mermaid vagy ASCII)
- [ ] DB constraint-ek megirva (alembic 030+)
- [ ] State transition validator (`is_valid_transition()`) implementalva
- [ ] Idempotens replay test PASS
- [ ] Resume mechanizmus test PASS minden recovery utra
- [ ] SLA expiration scheduler test PASS

---

## 11. Mit NEM tartalmaz ez a dokumentum

- Pydantic schema definition (lasd `100_b_*.md`)
- Migration script (lasd `100_d_*.md`)
- API endpoint mapping (`22_API_SPECIFICATION.md` kibovites)
- UI workflow timeline (Phase 3 audit page kibovites)

---

> **Megjegyzes:** A jelenlegi `WorkflowRunner` mar tartalmaz allapot kezelot (`workflow_runs.status`),
> de az **NEM ugyanaz** mint az `IntakePackage.status`. A package allapota a **business domain** szintje,
> a workflow_run a **vegrehajtasi eszkoz** szintje. A ket fogalmat NEM keverni.
