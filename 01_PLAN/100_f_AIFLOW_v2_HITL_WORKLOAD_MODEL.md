# AIFlow v2 — HITL Workload Model (Human-in-the-Loop Capacity)

> **Verzio:** 1.0 (FINAL — SIGNED OFF)
> **Datum:** 2026-04-09
> **Statusz:** ELFOGADVA (SIGNED OFF) — P1 hardening (`102_*` Section 3.9, SF3)
> **Master index:** `104_AIFLOW_v2_FINAL_MASTER_INDEX.md`
> **Rokon:** `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` (P1 parja)
> **Forras:** `102_AIFLOW_v2_FIRST_REVIEW_CYCLE.md` Section 3.9 (Should fix SF3)

> **Cel:** A multi-source intake utan a HITL terheles **varhatoan nagysagrendileg novekszik**.
> Ez a dokumentum formalizalja a review queue volumetriat, prioritast, SLA-t, assignment
> algoritmust, escalation szabalyokat es a bulk review UI minimumkovetelmenyeit.

---

## 0. Kontextus

A jelenlegi (v1.3.0) AIFlow HITL rendszer:
- `HumanReviewService` + `human_reviews` tabla (migration 022)
- Prioritas: low/medium/high/critical
- Manual pending → approve/reject workflow
- Nincs bulk review UI
- Nincs formalis SLA
- Nincs automatikus assignment / escalation

A v2 refinement utan **varhato terhelessnovekedes**:

| Review forras | Jelenleg | v2 utan |
|--------------|---------|---------|
| Low-confidence extraction | ~5-10% | **~15-25%** (multi-field confidence) |
| Ambiguous boundary | 0 | **~5-10%** (Qwen2.5-VL flags) |
| Ambiguous provider (routing) | 0 | **~2-5%** (all-providers-fail) |
| Ambiguous file-description | 0 | **~5-15%** (multi-file packages) |
| Ambiguous package context | 0 | **~2-5%** (cross-doc conflict) |
| Validation failure (veraPDF) | 0 | **~1-3%** (PDF/A fail) |
| Quarantine (compliance) | 0 | **~0.5-2%** |
| Policy violation | 0 | **~0.5-1%** |
| **OSSZESEN** | **~10%** | **~30-60%** |

Ha a volumen napi 1000 dokumentum Profile A GPU deployment-ben, akkor:
- v1.3.0: ~100 review/day
- v2 utan: **~300-600 review/day**

Ez kotelezi a bulk review UI-t es a formalis workload modellt.

---

## 1. Review queue volumetria model

### 1.1 Kategoria-szintu becsles (per 1000 dokumentum)

| Review tipus | % range | Atlag | Becsult idotartam/db | Osszes idő (perc) |
|-------------|---------|-------|--------------------|-------------------|
| `LOW_CONFIDENCE_EXTRACTION` | 15-25% | 20% | 3-5 perc | 600-1000 |
| `AMBIGUOUS_BOUNDARY` | 5-10% | 7% | 2-3 perc | 140-210 |
| `AMBIGUOUS_PROVIDER` | 2-5% | 3% | 1-2 perc | 30-60 |
| `AMBIGUOUS_FILE_DESCRIPTION` | 5-15% | 10% | 4-8 perc | 400-800 |
| `AMBIGUOUS_PACKAGE_CONTEXT` | 2-5% | 3% | 5-10 perc | 150-300 |
| `VALIDATION_FAILURE` | 1-3% | 2% | 3-5 perc | 60-100 |
| `QUARANTINE` | 0.5-2% | 1% | 10-15 perc | 100-150 |
| `POLICY_VIOLATION` | 0.5-1% | 0.7% | 15-30 perc | 105-210 |
| **OSSZESEN** | **30-66%** | **47%** | — | **1585-2830 perc** |

**Konkluzio per 1000 dokumentum:**
- ~470 review task
- ~30-47 reviewer-ora (osszesen)
- Ha egy reviewer napi 4 hatekony orat dolgozik → **7-12 reviewer** szukseges napi 1000 dok-ra

### 1.2 Customer sizing guide

| Napi dok volumen | Becsult review/day | Reviewer FTE |
|-----------------|-------------------|-------------|
| 100 | 47 | **0.3 FTE** (1 rész-munkaidős) |
| 500 | 235 | **1.2 FTE** (1 teljes + 0.2 backup) |
| 1000 | 470 | **2.5 FTE** |
| 2500 | 1175 | **6 FTE** |
| 5000 | 2350 | **12 FTE + senior reviewer lead** |

