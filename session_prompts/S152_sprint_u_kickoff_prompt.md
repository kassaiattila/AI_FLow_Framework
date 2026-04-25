# AIFlow [Sprint U] — Session 152 Prompt (Sprint U kickoff — scope triage + plan doc)

> **Datum:** 2026-04-25 (snapshot date — adjust if session runs later)
> **Branch:** `feature/u-s152-sprint-u-kickoff` (cut from `main` after the Sprint T close PR squash-merges → new tip).
> **HEAD (expected):** Sprint T close PR squash on top of `ee2b431` (S150 squash).
> **Port:** API 8102 | UI 5173
> **Elozo session:** S151 — Sprint T close. `docs/sprint_t_retro.md` + `docs/sprint_t_pr_description.md` + CLAUDE.md banner flip (Sprint T MERGED 2026-04-25, tag `v1.5.3` queued) + ST-FU-1 fix (`tests/unit/api/test_rag_collections_router.py` JWT singleton — `_client_and_headers` contextmanager wrap, 3/3 PASS). Sprint T closes the PromptWorkflow consumption loop (3 skills × 3 descriptors wired). All UC golden-path gates green.
> **Terv:** **TO BE AUTHORED** — `01_PLAN/118_SPRINT_U_*.md` is this session's deliverable. Two candidate scopes are queued in §1 below; operator picks before the plan doc gets cut.
> **Session tipus:** KICKOFF (scope triage + plan + carry-forward audit, no feature code change).

---

## 1. MISSION

Open Sprint U with the same kickoff discipline that Sprint J / M / N / O / P / Q / R / S / T used: a single `01_PLAN/118_*` plan doc, the carry-forward queue triaged, and a clear scope for sessions S153+.

**Sprint U scope is ambiguous and needs operator triage at the top of this session.** Two candidate scopes exist in `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md`:

### Candidate A — Cost-aware routing escalation (originally roadmap §5 Sprint T scope)
Sprint T was originally planned as cost-aware routing escalation, but the actual Sprint T became per-skill PromptWorkflow consumer migration (closing the deferred S141-FU-1/2/3). The cost-aware routing work is therefore **still queued, just unscheduled**.

Headlines:
- `PolicyEngine.pick_model_tier()` per-use-case (cheap-first → confidence-drop fallback to a more expensive model)
- Pipeline-level cumulative budget tracker (beyond per-call `CostPreflightGuardrail`)
- Sprint N FU-2 (model-tier fallback ceilings → `CostGuardrailSettings`) + Grafana panel

Rationale: closes capability **E** (cost-effective pipeline) — the last functional capability gap from the Sprint Q/R/S/T roadmap.

### Candidate B — Operational hardening (roadmap §6 Sprint U scope)
The carry-forward catch-up sprint:
- `/status` OpenAPI drift CI step (`scripts/check_openapi_drift.py` already exists, only needs CI hookup)
- Weekly 4-combo matrix measurement as GitHub Action (Sprint P FU-2)
- `CostAttributionRepository` ↔ `record_cost` consolidation
- `CostSettings` umbrella class (consolidate `BudgetSettings` + `CostGuardrailSettings`)
- Soft-quota / over-draft semantics
- Langfuse v3→v4 server migration
- Sprint M live Vault rotation E2E
- ST-FU-2 Expert/mentor persona PromptWorkflow descriptors
- ST-FU-3 Per-step cost ceiling consolidation into `CostPreflightGuardrail.check_step()`
- ST-FU-4 Operator parity scripts uniform `--output` flag
- ST-FU-5 ruff-strips-imports tooling fix

Rationale: closes accumulated debt across Sprint M / N / O / P / Q / R / S / T retros. No single big-feature win; many small operability wins.

### Candidate C — Mix
A hybrid where the first 2-3 sessions hit the highest-value cost-aware routing wins (Candidate A subset) and the remaining sessions sweep the operational-hardening backlog (Candidate B subset).

**S152 deliverable:** operator picks one of A / B / C → this session authors `01_PLAN/118_SPRINT_U_*.md` accordingly. **Default if no operator input:** Candidate B (operational hardening) — it has the lowest blast-radius and the most accumulated debt that's already been triaged through prior retros.

S152 **does not** touch:
- Skill code (no `email_intent_processor` / `invoice_processor` / `aszf_rag_chat` change).
- New tests (the implementation lands in S153+).
- Migrations (no Alembic — kickoff sessions are docs-only).
- The `customer` column rename (SS-FU-1, SS-FU-5; deferred to a separate refactor sprint).
- Profile B Azure live MRR@5 (SS-SKIP-2; credit pending).

---

## 2. KONTEXTUS

### Honnan jöttünk

Sprint T closed 2026-04-25 on `chore/sprint-t-close`. Three squash-merged per-skill PRs + one close PR:

| PR | Squash | Headline |
|---|---|---|
| #40 | `aa74e02` | S148 — `email_intent_processor` consumes `email_intent_chain` |
| #41 | `e936eb3` | S149 — `invoice_processor` consumes `invoice_extraction_chain` |
| #42 | `ee2b431` | S150 — `aszf_rag_chat` baseline persona consumes `aszf_rag_chain` |
| (S151) | (this PR) | Sprint T close — retro + PR description + tag `v1.5.3` prep + ST-FU-1 fix |

### Hova tartunk

Sprint U is the next sprint. Per Candidate A / B / C above, S152 picks scope.

### Jelenlegi állapot (post-Sprint-T)

```
27 service | 196 endpoint (31 routers) | 50 DB tabla | 47 Alembic (head: 047)
2424 unit PASS / 1 skipped (ST-SKIP-1 conditional Azure Profile B)
~116 integration | 430 E2E collected
26 UI oldal | 8 skill | 22 pipeline adapter
3 PromptWorkflow descriptors ready+wired (3 skills consume `PromptWorkflowExecutor`)
   email_intent_processor → email_intent_chain (3 steps)
   invoice_processor → invoice_extraction_chain (4 steps + per-step cost ceilings)
   aszf_rag_chat baseline → aszf_rag_chain (4 steps; expert/mentor on legacy)
Default-off rollout preserved: AIFLOW_PROMPT_WORKFLOWS__ENABLED=false
                                AIFLOW_PROMPT_WORKFLOWS__SKILLS_CSV=""
```

### Carry-forward inventory (post-Sprint-T)

| ID | Source | Description | Sprint U candidate? |
|---|---|---|---|
| ST-FU-2 | Sprint T retro | Expert/mentor persona descriptors | **B** (operational) |
| ST-FU-3 | Sprint T retro | Per-step cost ceiling consolidation | **A** or **B** (depending on framing) |
| ST-FU-4 | Sprint T retro | Operator parity scripts `--output` flag | **B** |
| ST-FU-5 | Sprint T retro | ruff-strips-imports tooling fix | **B** |
| SR-FU-4/5/6 | Sprint R retro | Live Playwright + vite-build hook + Langfuse listing | **B** |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | **Out** (separate refactor sprint) |
| SS-SKIP-2 | Sprint S retro | Profile B Azure live MRR@5 | **Out** (Azure credit pending) |
| SQ-FU-1..4 | Sprint Q retro | issue_date fix, docling warmup, corpus extension, ISO roundtrip | **B** (subset) |
| SP-FU-1..3 | Sprint P retro | LLM-context fixture measurement, etc. | **B** (subset) |
| SM-FU-* | Sprint M retro | Vault rotation E2E, AppRole IaC, Langfuse v3→v4 | **B** (subset) |
| SN-FU-* | Sprint N retro | `CostSettings` umbrella, soft-quota, model-tier fallback | **A** or **B** |

### Key files for S152

| Role | Path |
|---|---|
| Capability roadmap | `01_PLAN/114_CAPABILITY_ROADMAP_Q_R_S.md` (§5 = Candidate A; §6 = Candidate B) |
| Sprint T plan reference | `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` (template for §1-11 structure) |
| Sprint S kickoff template | `session_prompts/S143_*.md` or `S147_*.md` |
| Sprint T retro | `docs/sprint_t_retro.md` |
| Sprint T PR description | `docs/sprint_t_pr_description.md` |

---

## 3. ELOFELTETELEK

```bash
git switch main                                                    # presumes Sprint T close PR merged
git pull --ff-only origin main
git checkout -b feature/u-s152-sprint-u-kickoff
git log --oneline -5                                                # confirm S151 close squash on tip
PYTHONPATH="src;." .venv/Scripts/python.exe -m alembic current     # head: 047
PYTHONPATH="src;." .venv/Scripts/python.exe -m pytest tests/unit/ --collect-only -q 2>&1 | tail -1   # 2424 collected
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet
```