**Becsules elfeltetlesek**:
- 1 reviewer = 4 hatekony ora naponta (meeting, coffee, context switch levonasa utan)
- Average review task = 3.5 perc
- 4h × 60 min / 3.5 min = ~68 review/day/reviewer
- Overflow / SLA buffer: +20%

---

## 2. Prioritas rendszer

### 2.1 Review priority enum (lasd `100_b_*` Section 9)

```
CRITICAL  — compliance violation, quarantine, legal risk
HIGH      — SLA breach kozeli (< 2h deadline), nagy kotelezettsegu customer
MEDIUM    — normal business review (default)
LOW       — opcionalis review, training data collection
```

### 2.2 Automatikus prioritas felsorolas

| Review tipus | Default prioritas | Escalation triggers |
|-------------|-------------------|---------------------|
| `POLICY_VIOLATION` | CRITICAL | Compliance officer azonnal |
| `QUARANTINE` | CRITICAL | Compliance officer 1h-n belul |
| `VALIDATION_FAILURE` | HIGH | Archivista 4h-n belul |
| `AMBIGUOUS_PROVIDER` | HIGH | Reviewer 2h-n belul |
| `AMBIGUOUS_PACKAGE_CONTEXT` | HIGH | Lead reviewer 4h-n belul |
| `LOW_CONFIDENCE_EXTRACTION` | MEDIUM | Reviewer 8h-n belul |
| `AMBIGUOUS_BOUNDARY` | MEDIUM | Reviewer 8h-n belul |
| `AMBIGUOUS_FILE_DESCRIPTION` | MEDIUM | Reviewer 8h-n belul |

### 2.3 Uzleti prioritas felul-irás (customer policy)

A `instances/{customer}/hitl_policy.yaml`-ben:

```yaml
hitl_priority_override:
  # Mely dokumentumtipusok kerulnek automatikus HIGH-ba
  high_priority_doc_types:
    - invoice      # szamla pontossagi igeny
    - contract     # jogi kockazat
  
  # Melyik connector kerul automatikus HIGH-ba
  high_priority_sources:
    - vip_customer_inbox
  
  # Low priority (ignore-able)
  low_priority_doc_types:
    - marketing_material
```

---

## 3. SLA definiciok

### 3.1 Per-prioritas SLA

| Prioritas | Time-to-assign | Time-to-resolve | Escalation delay |
|-----------|---------------|-----------------|-----------------|
| CRITICAL | **5 perc** | **1 ora** | 30 perc |
| HIGH | **15 perc** | **4 ora** | 2 ora |
| MEDIUM | **1 ora** | **24 ora** | 12 ora |
| LOW | **4 ora** | **72 ora** | 48 ora |

**Szazalekos SLA celok**:
- CRITICAL: 99% SLA-ban resolved
- HIGH: 95% SLA-ban resolved
- MEDIUM: 90% SLA-ban resolved
- LOW: 80% SLA-ban resolved

### 3.2 Per-tenant SLA override

A `instances/{customer}/hitl_policy.yaml`:

```yaml
hitl_sla_override:
  # Enterprise customer szigorubb SLA
  critical:
    time_to_resolve_hours: 0.5  # 30 perc
  high:
    time_to_resolve_hours: 2    # 2 ora
  
  # Business hours only
  business_hours:
    start: "08:00"
    end: "17:00"
    timezone: "Europe/Budapest"
    sla_paused_outside_hours: true  # SLA not counting 17-08
```

### 3.3 SLA monitoring

Prometheus metricok (lasd `100_e_*` Section 6):

```
aiflow_hitl_tasks_pending{priority,tenant_id}
aiflow_hitl_tasks_assigned{priority,tenant_id}
aiflow_hitl_sla_breach_total{priority,tenant_id}
aiflow_hitl_resolution_duration_seconds_bucket{priority,tenant_id,le}
aiflow_hitl_escalations_total{priority,tenant_id}
```

Grafana dashboard `infra/grafana/dashboards/hitl_workload.json`:
- Queue depth per prioritas
- SLA breach rate (alert > 5%)
- Reviewer utilization
- Escalation chain visibility

---

## 4. Assignment algoritmus

### 4.1 Alapelv: skill-aware round-robin

A reviewer-eknek **skill tag-jei** vannak (pl. `invoice_specialist`, `legal_reviewer`, `compliance_officer`).

A `ReviewTask` auto-assignment:

```python
# src/aiflow/services/human_review/assignment.py
class ReviewAssignmentEngine:
    async def assign(self, task: ReviewTask) -> str | None:
        """Assign a review task to the best available reviewer."""
        
        # Step 1: skill matching
        required_skills = self._get_required_skills(task.review_type, task.tenant_id)
        eligible_reviewers = await self.reviewer_repo.list_by_skills(required_skills)
        
        if not eligible_reviewers:
            logger.warning("no_eligible_reviewer", task_id=task.task_id)
            return None
        
        # Step 2: availability check (business hours + current load)
        available = [
            r for r in eligible_reviewers
            if await self.is_available(r, task.tenant_id)
        ]
        
        if not available:
            # Fallback: assign to on-call reviewer
            return await self.get_oncall_reviewer(task.tenant_id)
        
        # Step 3: least loaded + round-robin tiebreaker
        return min(
            available,
            key=lambda r: (r.current_load, r.last_assigned_at or 0),
        )
```

### 4.2 Skill taxonomy (default)

| Skill tag | Ertekes review tipusokra | Reviewer profil |
|-----------|-------------------------|----------------|
| `invoice_specialist` | LOW_CONFIDENCE_EXTRACTION (invoice) | Konyvelo, penzugyes |
| `legal_reviewer` | AMBIGUOUS_PACKAGE_CONTEXT (contract), POLICY_VIOLATION | Jogi szakerto |
| `compliance_officer` | QUARANTINE, POLICY_VIOLATION | Compliance officer |
| `document_analyst` | AMBIGUOUS_FILE_DESCRIPTION, AMBIGUOUS_BOUNDARY | General document analyst |
| `archivist` | VALIDATION_FAILURE (PDF/A) | Archivista |

### 4.3 Reviewer profiles (per-tenant)

```yaml
# instances/{customer}/reviewers.yaml
reviewers:
  - user_id: "konyvelo1@bestix.hu"
    display_name: "Kovacs Anna"
    skills: [invoice_specialist, document_analyst]
    max_concurrent_tasks: 5
    business_hours:
      timezone: "Europe/Budapest"
      start: "09:00"
      end: "17:00"
      days: [mon, tue, wed, thu, fri]
    weekly_capacity_hours: 20  # part-time
  
  - user_id: "jog1@bestix.hu"
    display_name: "Nagy Peter"
    skills: [legal_reviewer, compliance_officer]
    max_concurrent_tasks: 3
    business_hours:
      timezone: "Europe/Budapest"
      start: "08:00"
      end: "16:00"
    weekly_capacity_hours: 40  # full-time
```

---

## 5. Escalation rules

### 5.1 Escalation chain

Minden `ReviewTask`-hez tartozik egy **escalation chain**:

```yaml
# Alap escalation (per priority)
CRITICAL:
  - assign_within: 5 min   → on-call reviewer
  - resolve_within: 30 min → senior lead
  - resolve_within: 1 hour → compliance officer
  - resolve_within: 2 hour → CTO / data protection officer

HIGH:
  - assign_within: 15 min  → skilled reviewer
  - resolve_within: 2 hour → senior reviewer
  - resolve_within: 4 hour → lead reviewer

MEDIUM:
  - assign_within: 1 hour  → reviewer
  - resolve_within: 12 hour → senior reviewer (if breach)
  - resolve_within: 24 hour → manual admin intervention
```

### 5.2 Auto-escalation background job

```python
# src/aiflow/services/human_review/escalation.py
@scheduled(cron="*/5 * * * *")  # every 5 min
async def check_escalations():
    """Background job to escalate breached tasks."""
    breached = await review_repo.find_sla_breached()
    
    for task in breached:
        if task.escalation_target:
            new_assignee = await escalation_chain.next_level(
                task.review_type,
                task.priority,
                current_level=task.escalation_level,
            )
            if new_assignee:
                await review_service.reassign(
                    task.task_id,
                    new_assignee,
                    reason="sla_breach",
                )
                await notification_service.notify(
                    recipient=new_assignee,
                    template="task_escalated",
                    context={"task": task},
                )
        else:
            # No more escalation → mark as EXPIRED + alert admin
            await review_service.mark_expired(task.task_id)
            await notification_service.notify_admin(
                template="task_expired",
                context={"task": task},
            )
```

---

## 6. Bulk review UI — minimum kovetelmenyek

### 6.1 Miert szukseges?

Jelenleg a `aiflow-admin` UI `human_review` oldalon **egy-egy** review task kerul feldolgozasra.
A v2 utan a volumen novekedessel **bulk mukveltek** kotelezoek.

### 6.2 Minimum funkciok