Stop, ha:
- Sprint T close PR not yet merged → wait or escalate (the kickoff branch needs the close docs on `main` so it doesn't conflict).
- Alembic head ≠ 047 → drift; investigate before opening S152.
- `git status` dirty → finish or stash first.

---

## 4. FELADATOK

### LEPES 1 — Operator scope decision

Surface Candidate A / B / C to the operator at session start. Confirm which scope to author. Default: **Candidate B (operational hardening)** if no input within the first operator round-trip.

If the operator picks Candidate A: the plan doc gets named `01_PLAN/118_SPRINT_U_COST_AWARE_ROUTING_PLAN.md` and mirrors Sprint T's structure with cost-aware routing as the headline.

If the operator picks Candidate B: the plan doc gets named `01_PLAN/118_SPRINT_U_OPERATIONAL_HARDENING_PLAN.md` and groups the carry-forwards into 3-4 sessions by theme (CI hookups, refactor consolidation, persona descriptors, etc.).

If the operator picks Candidate C: the plan doc gets named `01_PLAN/118_SPRINT_U_HYBRID_PLAN.md` and explicitly schedules the cost-aware routing wins first, hardening backlog second.

### LEPES 2 — Carry-forward triage

For each carry-forward in §2 above:
- Confirm it's still relevant (some may have been silently fixed since the source retro).
- Map to a session in the chosen Sprint U scope.
- Or move to a "deferred to Sprint V" bucket if out of scope.

### LEPES 3 — `01_PLAN/118_SPRINT_U_*.md` plan doc

Mirror `01_PLAN/117_SPRINT_T_PROMPTWORKFLOW_MIGRATION_PLAN.md` shape:
1. Goal + capability cohort delta
2. Sessions table (S153, S154, ..., Sclose)
3. Plan + gate matrix (per-session gate test + threshold + rollback path)
4. Risk register
5. Follow-up table (carry-forwards inherited from Sprint T)
6. Test count expectations
7. Definition of done — per session
8. Skipped items tracker
9. STOP conditions (HARD)
10. Rollback
11. Out of scope (Sprint U)

### LEPES 4 — `docs/sprint_u_plan.md` (operator-facing companion)

Lighter narrative summary of §1-3 above for stakeholder review. Mirrors `docs/sprint_n_plan.md` style. **Optional if operator skips this** — the plan doc itself is the deliverable; the companion is for stakeholder readability.

### LEPES 5 — Lint + commit + push + PR

```bash
.venv/Scripts/python.exe -m ruff check src/ tests/ --quiet

git add 01_PLAN/118_SPRINT_U_*.md docs/sprint_u_plan.md \
        session_prompts/NEXT.md session_prompts/S153_*.md \
        session_prompts/S152_sprint_u_kickoff_prompt.md
git commit -m "docs(sprint-u): S152 — kickoff plan + carry-forward triage"
git push -u origin feature/u-s152-sprint-u-kickoff
gh pr create --base main --head feature/u-s152-sprint-u-kickoff \
  --title "Sprint U S152 — kickoff plan + carry-forward triage"
```

Then `/session-close S152` — which queues S153 (first Sprint U execution session).

---

## 5. STOP FELTETELEK

**HARD:**
1. Sprint T close PR not yet merged on `main` — wait until `main` carries the Sprint T close squash.
2. Operator declines all three candidates (A / B / C) and won't pick a fourth — halt; the kickoff has no scope to author.
3. Alembic head ≠ 047 → drift; investigate before opening S152.
4. CLAUDE.md banner refresh accidentally truncates Sprint T/S/Q/P/O/N/M/L history → halt; the Overview banner is append-only, never delete prior sprint entries.

**SOFT:**
- Operator wants to bundle multiple candidates → fall back to Candidate C (hybrid).
- A carry-forward turns out to be silently resolved (e.g., CI step already merged) → drop from the plan + note in the carry-forward audit.
- Sprint scope feels too large for 3-4 sessions → split into Sprint U + Sprint V; document the cut line in the plan doc.

---

## 6. SESSION VEGEN

```
/session-close S152
```

The `/session-close` will:
- Validate lint + unit collect.
- Stage + commit the kickoff diff (plan doc + carry-forward audit + S153 NEXT).
- Push the branch.
- Open the kickoff PR.
- Generate `session_prompts/NEXT.md` for S153 — the first Sprint U execution session.

---

## 7. SKIPPED-ITEMS TRACKER (carry from Sprint T S151)

| ID | Hely | Mi | Unskip feltetel |
|---|---|---|---|
| ST-SKIP-1 | `tests/unit/providers/embedder/test_azure_openai.py` | Conditional Azure Profile B live | Azure credit |
| SS-FU-1 / SS-FU-5 | Sprint S retro | `customer` → `tenant_id` rename | Separate refactor sprint |
| ST-FU-2 | Sprint T retro | Expert/mentor persona descriptors | Sprint U Candidate B |
| ST-FU-3 | Sprint T retro | Per-step cost ceiling consolidation | Sprint U Candidate A or B |
| ST-FU-4 | Sprint T retro | Operator parity scripts `--output` flag | Sprint U Candidate B |
| ST-FU-5 | Sprint T retro | ruff-strips-imports tooling fix | Sprint U Candidate B |
| SR-FU-4/5/6 | Sprint R retro | Live Playwright + vite-build hook + Langfuse listing | Sprint U Candidate B |

S152 opens Sprint U with scope triage. S153+ executes the chosen scope.