| # | Funkcio | Priority | Hely |
|---|---------|----------|------|
| 1 | **Queue view** — reviewer saját queue filterezhet (priority, review_type, tenant) | MUST | `/review/queue` |
| 2 | **Bulk select** — checkbox-ok, select all visible | MUST | `/review/queue` |
| 3 | **Bulk approve** — tobb task egyuttes approve (ha hasonlok) | MUST | `/review/queue` |
| 4 | **Bulk reject** — tobb task egyuttes reject with common reason | MUST | `/review/queue` |
| 5 | **Bulk assign** — admin atdelegalhat tobb task-ot | SHOULD | `/review/admin` |
| 6 | **Smart grouping** — hasonlo task-ok (pl. same doc_type, same anomaly) | SHOULD | `/review/queue` |
| 7 | **Keyboard shortcuts** — A/R/N (approve/reject/next) | SHOULD | `/review/task/{id}` |
| 8 | **Split-screen** — task details + context side-by-side | SHOULD | `/review/task/{id}` |
| 9 | **Saved filter views** — reviewer sajat filter preset | NICE | `/review/queue` |
| 10 | **Batch annotation** — tobb task egyuttes annotation (ML training data) | NICE | `/review/queue` |

### 6.3 UI wireframe (ASCII sketch)

```
╔═══════════════════════════════════════════════════════════════════╗
║  Review Queue                                  [Filter ▼] [⚙️]    ║
╠═══════════════════════════════════════════════════════════════════╣
║  ☐ Select all  |  245 tasks  |  Selected: 0  |  Bulk: [Approve▼]  ║
╠═══════════════════════════════════════════════════════════════════╣
║  ☐ 🔴 CRITICAL  POLICY_VIOLATION  pkg-abc123      SLA: 12 min left ║
║     "Contract contains disallowed PII (email)"                     ║
║  ─────────────────────────────────────────────────────────────────║
║  ☐ 🟡 HIGH  LOW_CONFIDENCE_EXTRACTION  pkg-def456  SLA: 2h left    ║
║     "Invoice field 'vendor_name' confidence 0.62"                   ║
║  ─────────────────────────────────────────────────────────────────║
║  ☐ 🟢 MEDIUM  AMBIGUOUS_BOUNDARY  pkg-ghi789  SLA: 18h left        ║
║     "Multi-document PDF, 3 possible boundaries"                    ║
╠═══════════════════════════════════════════════════════════════════╣
║  Navigation: [◀ Prev] [Next ▶]    [Jump to: ___]                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

Task detail view:

```
╔═══════════════════════════════════════════════════════════════════╗
║  Review Task #abc123                    [← Back]  [Approve] [Reject]
╠═══════════════════════════════════════════════════════════════════╣
║ LEFT (document view)        ║ RIGHT (task context)                 ║
║ ┌───────────────────────┐  ║ Type: LOW_CONFIDENCE_EXTRACTION       ║
║ │  [PDF preview]         │ ║ Priority: HIGH                        ║
║ │  Page 1 of 3           │  ║ Package: pkg-def456                   ║
║ │  ...                    │ ║ File: invoice_001.pdf                 ║
║ └───────────────────────┘  ║                                       ║
║                             ║ Fields flagged:                       ║
║ [< Prev page] [Next page >] ║  • vendor_name (0.62) [edit]          ║
║                             ║  • total_amount (0.88) ✓              ║
║ Extracted fields:           ║  • invoice_date (0.95) ✓              ║
║  vendor_name: "Acme Kft"    ║                                       ║
║  total_amount: 123,456 HUF  ║ Suggested actions:                    ║
║  invoice_date: 2026-04-05   ║  [Accept as-is] [Edit] [Re-extract]   ║
║                             ║                                       ║
║ Reasoning:                  ║ Hotkey: A=approve R=reject N=next     ║
║  "gpt-4o-mini extraction..."║                                       ║
╚═══════════════════════════════════════════════════════════════════╝
```

### 6.4 Phase ordering

| Phase | Sprint | Funkcio |
|-------|--------|---------|
| Phase 1c | v1.4.2 | B7 verification page v2 (EGY task view with bounding box + per-field confidence) |
| Phase 3 | v1.6.0 | Queue view + bulk select + bulk approve/reject (MUST items 1-4) |
| Phase 3+ | v1.6.1 | Smart grouping + keyboard shortcuts (SHOULD items 5-8) |
| Phase 4 | v2.0.0+ | Saved filters + batch annotation (NICE items 9-10) |

---

## 7. Reviewer fatigue / cognitive load

### 7.1 Alapelvek

- **Max concurrent tasks**: 5 (reviewer-enkent, overrideable)
- **Break reminder**: 45 percenkent 5 perc szunet (pop-up)
- **Complex task limit**: `POLICY_VIOLATION` + `QUARANTINE` max 3/day/reviewer (mental load)
- **Rotation**: critical task nem kerul ugyanazt a reviewer-hez 2 oran belul

### 7.2 Reviewer health metrics

```
aiflow_hitl_reviewer_daily_tasks{user_id}
aiflow_hitl_reviewer_avg_resolution_seconds{user_id}
aiflow_hitl_reviewer_accuracy_rate{user_id}  # downstream feedback
aiflow_hitl_reviewer_fatigue_score{user_id}  # tasks/h + avg complexity
```

Ha a `fatigue_score > threshold` → auto-rotation.

---

## 8. Training data collection

A review actions (approve/reject/edit) **automatikusan** gyujtik a training datat:

```python
# src/aiflow/services/human_review/training_data.py
class ReviewTrainingDataCollector:
    async def on_review_resolved(self, task: ReviewTask, action: str):
        """Capture review as training signal."""
        if action == "approve":
            # Positive sample
            await self.positive_samples.append(task)
        elif action == "reject":
            # Negative sample with reason
            await self.negative_samples.append(task)
        elif action == "edit":
            # Correction signal for fine-tuning
            await self.correction_samples.append(task)
```

A Phase 3 `services/quality/` ezt hasznalja a confidence calibration re-training-jehez.

---

## 9. Customer onboarding — HITL setup

Per-customer deployment:

1. **Reviewer profile definialasa**: `instances/{customer}/reviewers.yaml`
2. **SLA override**: `instances/{customer}/hitl_policy.yaml`
3. **Notification channel**: Slack channel vagy email
4. **Dashboard access**: reviewer-eknek aiflow-admin account
5. **Training session**: 2 ora onboarding (task types + UI)
6. **Shadow week**: 1 het felugyelt review (senior + junior)

---

## 10. Risk items

| # | Kockazat | Hatas | Mitigation |
|---|---------|-------|------------|
| H1 | HITL overflow (reviewer FTE elegtelen) | SLA breach, customer dissatisfaction | Dashboard alert at 80% capacity, auto-HIRE suggest |
| H2 | Reviewer cognitive fatigue | Accuracy drop | `fatigue_score` monitoring + auto-rotation |
| H3 | Low-confidence threshold tul agresszivebb | Noise review queue | Phase 2c confidence kalibracios re-tuning |
| H4 | Escalation chain rossz (nem ertesul) | Expired task, compliance risk | SLA monitoring + Grafana alert |
| H5 | Bulk approve hiba (veletlen) | Data quality issue | Undo window (5 min soft delete), confirm dialog |

---

## 11. Sign-off checklist

- [ ] Workload modell szakmai review (architect + product + customer success)
- [ ] SLA matrix elfogadva
- [ ] Reviewer skill taxonomy elfogadva
- [ ] Bulk review UI wireframe UX review
- [ ] Customer onboarding template kesz
- [ ] HITL Grafana dashboard scaffolding
- [ ] Training data collection policy elfogadva

---

## 12. Open items

| # | Tema | Kerdes | Default |
|---|------|--------|--------|
| H-Q1 | GDPR + training data | Allowed to use review data for retraining? | Explicit opt-in per tenant |
| H-Q2 | Multi-language review | Hungarian reviewer for HU docs, English for EN? | Skill tag-gel megoldva |
| H-Q3 | External reviewer (contractor) | Security model? | Limited instance scope + audit log |
| H-Q4 | Reviewer AI copilot (CrewAI) | Phase 3 N22 integrate? | Yes — `operator_copilot_flow` |

---

## 13. Hivatkozasok

- `100_b_AIFLOW_v2_DOMAIN_CONTRACTS.md` Section 9 — `ReviewTask` Pydantic modell
- `100_c_AIFLOW_v2_STATE_LIFECYCLE_MODEL.md` Section 6 — `ReviewTask` state machine
- `100_e_AIFLOW_v2_CAPACITY_PLANNING.md` Section 6 — Prometheus metricok
- `101_AIFLOW_v2_COMPONENT_TRANSFORMATION_PLAN.md` R11 — Confidence Calibration Layer
- `52_HUMAN_IN_THE_LOOP_NOTIFICATION.md` — meglevo HITL alap

---

> **Vegleges:** Ez a dokumentum lezarja a HITL workload tervezes gap-et (P1 SF3). A Phase 2
> indulas (v1.5.0) elott ez a dokumentum **sign-off-olt kell legyen** az architect + product
> + customer success altal. A `100_e_*` Capacity Planning parja, egyutt adjak a full
> operational readiness-t.
